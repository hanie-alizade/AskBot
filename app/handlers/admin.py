"""
Admin handlers for the user flow.
Handles admin approval commands and admin-only functions.
"""

import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from database.crud import (
    get_user, update_user_status, get_all_users, get_pending_users, get_user_count_by_status,
    retry_failed_delivery, update_question_status, reset_user_completely, reject_user, create_user,
)
from database.db import SessionLocal
from database.models import User
from ..config import config
from services.subscription_service import SubscriptionService
from services.subscription_readout import build_subscription_view, format_admin_subscription_status_message
from services.entitlement_policy import EntitlementPolicy
from services.i18n import t_user
from services.i18n.admin import get_admin_language, get_admin_text
from services.payments.factory import build_payment_gateway
from services.payments.webhook_service import WebhookService
from services.vip_invite import notify_vip_invite_if_eligible

logger = logging.getLogger(__name__)

router = Router()


def _t(key: str, **kwargs) -> str:
    """Localize an admin string in the currently-selected admin language."""
    return get_admin_text(key, None, **kwargs)


# Standard separator used by a few command bodies (matches the panel's style).
_CMD_SEPARATOR = "━━━━━━━━━━━━━━━━━━━━"

# Global bot instance for sending messages
_bot_instance = None

def setup_bot_instance(bot: Bot) -> None:
    """Setup bot instance for sending messages."""
    global _bot_instance
    _bot_instance = bot



class AdminFilter:
    """Custom filter to check if user is admin."""
    
    def __init__(self, admin_id: int):
        self.admin_id = admin_id
    
    def __call__(self, message: Message) -> bool:
        return message.from_user.id == self.admin_id


@router.message(Command("approve"), AdminFilter(config.admin_id))
async def handle_approve_command(message: Message) -> None:
    """Handle /approve command for admin to approve users."""
    try:
        # Extract user_id from command
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer(_t("cmd.approve_invalid_format"))
            return

        try:
            user_id = int(parts[1])
        except ValueError:
            await message.answer(_t("cmd.approve_invalid_id"))
            return

        db = SessionLocal()
        try:
            # Check if user exists and is pending approval
            user = get_user(db, user_id)

            if not user:
                await message.answer(_t("cmd.user_not_found", user_id=user_id))
                return

            if user.status == "NEW":
                await message.answer(_t("cmd.approve_not_verified", user_id=user_id))
                return

            elif user.status == "VERIFIED":
                await message.answer(_t("cmd.approve_not_requested", user_id=user_id))
                return

            elif user.status == "APPROVED":
                await message.answer(_t("cmd.approve_already", user_id=user_id))
                return

            elif user.status != "PENDING_APPROVAL":
                await message.answer(_t("cmd.approve_not_pending", user_id=user_id))
                return

            # Approve the user
            approved_user = update_user_status(db, user_id, "APPROVED")
            if not approved_user:
                await message.answer(_t("cmd.approve_failed"))
                return

            await send_approval_notice(user_id)

            await message.answer(_t("cmd.approve_success", user_id=user_id))

            logger.info(f"Admin {message.from_user.id} approved user {user_id}")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in approve command: {e}")
        await message.answer(_t("cmd.approve_error"))


@router.message(Command("reject"), AdminFilter(config.admin_id))
async def handle_reject_command(message: Message) -> None:
    """Handle /reject command for admin to reject users - production-safe implementation."""
    try:
        logger.info(f"Reject command received from admin {message.from_user.id}")
        
        # Extract user_id and reason from command
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            await message.answer(_t("cmd.reject_invalid_format"))
            return

        try:
            user_id = int(parts[1])
            reason = parts[1] if len(parts) > 2 else "Access denied"
            logger.info(f"Parsed reject command: user_id={user_id}, reason='{reason}'")
        except ValueError:
            await message.answer(_t("cmd.reject_invalid_id"))
            return

        db = SessionLocal()
        try:
            # Check if user exists
            user = get_user(db, user_id)

            if not user:
                logger.error(f"Reject failed: User {user_id} not found in database")
                await message.answer(_t("cmd.reject_user_not_found", user_id=user_id))
                return

            logger.info(f"Found user {user_id} with current status: {user.status}")

            # Check if already rejected (idempotent)
            if user.status == "REJECTED":
                logger.info(f"User {user_id} is already rejected - idempotent operation")
                await message.answer(_t("cmd.reject_already", user_id=user_id))
                return

            # Reject user in database FIRST (atomic operation)
            if not reject_user(db, user_id, reason):
                logger.error(f"Database reject failed for user {user_id}")
                await message.answer(_t("cmd.reject_db_error"))
                return
            
            logger.info(f"Database reject successful for user {user_id}")
            
            # Initialize operation results
            notification_sent = False
            group_removal_success = False
            group_removal_attempted = False
            
            # Try to send notification to user (independent operation)
            try:
                await send_rejection_notification(user_id, reason)
                notification_sent = True
                logger.info(f"Rejection notification sent successfully to user {user_id}")
            except Exception as notify_error:
                logger.warning(f"Failed to send rejection notification to user {user_id}: {notify_error}")
                # Continue with other operations even if notification fails
            
            # Try to remove from VIP group (independent operation)
            try:
                if _bot_instance and config.vip_group_id:
                    group_removal_attempted = True
                    await _bot_instance.ban_chat_member(
                        chat_id=config.vip_group_id,
                        user_id=user_id
                    )
                    group_removal_success = True
                    logger.info(f"Successfully removed user {user_id} from VIP group")
                else:
                    logger.warning("Bot instance or VIP_GROUP_ID not available for group removal")
            except Exception as group_error:
                logger.warning(f"Failed to remove user {user_id} from VIP group: {group_error}")
                # Continue even if group removal fails
            
            # Send detailed success message to admin
            success_message = _t(
                "cmd.reject_success",
                user_id=user_id,
                reason=reason,
                notif=_t("cmd.op_success") if notification_sent else _t("cmd.op_failed"),
            )

            if group_removal_attempted:
                success_message += _t(
                    "cmd.reject_group_removal",
                    result=_t("cmd.op_success") if group_removal_success else _t("cmd.op_failed"),
                )
            else:
                success_message += _t("cmd.reject_group_skipped")

            await message.answer(success_message)
            
            logger.info(f"Reject flow completed for user {user_id}: "
                      f"notification={'sent' if notification_sent else 'failed'}, "
                      f"group_removal={'success' if group_removal_success else 'failed' if group_removal_attempted else 'skipped'}")
                
        except Exception as db_error:
            logger.error(f"Database error in reject command for user {user_id}: {db_error}")
            await message.answer(_t("cmd.reject_db_error_process"))
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Critical error in reject command: {e}")
        await message.answer(_t("cmd.reject_system_error"))


async def send_rejection_notification(user_id: int, reason: str) -> None:
    """Send rejection notification to user — translated into the user's language."""
    try:
        if not _bot_instance:
            logger.error("Bot instance not available for sending rejection notification")
            return

        db = SessionLocal()
        try:
            target_user = get_user(db, user_id)
        finally:
            db.close()

        rejection_message = t_user(target_user, "admin.user_rejected", reason=reason)

        # No parse_mode: messages contain user-provided `reason` text we don't want to interpret.
        await _bot_instance.send_message(chat_id=user_id, text=rejection_message)

        logger.info(f"Sent rejection notification to user {user_id}")

    except Exception as e:
        logger.error(f"Error sending rejection notification to user {user_id}: {e}")


async def send_approval_notice(user_id: int) -> None:
    """Tell user they are approved; VIP link is sent later when subscription is valid."""
    if not _bot_instance:
        logger.warning("Bot instance not available for approval notice user_id=%s", user_id)
        return
    try:
        db = SessionLocal()
        try:
            target_user = get_user(db, user_id)
        finally:
            db.close()
        await _bot_instance.send_message(
            chat_id=user_id,
            text=t_user(target_user, "admin.user_approved"),
        )
        logger.info("Approval notice sent user_id=%s", user_id)
    except Exception as e:
        logger.error("Failed to send approval notice to user %s: %s", user_id, e)


@router.message(Command("pending"), AdminFilter(config.admin_id))
async def handle_pending_command(message: Message) -> None:
    """Handle /pending command to show all users pending approval."""
    db = SessionLocal()
    try:
        pending_users = get_pending_users(db)
        
        if not pending_users:
            await message.answer(
                _t("cmd.pending_empty", sep=_CMD_SEPARATOR),
                parse_mode="HTML",
            )
            return

        pending_text = _t("cmd.pending_header")

        for user in pending_users:
            pending_text += _t("cmd.pending_row", user_id=user.telegram_id)

        await message.answer(pending_text)
        logger.info(f"Admin {message.from_user.id} viewed pending users")

    except Exception as e:
        logger.error(f"Error in pending command: {e}")
        await message.answer(_t("cmd.pending_error"))
    finally:
        db.close()


@router.message(Command("users"), AdminFilter(config.admin_id))
async def handle_users_command(message: Message) -> None:
    """Handle /users command to show all users with details."""
    db = SessionLocal()
    try:
        all_users = get_all_users(db)
        
        if not all_users:
            await message.answer(
                _t("cmd.users_empty", sep=_CMD_SEPARATOR),
                parse_mode="HTML",
            )
            return

        users_text = _t("cmd.users_header")

        for user in all_users:
            role_emoji = {
                "NEW": "🆕",
                "VERIFIED": "✅",
                "PENDING_APPROVAL": "⏳",
                "APPROVED": "🎉"
            }.get(user.status, "❓")

            role_name = {
                "NEW": _t("cmd.role_new"),
                "VERIFIED": _t("cmd.role_verified"),
                "PENDING_APPROVAL": _t("cmd.role_pending"),
                "APPROVED": _t("cmd.role_approved"),
            }.get(user.status, _t("cmd.role_unknown"))

            username_display = f"@{user.username}" if user.username else _t("cmd.users_no_username")

            users_text += _t(
                "cmd.users_row",
                role_emoji=role_emoji,
                first_name=user.first_name,
                telegram_id=user.telegram_id,
                username_display=username_display,
                role_name=role_name,
            )
        
        # Split message if too long
        if len(users_text) > 4000:
            parts = [users_text[i:i+4000] for i in range(0, len(users_text), 4000)]
            for part in parts:
                await message.answer(part, parse_mode="Markdown")
        else:
            await message.answer(users_text, parse_mode="Markdown")
        
        logger.info(f"Admin {message.from_user.id} viewed users list")

    except Exception as e:
        logger.error(f"Error in users command: {e}")
        await message.answer(_t("cmd.users_error"))
    finally:
        db.close()


@router.message(Command("stats"), AdminFilter(config.admin_id))
async def handle_stats_command(message: Message) -> None:
    """Handle /stats command to show user statistics."""
    db = SessionLocal()
    try:
        counts = get_user_count_by_status(db)

        stats_text = _t(
            "cmd.stats",
            new=counts["new"],
            verified=counts["verified"],
            pending=counts["pending_approval"],
            approved=counts["approved"],
            total=sum(counts.values()),
        )

        await message.answer(stats_text)
        logger.info(f"Admin {message.from_user.id} viewed statistics")

    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await message.answer(_t("cmd.stats_error"))
    finally:
        db.close()


@router.message(Command("sub_status"), AdminFilter(config.admin_id))
async def handle_sub_status_command(message: Message) -> None:
    """Admin: read-only subscription + entitlement snapshot."""
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(_t("cmd.sub_status_usage"))
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer(_t("cmd.invalid_user_id_numeric"))
        return

    db = SessionLocal()
    try:
        svc = SubscriptionService(db)
        user = get_user(db, target_id)
        snap = svc.get_subscription_snapshot(target_id, user=user)
        expl = EntitlementPolicy().explain_question_entitlement(user)
        vm = build_subscription_view(snap, expl)
        await message.answer(
            format_admin_subscription_status_message(target_id, vm, lang=get_admin_language())
        )
        logger.info("admin sub_status target=%s by=%s", target_id, message.from_user.id)
    finally:
        db.close()


@router.message(Command("sub_activate"), AdminFilter(config.admin_id))
async def handle_sub_activate_command(message: Message) -> None:
    """Admin: activate subscription via SubscriptionService."""
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(_t("cmd.sub_activate_usage"))
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer(_t("cmd.invalid_user_id_numeric"))
        return

    db = SessionLocal()
    try:
        svc = SubscriptionService(db)
        ok = svc.admin_activate_subscription(
            target_id,
            admin_user_id=message.from_user.id,
        )
        if ok and _bot_instance:
            await notify_vip_invite_if_eligible(_bot_instance, target_id)
        await message.answer(_t("cmd.sub_activated") if ok else _t("cmd.sub_activate_failed"))
    finally:
        db.close()


@router.message(Command("sub_expire"), AdminFilter(config.admin_id))
async def handle_sub_expire_command(message: Message) -> None:
    """Admin: force-expire latest subscription row."""
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(_t("cmd.sub_expire_usage"))
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer(_t("cmd.invalid_user_id_numeric"))
        return

    db = SessionLocal()
    try:
        svc = SubscriptionService(db)
        ok = svc.force_expire_subscription(target_id, admin_user_id=message.from_user.id)
        await message.answer(_t("cmd.sub_expired") if ok else _t("cmd.sub_expire_failed"))
    finally:
        db.close()


@router.message(Command("sub_grace"), AdminFilter(config.admin_id))
async def handle_sub_grace_command(message: Message) -> None:
    """Admin: move subscription to grace."""
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(_t("cmd.sub_grace_usage"))
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer(_t("cmd.invalid_user_id_numeric"))
        return

    grace_days = 3
    if len(parts) >= 3:
        try:
            grace_days = int(parts[2])
        except ValueError:
            await message.answer(_t("cmd.grace_days_numeric"))
            return

    db = SessionLocal()
    try:
        svc = SubscriptionService(db)
        ok = svc.admin_move_to_grace(
            target_id,
            admin_user_id=message.from_user.id,
            grace_days=grace_days,
        )
        if ok and _bot_instance:
            await notify_vip_invite_if_eligible(_bot_instance, target_id)
        await message.answer(_t("cmd.sub_grace_ok") if ok else _t("cmd.sub_grace_failed"))
    finally:
        db.close()


@router.message(Command("admin_help"), AdminFilter(config.admin_id))
async def handle_admin_help_command(message: Message) -> None:
    """Handle /admin_help command to show admin commands."""
    await show_admin_menu(message)
    logger.info(f"Admin {message.from_user.id} requested admin help")


async def show_admin_menu(message: Message) -> None:
    """Show admin menu with command buttons."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_t("cmd.admin_menu_btn_users"), callback_data="admin_users")],
        [InlineKeyboardButton(text=_t("cmd.admin_menu_btn_pending"), callback_data="admin_pending")],
        [InlineKeyboardButton(text=_t("cmd.admin_menu_btn_stats"), callback_data="admin_stats")],
        [InlineKeyboardButton(text=_t("cmd.admin_menu_btn_help"), callback_data="admin_help_menu")]
    ])

    help_text = _t("cmd.admin_menu_text")

    await message.answer(help_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("admin_"), AdminFilter(config.admin_id))
async def handle_admin_callback(callback: CallbackQuery) -> None:
    """Handle admin menu button clicks."""
    action = callback.data.split("_")[1]
    
    if action == "users":
        await handle_users_command(callback.message)
    elif action == "pending":
        await handle_pending_command(callback.message)
    elif action == "stats":
        await handle_stats_command(callback.message)
    elif action == "help_menu":
        await show_admin_menu(callback.message)
    
    await callback.answer()


@router.callback_query(F.data == "check_status", AdminFilter(config.admin_id))
async def handle_admin_status_callback(callback: CallbackQuery) -> None:
    """Handle status button click for admin."""
    from .access import handle_status_command
    
    await handle_status_command(callback.message)
    await callback.answer()


@router.callback_query(F.data == "show_help", AdminFilter(config.admin_id))
async def handle_admin_help_callback(callback: CallbackQuery) -> None:
    """Handle help button click for admin."""
    from .access import handle_help_command
    
    await handle_help_command(callback.message)
    await callback.answer()

@router.message(Command("start"), AdminFilter(config.admin_id))
async def handle_admin_start(message: Message) -> None:
    """Handle /start command for admin users with automatic approval."""
    user_id = message.from_user.id
    logger.info(f"👑 Admin START command triggered by user {user_id}")
    
    db = SessionLocal()
    try:
        # Get or create admin user in database
        admin_user = get_user(db, user_id)
        
        if not admin_user:
            # Create admin user with APPROVED status
            admin_user = create_user(
                db,
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.full_name
            )
            logger.info(f"Created new admin user: {user_id}")
        
        # Auto-approve admin user
        if admin_user.status != "APPROVED":
            approved_admin = update_user_status(db, user_id, "APPROVED")
            if approved_admin:
                logger.info(f"👑 Admin auto-approved: {user_id}")
            else:
                logger.error(f"Failed to auto-approve admin: {user_id}")
        
        # Send admin welcome message
        admin_welcome = _t("cmd.admin_welcome")

        await message.answer(admin_welcome, parse_mode="Markdown")
        logger.info(f"Admin welcome sent to user {user_id}")

    except Exception as e:
        logger.error(f"Error in admin start handler for user {user_id}: {e}")
        await message.answer(_t("cmd.admin_setup_error"))
    finally:
        db.close()


# Non-admin handlers for unauthorized access attempts
@router.message(Command("approve"))
async def handle_unauthorized_approve(message: Message) -> None:
    """Handle unauthorized /approve attempts."""
    await message.answer(_t("cmd.not_authorized"))


@router.message(Command("pending"))
async def handle_unauthorized_pending(message: Message) -> None:
    """Handle unauthorized /pending attempts."""
    await message.answer(_t("cmd.not_authorized"))


@router.message(Command("stats"))
async def handle_unauthorized_stats(message: Message) -> None:
    """Handle unauthorized /stats attempts."""
    await message.answer(_t("cmd.not_authorized"))


@router.message(Command("users"))
async def handle_unauthorized_users(message: Message) -> None:
    """Handle unauthorized /users attempts."""
    await message.answer(_t("cmd.not_authorized"))


@router.message(Command("admin_help"))
async def handle_unauthorized_admin_help(message: Message) -> None:
    """Handle unauthorized /admin_help attempts."""
    await message.answer(_t("cmd.not_authorized"))


@router.message(Command("simulate_payment"))
async def handle_unauthorized_simulate_payment(message: Message) -> None:
    """Handle unauthorized /simulate_payment attempts."""
    await message.answer(_t("cmd.not_authorized"))


@router.message(Command("simulate_subscription_expiry"))
async def handle_unauthorized_simulate_subscription_expiry(message: Message) -> None:
    """Handle unauthorized /simulate_subscription_expiry attempts."""
    await message.answer(_t("cmd.not_authorized"))


@router.message(Command("sub_status"))
async def handle_unauthorized_sub_status(message: Message) -> None:
    await message.answer(_t("cmd.not_authorized"))


@router.message(Command("sub_activate"))
async def handle_unauthorized_sub_activate(message: Message) -> None:
    await message.answer(_t("cmd.not_authorized"))


@router.message(Command("sub_expire"))
async def handle_unauthorized_sub_expire(message: Message) -> None:
    await message.answer(_t("cmd.not_authorized"))


@router.message(Command("sub_grace"))
async def handle_unauthorized_sub_grace(message: Message) -> None:
    await message.answer(_t("cmd.not_authorized"))


@router.callback_query(F.data.startswith("approve:"), AdminFilter(config.admin_id))
async def handle_approve_callback(callback: CallbackQuery) -> None:
    """Handle approve button click from inline keyboard."""
    try:
        # Extract user_id from callback data
        user_id = int(callback.data.split(":")[1])
        
        db = SessionLocal()
        try:
            # Check if user exists and is pending approval
            user = get_user(db, user_id)
            
            if not user:
                await callback.message.edit_text(_t("cmd.user_not_found", user_id=user_id))
                return

            if user.status != "PENDING_APPROVAL":
                await callback.message.edit_text(
                    _t("cmd.approve_not_pending_status", user_id=user_id, status=user.status)
                )
                return

            # Approve user
            if update_user_status(db, user_id, "APPROVED"):
                await send_approval_notice(user_id)

                await callback.message.edit_text(_t("cmd.approve_success", user_id=user_id))

                logger.info(f"Admin approved user {user_id} via button")
            else:
                await callback.message.edit_text(_t("cmd.approve_failed"))

        except Exception as e:
            logger.error(f"Error in approve callback: {e}")
            await callback.message.edit_text(_t("cmd.approve_error"))
        finally:
            db.close()

    except ValueError:
        await callback.answer(_t("cmd.cb_invalid_user_id"))
    except Exception as e:
        logger.error(f"Error handling approve callback: {e}")
        await callback.answer(_t("cmd.cb_approve_error"))


@router.callback_query(F.data.startswith("reject:"), AdminFilter(config.admin_id))
async def handle_reject_callback(callback: CallbackQuery) -> None:
    """Handle reject button click from inline keyboard - production-safe implementation."""
    try:
        logger.info(f"Reject callback received from admin {callback.from_user.id}")
        
        # Extract user_id from callback data
        try:
            user_id = int(callback.data.split(":")[1])
            logger.info(f"Parsed reject callback: user_id={user_id}")
        except ValueError:
            logger.error("Invalid user ID in reject callback data")
            await callback.answer(_t("cmd.cb_invalid_user_id"))
            return

        db = SessionLocal()
        try:
            # Check if user exists
            user = get_user(db, user_id)

            if not user:
                logger.error(f"Reject callback failed: User {user_id} not found in database")
                await callback.message.edit_text(_t("cmd.reject_user_not_found", user_id=user_id))
                return

            logger.info(f"Reject callback: Found user {user_id} with status: {user.status}")

            # Check if already rejected (idempotent)
            if user.status == "REJECTED":
                logger.info(f"Reject callback: User {user_id} already rejected - idempotent")
                await callback.message.edit_text(_t("cmd.reject_already", user_id=user_id))
                return

            # Reject user in database FIRST (atomic operation)
            if not reject_user(db, user_id, "Rejected via admin button"):
                logger.error(f"Reject callback: Database reject failed for user {user_id}")
                await callback.message.edit_text(_t("cmd.reject_db_error_cb", user_id=user_id))
                return
            
            logger.info(f"Reject callback: Database reject successful for user {user_id}")
            
            # Initialize operation results
            notification_sent = False
            
            # Try to send notification to user (independent operation)
            try:
                await send_rejection_notification(user_id, "Rejected via admin button")
                notification_sent = True
                logger.info(f"Reject callback: Notification sent to user {user_id}")
            except Exception as notify_error:
                logger.warning(f"Reject callback: Failed to send notification to user {user_id}: {notify_error}")
                # Continue even if notification fails
            
            # Update admin message with detailed results
            success_message = _t(
                "cmd.reject_success",
                user_id=user_id,
                reason="Rejected via admin button",
                notif=_t("cmd.op_success") if notification_sent else _t("cmd.op_failed"),
            )

            await callback.message.edit_text(success_message)

            logger.info(f"Reject callback completed for user {user_id}: "
                      f"notification={'sent' if notification_sent else 'failed'}")

        except Exception as db_error:
            logger.error(f"Database error in reject callback for user {user_id}: {db_error}")
            await callback.message.edit_text(_t("cmd.reject_db_error_process"))
        finally:
            db.close()

    except ValueError:
        logger.error("Invalid user ID in reject callback data")
        await callback.answer(_t("cmd.cb_invalid_user_id"))
    except Exception as e:
        logger.error(f"Critical error in reject callback: {e}")
        await callback.answer(_t("cmd.cb_reject_error"))


@router.message(Command("retry"))
async def retry_failed_question_command(message: Message) -> None:
    """Retry sending failed delivery questions to users."""
    if not message.from_user or message.from_user.id != config.admin_id:
        return
    
    try:
        # Extract question ID from command
        command_parts = message.text.split()
        if len(command_parts) != 2:
            await message.answer(_t("cmd.retry_invalid_command"))
            return

        try:
            question_id = int(command_parts[1])
        except ValueError:
            await message.answer(_t("cmd.retry_invalid_id"))
            return

        db = SessionLocal()
        try:
            # Get failed delivery question
            question = retry_failed_delivery(db, question_id)
            if not question:
                await message.answer(_t("cmd.retry_not_found", question_id=question_id))
                return
            
            # Try to resend the message
            reply_to_user = (
                f"📨 **Admin Response**\n\n"
                f"❓ **Your Question:**\n"
                f"{question.question_text}\n\n"
                f"💬 **Response:**\n"
                f"{question.admin_reply_text}\n\n"
                f"---\n"
                f"This is a response to your question. You can reply to this message if you need clarification."
            )
            
            if not _bot_instance:
                await message.answer(_t("cmd.retry_no_bot"))
                return

            await _bot_instance.send_message(
                chat_id=question.user_id,
                text=reply_to_user
            )

            # Mark as answered if successful
            if update_question_status(db, question_id, "ANSWERED"):
                await message.answer(
                    _t("cmd.retry_success", question_id=question_id, user_id=question.user_id)
                )
                logger.info(f"Successfully retried question {question_id} to user {question.user_id}")
            else:
                await message.answer(_t("cmd.retry_partial"))

        except Exception as e:
            logger.error(f"Error retrying question {question_id}: {e}")
            await message.answer(_t("cmd.retry_failed", question_id=question_id, err=e))
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in retry command: {e}")
        await message.answer(_t("cmd.retry_error"))


@router.message(Command("simulate_payment"))
async def simulate_payment_command(message: Message) -> None:
    """
    Simulate payment events locally.
    Usage: /simulate_payment [user_id] [success|failed|renew|cancel]
    """
    if not message.from_user or message.from_user.id != config.admin_id:
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer(_t("cmd.sim_payment_invalid"))
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer(_t("cmd.sim_user_id_numeric"))
        return

    action = parts[2].lower()
    event_map = {
        "success": "payment.succeeded",
        "failed": "payment.failed",
        "renew": "subscription.renewed",
        "cancel": "subscription.cancelled",
    }
    event_type = event_map.get(action)
    if not event_type:
        await message.answer(_t("cmd.sim_action_invalid"))
        return

    db = SessionLocal()
    try:
        gateway = build_payment_gateway()
        webhook = WebhookService(db, gateway)
        ok = webhook.process_mock_event(event_type=event_type, user_id=user_id)
        if ok and _bot_instance and event_type in ("payment.succeeded", "subscription.renewed"):
            await notify_vip_invite_if_eligible(_bot_instance, user_id)
        if ok:
            await message.answer(
                _t("cmd.sim_payment_ok", event_type=event_type, user_id=user_id),
                parse_mode="Markdown",
            )
        else:
            await message.answer(
                _t("cmd.sim_payment_failed", event_type=event_type, user_id=user_id),
                parse_mode="Markdown",
            )
    finally:
        db.close()


@router.message(Command("simulate_subscription_expiry"))
async def simulate_subscription_expiry_command(message: Message) -> None:
    """
    Simulate subscription expiry transition for local testing.
    Usage: /simulate_subscription_expiry [user_id]
    """
    if not message.from_user or message.from_user.id != config.admin_id:
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(_t("cmd.sim_expiry_invalid"))
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer(_t("cmd.sim_user_id_numeric"))
        return

    db = SessionLocal()
    try:
        service = SubscriptionService(db)
        if service.expire_subscription(user_id):
            await message.answer(_t("cmd.sim_expiry_ok", user_id=user_id), parse_mode="Markdown")
        else:
            await message.answer(_t("cmd.sim_expiry_failed", user_id=user_id), parse_mode="Markdown")
    finally:
        db.close()


# TODO: remove in production if not needed
@router.message(Command("reset_user"))
async def reset_user_command(message: Message) -> None:
    """Admin: permanently delete a user and all related data (full GDPR-style wipe for this bot)."""
    if not message.from_user or message.from_user.id != config.admin_id:
        return
    
    try:
        # Extract user ID from command
        command_parts = message.text.split()
        if len(command_parts) != 2:
            await message.answer(_t("cmd.reset_invalid_command"))
            return

        try:
            target_user_id = int(command_parts[1])
        except ValueError:
            await message.answer(_t("cmd.reset_invalid_id"))
            return

        # Safety: do not allow resetting admin account
        if target_user_id == config.admin_id:
            await message.answer(_t("cmd.reset_safety"))
            return

        db = SessionLocal()
        try:
            # Check if user exists first
            target_user = get_user(db, target_user_id)
            if not target_user:
                await message.answer(_t("cmd.reset_user_not_found", user_id=target_user_id))
                return

            # Reset user completely
            if reset_user_completely(db, target_user_id):
                await message.answer(_t("cmd.reset_success", user_id=target_user_id))
                logger.info(f"Admin reset user {target_user_id}")
            else:
                await message.answer(_t("cmd.reset_failed", user_id=target_user_id))

        except Exception as e:
            logger.error(f"Error resetting user {target_user_id}: {e}")
            await message.answer(_t("cmd.reset_error", user_id=target_user_id, err=e))
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in reset_user command: {e}")
        await message.answer(_t("cmd.reset_command_error"))
