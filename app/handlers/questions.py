"""
Private question handlers for user support.
Handles question limits, validation, and admin notifications.
"""

import logging
from datetime import datetime, date
from typing import Optional
from aiogram import Router, F, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramForbiddenError

from database.crud import (
    get_user, increment_question_usage, create_question, get_question,
    get_question_by_admin_message_id, answer_question, check_duplicate_question,
    check_question_cooldown, mark_question_failed_delivery, get_question_by_id,
    retry_failed_delivery, update_question_status
)
from database.db import SessionLocal
from ..config import config
from services.entitlement_policy import EntitlementPolicy, EntitlementExplanation, log_entitlement_decision
from services.i18n import t, t_user
from services.reconciliation_service import ReconciliationService

logger = logging.getLogger(__name__)


router = Router()

# Global bot instance for sending messages
_bot_instance = None
policy = EntitlementPolicy()


def _entitlement_denial_user_message(
    expl: EntitlementExplanation, user
) -> tuple[str, Optional[InlineKeyboardMarkup]]:
    """Map a denial into a context-aware (text, keyboard) pair.

    Replaces the previous one-size-fits-all "send /start" reply with guidance
    that reflects where the user actually is in onboarding / billing.
    """
    # No DB row at all → the one place where "send /start" is correct.
    if user is None:
        return t(None, "q.deny_not_registered"), None

    # Legal acceptance gate: distinguish "never accepted" (initial onboarding)
    # from "accepted prior version, document was bumped".
    if expl.reason == "legal_consent_missing":
        from services.legal_documents import REQUIRED_DOCUMENTS

        any_accepted = any(
            getattr(user, d.accepted_at_attr, None) for d in REQUIRED_DOCUMENTS
        )
        key = "q.deny_legal_updated" if any_accepted else "q.deny_legal_pending"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t_user(user, "btn.resume_legal"),
                    callback_data="legal_resume",
                )
            ],
        ])
        return t_user(user, key), kb

    # Not approved yet — branch on exact lifecycle status.
    if expl.reason == "user_not_approved":
        status = user.status
        if status == "NEW":
            return t_user(user, "q.deny_new_user"), None
        if status == "VERIFIED":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t_user(user, "btn.request_access_now"),
                        callback_data="request_access",
                    )
                ],
            ])
            return t_user(user, "q.deny_must_request_access"), kb
        if status == "PENDING_APPROVAL":
            return t_user(user, "q.deny_pending_approval"), None
        if status == "REJECTED":
            return t_user(user, "q.deny_rejected"), None
        return t_user(user, "q.deny_unknown_status", status=status or "?"), None

    # APPROVED, no Subscription row.
    if expl.reason == "no_subscription":
        return t_user(user, "q.deny_no_subscription"), None

    # APPROVED, has a Subscription row but it doesn't pass entitlement.
    if expl.reason in {"grace_expired", "past_due_grace_expired"}:
        return t_user(user, "q.deny_grace_expired"), None
    if expl.reason == "subscription_expired":
        return t_user(user, "q.deny_subscription_expired"), None
    if expl.reason == "subscription_cancelled":
        return t_user(user, "q.deny_subscription_cancelled"), None
    if expl.reason in {
        "subscription_inactive",
        "subscription_pending_payment",
        "subscription_suspended",
        "subscription_period_expired",
        "active_missing_end_date",
        "subscription_state_unknown",
    }:
        return t_user(user, "q.deny_subscription_inactive"), None

    # Safety net — should not be reached under current policy.
    return t_user(user, "q.deny_subscription_inactive"), None


MAX_QUESTION_LENGTH = 200


async def validate_question_content(question_text: str, message: Message, user) -> bool:
    """Validate question content for minimum requirements."""
    try:
        # Check if text is empty or whitespace only
        if not question_text or question_text.strip() == "":
            await message.answer(t_user(user, "q.empty"))
            return False

        # Check minimum length (at least 3 non-space characters)
        meaningful_chars = len(question_text.replace(" ", "").replace("\n", "").replace("\t", ""))
        if meaningful_chars < 3:
            await message.answer(t_user(user, "q.too_short"))
            return False

        # Enforce maximum question length (client spec: 200 chars).
        if len(question_text) > MAX_QUESTION_LENGTH:
            await message.answer(
                t_user(user, "q.too_long", limit=MAX_QUESTION_LENGTH, length=len(question_text))
            )
            return False

        # Check for obvious spam patterns
        spam_patterns = [".", "..", "ok", "hi", "hello", "hey"]
        normalized_text = question_text.strip().lower()
        if normalized_text in spam_patterns:
            await message.answer(t_user(user, "q.invalid"))
            return False

        return True

    except Exception as e:
        logger.error(f"Error validating question content: {e}")
        return False

def setup_bot_instance(bot: Bot) -> None:
    """Setup bot instance for sending messages."""
    global _bot_instance
    _bot_instance = bot


async def process_private_question_submission(
    message: Message, user_id: int, question_text: str
) -> None:
    """
    Full private-question pipeline (entitlement, validation, limits, persist, admin forward).
    Used for normal private messages and for VIP group → Yes callback forwarding.
    """
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            await message.answer(t(None, "q.deny_not_registered"))
            logger.info(f"Unregistered user {user_id} tried to send question")
            return

        expl = policy.explain_question_entitlement(user)
        log_entitlement_decision(logger, expl, user_id)

        if not expl.allows_questions:
            ReconciliationService(db).log_user_entitlement_state(user_id)
            deny_text, deny_kb = _entitlement_denial_user_message(expl, user)
            await message.answer(deny_text, reply_markup=deny_kb)
            logger.info(
                "Question blocked by entitlement user_id=%s user_status=%s reason=%s",
                user_id,
                user.status,
                expl.reason,
            )
            return

        qt = question_text or ""
        if not await validate_question_content(qt, message, user):
            return

        if not check_question_cooldown(db, user_id):
            await message.answer(t_user(user, "q.cooldown"))
            logger.info(f"User {user_id} on cooldown, question rejected")
            return

        duplicate = check_duplicate_question(db, user_id, qt)
        if duplicate:
            await message.answer(t_user(user, "q.duplicate"))
            logger.info(f"Duplicate question from user {user_id}: '{qt[:50]}...'")
            return

        if not await check_question_limit(user, message):
            return

        await accept_question(message, user_id, qt)

    except Exception as e:
        logger.error(f"Error processing question from user {user_id}: {e}")
        await message.answer(t_user(None, "q.system_error"))
    finally:
        db.close()


@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.text,
    ~F.command(),
    F.from_user.id != config.admin_id
)
async def handle_private_question(message: Message) -> None:
    """Handle private messages/questions from users (excluding admin messages)."""
    await process_private_question_submission(
        message, message.from_user.id, message.text or ""
    )


async def check_question_limit(user, message: Message) -> bool:
    """Check if user has remaining questions for the month."""
    try:
        # Keep existing Phase 1 limit behavior unchanged for safe rollout.
        if user.questions_used >= user.question_limit:
            await message.answer(
                t_user(user, "q.limit_reached", limit=user.question_limit)
            )
            logger.info(f"User {user.telegram_id} exceeded daily question limit")
            return False

        return True

    except Exception as e:
        logger.error(f"Error checking question limit for user {user.telegram_id}: {e}")
        return False


async def accept_question(message: Message, user_id: int, question_text: str) -> None:
    """Accept and process the user's question with proper tracking."""

    db = SessionLocal()
    try:
        # Get user object in this session to avoid persistence issues
        user = get_user(db, user_id)
        if not user:
            await message.answer(t(None, "q.system_error_user_not_found"))
            logger.error(f"User {user_id} not found during question processing")
            return

        # Create question record in database
        question = create_question(
            db,
            user_id=user_id,
            question_text=question_text,
        )

        if not question:
            await message.answer(t_user(user, "q.system_error_generic"))
            logger.error(f"Failed to create question record for user {user_id}")
            return

        # Increment question usage (without auto-commit for atomic transaction)
        from database.crud import increment_question_usage_no_commit
        if not increment_question_usage_no_commit(db, user):
            await message.answer(
                t_user(user, "q.limit_reached", limit=user.question_limit)
            )
            logger.info(f"User {user_id} exceeded daily question limit")
            # Rollback question creation since limit reached
            db.rollback()
            return

        # Accept the question - user object is already fresh from increment_question_usage
        remaining_questions = user.question_limit - user.questions_used
        logger.info(f"--- {user_id} remaining questions: {remaining_questions} ---- user.question_limit {user.question_limit} ----- user.questions_used {user.questions_used}--------")

        # Try to send user confirmation first - if this fails, rollback everything
        try:
            await message.answer(
                t_user(
                    user,
                    "q.received",
                    remaining=remaining_questions,
                    limit=user.question_limit,
                )
            )
        except Exception as msg_error:
            logger.error(f"Failed to send confirmation to user {user_id}: {msg_error}")
            db.rollback()
            await message.answer(t_user(user, "q.error_generic"))
            return

        # Try to forward to admin - if this fails, rollback user confirmation
        try:
            await forward_question_to_admin(message, user, question, db, question_text=question_text)
        except Exception as admin_error:
            logger.error(f"Failed to forward question {question.id} to admin: {admin_error}")
            db.rollback()
            await message.answer(t_user(user, "q.error_forwarding"))
            return

        # Only commit after all operations succeed
        db.commit()
        logger.info(f"Question persisted with ID: {question.id}")
        logger.info(f"Accepted question {question.id} from user {user_id}, remaining: {remaining_questions}")

    except Exception as e:
        logger.error(f"Error accepting question from user {user_id}: {e}")
        await message.answer(t(None, "q.error_generic"))
    finally:
        db.close()


async def forward_question_to_admin(
    message: Message, user, question, db, *, question_text: str
) -> None:
    """Forward user question to admin with question details using persistent session.

    Admin-facing text stays in English by design (see top of file).
    """
    try:
        if not _bot_instance:
            logger.warning("Bot instance not available for admin forwarding")
            return

        # Format user info
        username_display = f"@{user.username}" if user.username else "No username"

        admin_message = (
            f"**QUESTION #{question.id}**\n\n"
            f"👤 **From:** {user.first_name} (@{user.username or 'no username'})\n"
            f"🆔 **User ID:** `{user.telegram_id}`\n"
            f"📊 **Status:** {user.status} | Questions: {user.questions_used}/{user.question_limit}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💬 **Question:**\n"
            f"{question_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 *Reply to this message to respond*"
        )

        # Send to admin and capture the message ID
        admin_message_obj = await _bot_instance.send_message(
            chat_id=config.admin_id,
            text=admin_message,
            parse_mode="Markdown"
        )

        # Store admin message ID in database using the SAME session (no commit for atomic transaction)
        try:
            logger.info(f"Updating admin_message_id for question {question.id}")
            question.admin_message_id = admin_message_obj.message_id
            # Don't commit here - let caller handle commit for atomic transaction
            logger.info(f"admin_message_id updated successfully: question_id={question.id}, admin_message_id={admin_message_obj.message_id}")
        except Exception as e:
            logger.error(f"Failed to store admin message ID for question {question.id}: {e}")
            logger.exception("Full traceback:")
            raise  # Re-raise to trigger rollback in caller

        logger.info(f"Forwarded question {question.id} from user {user.telegram_id} to admin (msg_id: {admin_message_obj.message_id})")

    except Exception as e:
        logger.error(f"Error forwarding question to admin: {e}")
        logger.exception("Full traceback:")


# Handle non-text messages in private chat
@router.message(F.chat.type == ChatType.PRIVATE, ~F.text)
async def handle_private_content(message: Message) -> None:
    """Handle non-text messages in private chat."""
    user_id = message.from_user.id

    # Skip admin messages - admins can send any content
    if user_id == config.admin_id:
        logger.info(f"👑 Admin non-text message received: {message.content_type}")
        return

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
    finally:
        db.close()

    await message.answer(t_user(user, "q.text_only"))

    logger.info(f"Rejected non-text message from user {user_id} in private chat")


# Admin reply functionality - FIRST HANDLER
@router.message(F.chat.type == ChatType.PRIVATE, F.reply_to_message, F.from_user.id == config.admin_id, ~F.command())
async def handle_admin_reply(message: Message) -> None:
    """Handle admin replies to user questions using message ID mapping.

    Admin-facing alerts stay English; the message *delivered to the user* is
    translated into the user's language.
    """
    logger.info("🔍 STEP 1: Admin reply handler triggered")
    logger.info(f"🔍 Message details: from_id={message.from_user.id}, chat_type={message.chat.type}, has_reply_to_message={bool(message.reply_to_message)}")

    try:
        # Verify this is a reply to a message
        if not message.reply_to_message:
            logger.warning("🔍 STEP 2 FAILED: No reply_to_message found")
            logger.info(f"Admin sent message without reply_to_message, ignoring: {message.text[:50]}...")
            return

        logger.info("🔍 STEP 2: reply_to_message exists - SUCCESS")

        # Get the admin message ID that was replied to
        admin_message_id = message.reply_to_message.message_id
        logger.info(f"🔍 STEP 3: Extracted admin_message_id = {admin_message_id}")

        db = SessionLocal()
        try:
            logger.info("🔍 STEP 4: Querying database for question mapping")
            # Find the original question using admin message ID
            question = get_question_by_admin_message_id(db, admin_message_id)

            if not question:
                logger.warning(f"🔍 STEP 5 FAILED: No question found for admin_message_id: {admin_message_id}")
                logger.warning("🔍 DATABASE ISSUE: Question mapping not found in database")
                await message.answer("❌ Could not find the original question for this reply.")
                return

            logger.info(f"🔍 STEP 5: Mapping found - question_id={question.id}, user_id={question.user_id}, status={question.status}")

            # Check if question is still pending
            if not question.is_pending():
                logger.warning(f"🔍 STEP 6 FAILED: Question {question.id} already answered (status: {question.status})")
                await message.answer("❌ This question has already been answered.")
                logger.info(f"Question {question.id} already answered, ignoring admin reply")
                return

            logger.info("🔍 STEP 6: Question is pending - SUCCESS")

            # Send reply to user FIRST (before saving to DB)
            admin_reply_text = message.text

            if not _bot_instance:
                logger.error("🔍 STEP 7 FAILED: Bot instance not available")
                await message.answer("❌ Bot instance not available.")
                logger.error("Bot instance not available for sending reply to user")
                return

            logger.info("🔍 STEP 7: Bot instance available - SUCCESS")

            # Translate the user-facing response into THE USER's language.
            target_user = get_user(db, question.user_id)
            reply_to_user = t_user(
                target_user,
                "q.admin_response",
                question=question.question_text,
                reply=admin_reply_text,
            )

            logger.info(f"🔍 STEP 8: Sending response to user {question.user_id}")
            try:
                await _bot_instance.send_message(
                    chat_id=question.user_id,
                    text=reply_to_user
                    # Removed parse_mode to handle emojis and special characters safely
                )
                logger.info("🔍 STEP 9: Message sent to user successfully")
            except TelegramForbiddenError as forbidden_error:
                logger.error(f"🔍 STEP 9 FAILED: User {question.user_id} blocked bot or deleted chat: {forbidden_error}")
                logger.warning("Reply delivery failed due to user blocking bot")

                # Mark as failed delivery but save the admin reply
                if mark_question_failed_delivery(db, question.id, admin_reply_text):
                    await message.answer(
                        f"⚠️ **User Blocked Bot**\n\n"
                        f"User {question.user_id} has blocked the bot or deleted the chat.\n\n"
                        f"Your reply has been saved with status FAILED_DELIVERY.\n"
                        f"Use /retry {question.id} if the user unblocks later."
                    )
                else:
                    await message.answer("❌ Failed to save failed delivery status.")
                return

            except Exception as send_error:
                logger.error(f"🔍 STEP 9 FAILED: Failed to send message to user {question.user_id}: {send_error}")
                logger.warning("Reply delivery failed, question remains pending")
                await message.answer("❌ Failed to send reply to user. Please try again.")
                return

            # Only save to database AFTER successful message delivery
            logger.info(f"🔍 STEP 10: Updating question with admin reply")
            try:
                if not answer_question(db, question.id, admin_reply_text):
                    logger.error(f"🔍 STEP 11 FAILED: Failed to save answer to database for question {question.id}")
                    await message.answer("❌ Reply sent to user but failed to save to database.")
                    return

                logger.info("🔍 STEP 11: Answer saved to database - SUCCESS")
                logger.info("Reply delivered successfully, marking question answered")
            except Exception as db_error:
                logger.error(f"🔍 STEP 11 FAILED: Database error after successful send: {db_error}")
                await message.answer("⚠️ Reply sent to user but database update failed. Please check manually.")
                return

            await message.answer(f"✅ Reply sent to user {question.user_id}")
            logger.info(f"🔍 STEP 12: Admin response successfully delivered to user {question.user_id} for question {question.id}")

        except Exception as e:
            logger.error(f"🔍 DATABASE ERROR: Error handling admin reply: {e}")
            logger.exception("🔍 Full traceback:")
            await message.answer("❌ Error sending reply to user.")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"🔍 HANDLER ERROR: Error handling admin reply: {e}")
        logger.exception("🔍 Full traceback:")
        await message.answer("❌ Error sending reply to user.")
