"""
Private question handlers for user support.
Handles question limits, validation, and admin notifications.
"""

import logging
from datetime import datetime, date
from aiogram import Router, F, Bot
from aiogram.types import Message
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
from services.reconciliation_service import ReconciliationService

logger = logging.getLogger(__name__)


router = Router()

# Global bot instance for sending messages
_bot_instance = None
policy = EntitlementPolicy()


def _entitlement_denial_user_message(expl: EntitlementExplanation, user_status: str) -> str:
    if expl.reason == "user_not_approved":
        return (
            "❌ Access required\n\n"
            f"Your current status: {user_status}\n\n"
            "You need to be approved to ask questions.\n"
            "Please start the verification process by sending /start"
        )
    return (
        "❌ Your subscription is inactive or expired.\n"
        "Use /renew to restore access."
    )


async def validate_question_content(question_text: str, message: Message) -> bool:
    """Validate question content for minimum requirements."""
    try:
        # Check if text is empty or whitespace only
        if not question_text or question_text.strip() == "":
            await message.answer(
                "❌ **Empty Question**\n\n"
                "Please send a meaningful question."
            )
            return False
        
        # Check minimum length (at least 3 non-space characters)
        meaningful_chars = len(question_text.replace(" ", "").replace("\n", "").replace("\t", ""))
        if meaningful_chars < 3:
            await message.answer(
                "❌ **Question Too Short**\n\n"
                "Please send a more detailed question (at least 3 characters)."
            )
            return False
        
        # Check for obvious spam patterns
        spam_patterns = [".", "..", "ok", "hi", "hello", "hey"]
        normalized_text = question_text.strip().lower()
        if normalized_text in spam_patterns:
            await message.answer(
                "❌ **Invalid Question**\n\n"
                "Please send a meaningful question."
            )
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating question content: {e}")
        return False

def setup_bot_instance(bot: Bot) -> None:
    """Setup bot instance for sending messages."""
    global _bot_instance
    _bot_instance = bot


@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.text,
    ~F.command(),
    F.from_user.id != config.admin_id
)
async def handle_private_question(message: Message) -> None:
    """Handle private messages/questions from users (excluding admin messages)."""
    user_id = message.from_user.id
    
    db = SessionLocal()
    try:
        # Check if user is approved
        user = get_user(db, user_id)
        if not user:
            await message.answer(
                "❌ **Access Required**\n\n"
                "You need to be approved to ask questions.\n\n"
                "Please start the verification process by sending /start"
            )
            logger.info(f"Unregistered user {user_id} tried to send question")
            return
        
        expl = policy.explain_question_entitlement(user)
        log_entitlement_decision(logger, expl, user_id)

        if not expl.allows_questions:
            ReconciliationService(db).log_user_entitlement_state(user_id)
            await message.answer(_entitlement_denial_user_message(expl, user.status))
            logger.info(
                "Question blocked by entitlement user_id=%s user_status=%s reason=%s",
                user_id,
                user.status,
                expl.reason,
            )
            return
        
        # Validate question content
        question_text = message.text or ""
        if not await validate_question_content(question_text, message):
            return
        
        # Check cooldown
        if not check_question_cooldown(db, user_id):
            await message.answer(
                "⏳ **Please Wait**\n\n"
                "Please wait a few seconds before sending another question."
            )
            logger.info(f"User {user_id} on cooldown, question rejected")
            return
        
        # Check for duplicate questions
        duplicate = check_duplicate_question(db, user_id, question_text)
        if duplicate:
            await message.answer(
                "⚠️ **Duplicate Question**\n\n"
                "You already sent this question recently."
            )
            logger.info(f"Duplicate question from user {user_id}: '{question_text[:50]}...'")
            return
        
        # Check question limit
        if not await check_question_limit(user, message):
            return
        
        # Create question record and accept it
        await accept_question(message, user_id)
        
    except Exception as e:
        logger.error(f"Error processing question from user {user_id}: {e}")
        await message.answer(
            "❌ **System Error**\n\n"
            "Sorry, there was an error processing your question. Please try again later."
        )
    finally:
        db.close()


async def check_question_limit(user, message: Message) -> bool:
    """Check if user has remaining questions for the month."""
    try:
        # Keep existing Phase 1 limit behavior unchanged for safe rollout.
        if user.questions_used >= user.question_limit:
            await message.answer(
                "❌ **Question Limit Reached**\n\n"
                f"You have used your daily limit of {user.question_limit} questions.\n\n"
                "Your question count will reset tomorrow. Please try again then."
            )
            logger.info(f"User {user.telegram_id} exceeded daily question limit")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking question limit for user {user.telegram_id}: {e}")
        return False


async def accept_question(message: Message, user_id: int) -> None:
    """Accept and process the user's question with proper tracking."""
    
    db = SessionLocal()
    try:
        # Get user object in this session to avoid persistence issues
        user = get_user(db, user_id)
        if not user:
            await message.answer(
                "❌ **System Error**\n\n"
                "User not found. Please try again."
            )
            logger.error(f"User {user_id} not found during question processing")
            return
        
        # Create question record in database
        question = create_question(
            db,
            user_id=user_id,
            question_text=message.text
        )
        
        if not question:
            await message.answer(
                "❌ **System Error**\n\n"
                "There was an error processing your question. Please try again."
            )
            logger.error(f"Failed to create question record for user {user_id}")
            return
        
        # Increment question usage (without auto-commit for atomic transaction)
        from database.crud import increment_question_usage_no_commit
        if not increment_question_usage_no_commit(db, user):
            await message.answer(
                "❌ **Question Limit Reached**\n\n"
                f"You have reached your daily limit of {user.question_limit} questions.\n\n"
                "Your question count will reset tomorrow. Please try again then."
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
                f"✅ **Question Received**\n\n"
                f"Your question has been sent to the admin.\n\n"
                f"📊 Remaining questions today: {remaining_questions}/{user.question_limit}\n\n"
                f"You'll receive a response as soon as possible."
            )
        except Exception as msg_error:
            logger.error(f"Failed to send confirmation to user {user_id}: {msg_error}")
            db.rollback()
            await message.answer(
                "❌ **Error**\n\n"
                "There was an error processing your question. Please try again."
            )
            return
        
        # Try to forward to admin - if this fails, rollback user confirmation
        try:
            await forward_question_to_admin(message, user, question, db)
        except Exception as admin_error:
            logger.error(f"Failed to forward question {question.id} to admin: {admin_error}")
            db.rollback()
            await message.answer(
                "❌ **Error**\n\n"
                "Your question was received but there was an error forwarding it. Please try again."
            )
            return
        
        # Only commit after all operations succeed
        db.commit()
        logger.info(f"Question persisted with ID: {question.id}")
        logger.info(f"Accepted question {question.id} from user {user_id}, remaining: {remaining_questions}")
        
    except Exception as e:
        logger.error(f"Error accepting question from user {user_id}: {e}")
        await message.answer(
            "❌ **Error**\n\n"
            "There was an error processing your question. Please try again."
        )
    finally:
        db.close()


async def forward_question_to_admin(message: Message, user, question, db) -> None:
    """Forward user question to admin with question details using persistent session."""
    try:
        if not _bot_instance:
            logger.warning("Bot instance not available for admin forwarding")
            return
        
        # Format user info
        username_display = f"@{user.username}" if user.username else "No username"
        
        admin_message = (
            f"� **QUESTION #{question.id}**\n\n"
            f"👤 **From:** {user.first_name} (@{user.username or 'no username'})\n"
            f"🆔 **User ID:** `{user.telegram_id}`\n"
            f"📊 **Status:** {user.status} | Questions: {user.questions_used}/{user.question_limit}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💬 **Question:**\n"
            f"{message.text}\n\n"
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
    
    await message.answer(
        "❌ **Text Only**\n\n"
        "Please send your questions as text messages only.\n\n"
        "Images, files, and other content are not supported at this time."
    )
    
    logger.info(f"Rejected non-text message from user {user_id} in private chat")


# Admin reply functionality - FIRST HANDLER
@router.message(F.chat.type == ChatType.PRIVATE, F.reply_to_message, F.from_user.id == config.admin_id, ~F.command())
async def handle_admin_reply(message: Message) -> None:
    """Handle admin replies to user questions using message ID mapping."""
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
            
            reply_to_user = (
                f"📨 **Admin Response**\n\n"
                f"❓ **Your Question:**\n"
                f"{question.question_text}\n\n"
                f"💬 **Response:**\n"
                f"{admin_reply_text}\n\n"
                f"---\n"
                f"This is a response to your question. You can reply to this message if you need clarification."
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


