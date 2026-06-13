"""English admin catalog (default + fallback language).

Keys are grouped by admin screen. Placeholders use str.format syntax ({name}).
NEVER translate interpolated values (DB statuses, usernames, Stripe data,
user-generated text) — only the surrounding labels live here.
"""

ADMIN_MESSAGES = {
    # --- Sections / main menu (reply keyboard + inline) --------------------- #
    "menu.user_management": "User Management",
    "menu.questions": "Questions",
    "menu.subscriptions": "Subscriptions & Payment",
    "menu.system": "System Settings",

    # --- Start / home ------------------------------------------------------- #
    "start.title": "👑 <b>AskBot — Admin</b>",
    "start.body": (
        "You are the administrator — <b>no verification or approval is needed</b>.\n\n"
        "Use the <b>keyboard below</b> (two buttons per row) to open a section, "
        "or use the <b>inline</b> shortcuts in the next message.\n"
        "All section actions stay button-driven."
    ),
    "home.title": "🏠 Admin Home Hub",
    "home.desc": "Manage users, questions, subscriptions, and system settings from one place.",
    "home.prompt": "Choose a section below.",

    # --- Common ------------------------------------------------------------- #
    "nav.back": "◀ Back",
    "nav.home": "🏠 Home",
    "common.choose_option": "Choose an option below.",
    "pg.prev": "⬅️ Prev",
    "pg.next": "➡️ Next",
    "pg.prev_arrow": "⬅️",
    "pg.next_arrow": "➡️",
    "btn.open_user": "👤 {tid}",

    # --- User Management dashboard ----------------------------------------- #
    "um.title": "👥 User Management",
    "um.total": "📊 <b>{total}</b> total users",
    "um.line_active_expired": "🟢 Active: <b>{active}</b>\xa0\xa0\xa0🔴 Expired: <b>{expired}</b>",
    "um.line_grace_pending": "⏳ Grace: <b>{grace}</b>\xa0\xa0\xa0📝 Pending: <b>{pending}</b>",
    "um.hint": "Tap a card to drill in, or search for a specific user.",
    "um.card_active": "🟢 Active · {n}",
    "um.card_expired": "🔴 Expired · {n}",
    "um.card_grace": "⏳ Grace · {n}",
    "um.card_pending": "📝 Pending · {n}",
    "um.card_all": "👥 All Users · {n}",
    "um.card_search": "🔍  Search User  🔍",

    # Filtered list titles
    "filter.active_title": "🟢 Active Members",
    "filter.expired_title": "🔴 Expired Members",
    "filter.grace_title": "⏳ Grace Period Users",

    # All-users list
    "ul.empty_title": "👥 User Management Overview",
    "ul.empty_body": "No users are registered in the system yet.",
    "ul.empty_hint": "Users will appear here as soon as they begin onboarding.",
    "ul.header": "<b>All users</b> ({total}) — page {page}",
    "ul.summary_line": (
        "• <code>{tid}</code> {name} {un}\n"
        "  status: <b>{status}</b> | sub: <b>{sub}</b> {plan}\n"
        "  questions used: <b>{used}</b> / {limit}"
    ),

    # Filtered list
    "uf.empty_body": "No members match this status right now.",
    "uf.empty_hint": "They will appear here automatically as subscription states change.",
    "uf.header": "<b>{title}</b> ({total}) — page {page}",

    # Pending approval
    "up.empty_title": "📋 Pending Approval Queue",
    "up.empty_body": "There are currently no users waiting for approval.",
    "up.empty_hint": "New access requests will appear here as soon as they come in.",
    "up.header": "<b>Pending approval</b> ({n})\n\nOpen a user:",

    # --- User detail -------------------------------------------------------- #
    "ud.not_found_popup": "User {tid} not found.\n\nThey may have been removed or never registered.",
    "ud.block": (
        "<b>User</b> <code>{tid}</code>\n"
        "Name: {name}\n"
        "Username: {username}\n"
        "Approval: <b>{approval}</b>\n"
        "User Category: <b>{category}</b>\n"
        "Questions used: <b>{used}</b> / limit {limit}\n\n"
        "{sub_block}"
    ),
    "btn.approve": "✅ Approve",
    "btn.reject": "❌ Reject",
    "btn.reset_user": "🔄 Reset user",
    "btn.expire_sub": "⏹ Expire subscription",
    "btn.grace": "⏳ Grace",
    "btn.activate_sub": "▶️ Activate sub",
    "btn.remove_vip": "🚫 Remove from VIP",

    # Approve
    "approve.cannot": "Cannot approve this user from current state.",

    # Reject
    "rj.title": "❌ Reject Access Request",
    "rj.desc": (
        "Choose a reason for rejecting this user. They will be notified and "
        "removed from the VIP group if currently a member."
    ),
    "rj.prompt": "Pick a reason below.",
    "rj.reason_standards": "Standards",
    "rj.reason_spam": "Spam",
    "rj.reason_other": "Other",
    "rj.failed": "Reject failed",

    # Reset
    "reset.confirm_btn": "⚠️ Confirm reset",
    "reset.ask": "<b>Reset user</b>\n\nThis deletes the user row, subscription, payments, and questions.",
    "reset.done": "Reset done",
    "reset.failed": "Reset failed",
    "reset.removed": "User <code>{tid}</code> removed from database.",
    "reset.failed_page": "Reset failed.",

    # VIP remove
    "vip.not_configured": "VIP group not configured",
    "vip.telegram_err": "Telegram: {err}",

    # --- ID search ---------------------------------------------------------- #
    "ids.btn_cancel": "❌ Cancel",
    "ids.prompt": (
        "<b>🔍 Search User By Telegram ID</b>\n\n"
        "{sep}\n\n"
        "Please send the Telegram ID of the user.\n\n"
        "<i>You can type it manually or paste it from the clipboard. "
        "Telegram IDs are numeric and typically 5 to 15 digits long.</i>\n\n"
        "{sep}"
    ),
    "ids.invalid": (
        "<b>❌ Invalid Telegram ID</b>\n\n"
        "{sep}\n\n"
        "The value you sent doesn't look like a Telegram user id.\n\n"
        "Please send a valid numeric Telegram ID — typically 5 to 15 digits.\n\n"
        "{sep}"
    ),
    "ids.cancelled": "Cancelled",
    "ids.lookup_empty_title": "🔍 User Lookup Result",
    "ids.lookup_empty_body": "No user is registered with Telegram ID <code>{tid}</code>.",
    "ids.lookup_empty_hint": "Double-check the id and try again, or return to User Management.",

    # --- Questions ---------------------------------------------------------- #
    "qm.title": "📌 Questions Management Section",
    "qm.desc": (
        "View pending questions awaiting a reply or browse the full history of "
        "questions submitted by users."
    ),
    "qm.btn_pending": "📌 Pending ({n})",
    "qm.btn_all": "📚 All Submitted Questions ({n})",
    "qm.btn_export_pending": "📤 Export Pending",
    "qm.btn_export_all": "📤 Export All",
    # Question export dataset names (caption + sheet title) + column headers.
    "qexport.name_pending": "Pending Questions",
    "qexport.name_all": "All Questions",
    "qexport.col_id": "Question ID",
    "qexport.col_user_id": "Telegram User ID",
    "qexport.col_username": "Username",
    "qexport.col_full_name": "Full Name",
    "qexport.col_status": "Status",
    "qexport.col_type": "Question Type",
    "qexport.col_text": "Question",
    "qexport.col_reply": "Admin Reply",
    "qexport.col_created": "Created Date",
    "qexport.col_answered": "Answered Date",

    "q.pending_empty_title": "📌 Pending Questions Queue",
    "q.pending_empty_body": "There are no pending questions right now.",
    "q.pending_empty_hint": "Questions awaiting a reply will appear here as soon as users send them.",
    "q.pending_header": "<b>Pending questions</b> ({n})",
    "q.hist_empty_title": "📚 Questions History Overview",
    "q.hist_empty_body": "No questions have been recorded yet.",
    "q.hist_empty_hint": "Every user question (Quick or VIP Legal) will be logged here.",
    "q.hist_header": "<b>All questions</b> ({n})",
    "q.detail": (
        "<b>Question #{id}</b>\n"
        "User: <code>{uid}</code> (@{un})\n"
        "Status: <b>{status}</b>\n"
        "Created: {created}\n\n"
        "<b>Text</b>\n{text}\n"
    ),
    "q.admin_reply_block": "\n<b>Admin reply</b>\n{reply}\n",
    "q.btn_compose": "✍️ Compose reply",
    "q.not_found": "Not found",
    "q.compose_title": "✍️ Compose Reply Mode",
    "q.compose_desc": (
        "Send your <b>next text message</b> in this chat (not a command). "
        "It will be delivered to the user and the question marked answered.\n\n"
        "<i>This is the only step that uses a normal message — after you "
        "pressed the button.</i>"
    ),
    "q.compose_prompt": "Type your reply now, or tap Cancel.",
    "q.btn_cancel_compose": "❌ Cancel compose",
    "q.compose_cancelled_title": "📝 Reply Compose Cancelled",
    "q.compose_cancelled_body": "The pending reply was discarded — nothing was sent.",
    "q.compose_cancelled_hint": "Use the Questions menu below to pick another question.",
    "q.no_longer_pending": "Question is no longer pending.",
    "q.user_blocked": "User blocked the bot. Saved as FAILED_DELIVERY.",
    "q.send_failed": "Send failed: {err}",
    "q.db_update_failed": "Sent to user but DB update failed.",
    "q.answered": "✅ Answered question #{qid}",

    # --- Subscriptions & Payment ------------------------------------------- #
    "sm.title": "📜 Subscriptions &amp; Payment Center",
    "sm.desc": (
        "Browse subscriptions, recent payments, the webhook event log, and the "
        "latest payment per user."
    ),
    "sm.btn_subscriptions": "📜 Subscriptions",
    "sm.btn_recent_payments": "💵 Recent payments",
    "sm.btn_webhook_log": "📡 Webhook log",
    "sm.btn_last_payment": "👤 Last payment / user",

    "sl.empty_title": "📜 Subscription Management Overview",
    "sl.empty_body": "No subscriptions were found.",
    "sl.empty_hint": "Active and past subscriptions will appear here once users subscribe.",
    "sl.header": "<b>Subscriptions</b> ({n})",

    "pay.empty_title": "💵 Recent Payments Overview",
    "pay.empty_body": "No payments have been recorded yet.",
    "pay.empty_hint": "Stripe webhook events will populate this list as soon as users pay.",
    "pay.header": "<b>Recent payments</b> ({n})",

    "wl.empty_title": "📡 Webhook Event Log",
    "wl.empty_body": "No webhook events have been recorded yet.",
    "wl.empty_hint": "Stripe deliveries and other provider events will appear here.",
    "wl.header": "<b>Webhook / event log</b> ({n})",

    "pp.empty_title": "👤 Latest Payment Per User",
    "pp.empty_body": "No payments are linked to any user yet.",
    "pp.empty_hint": "Each user's most-recent payment will be summarized here.",
    "pp.header": "<b>Latest payment per user</b> ({n} users)",

    # Admin subscription readout header (body uses the shared user readout keys)
    "sub.admin_header": "🛠 Admin sub view — user {user_id}",

    # --- System settings ---------------------------------------------------- #
    "sys.title": "⚙️ System Settings Overview",
    "sys.desc": (
        "Read-only snapshot of the live configuration values the bot is running "
        "with. Use Render's dashboard to change them."
    ),
    "sys.lbl_vip_lapse": "VIP lapse removal delay (s):",
    "sys.lbl_vip_sync": "VIP sync interval (s):",
    "sys.lbl_stripe_mode": "Stripe mode:",
    "sys.lbl_stripe_key_set": "Stripe key set:",
    "sys.lbl_webhook_secret_set": "Webhook secret set:",
    "sys.btn_refresh": "🔄 Refresh",
    "sys.btn_language": "🌐 Admin Language",

    # --- User export (Excel) ----------------------------------------------- #
    "export.section_title": "📊 Export Data",
    "export.btn_active": "📗 Export Active Users",
    "export.btn_expired": "📕 Export Expired Users",
    "export.btn_grace": "⏳ Export Grace Users",
    "export.btn_pending": "📄 Export Pending Users",
    "export.btn_all": "📊 Export All Users",
    # Dataset names (used in the file caption + sheet title).
    "export.name_active": "Active Users",
    "export.name_expired": "Expired Users",
    "export.name_grace": "Grace Period Users",
    "export.name_pending": "Pending Approval Users",
    "export.name_all": "All Users",
    "export.generating": "Generating export…",
    "export.caption": "📊 {name} — {n} record(s) exported.",
    "export.empty": "Nothing to export — this list is now empty.",
    "export.failed": "❌ Export failed. Please try again.",
    # Column headers
    "export.col_user_id": "Telegram User ID",
    "export.col_username": "Username",
    "export.col_full_name": "Full Name",
    "export.col_status": "Status",
    "export.col_sub_status": "Subscription Status",
    "export.col_case_type": "Case Type",
    "export.col_created": "Created Date",
    "export.col_approved": "Approval Date",

    # --- Admin language picker --------------------------------------------- #
    "lang.title": "🌐 Admin Language",
    "lang.desc": "Choose the language for the admin interface. English is the default.",
    "lang.prompt": "Select a language below.",
    "lang.current": "Current: {label}",
    "lang.changed": "Language updated.",
    "lang.menu_refreshed": "✅ Menu language updated. The buttons below are now in the new language.",

    # ======================================================================= #
    # Legacy command handlers (app/handlers/admin.py)
    # ======================================================================= #
    "cmd.not_authorized": "❌ You are not authorized to use this command.",

    # Command palette ("/" menu) descriptions for the admin.
    "cmd_desc.start": "Open the admin panel",
    "cmd_desc.help": "Admin help",
    "cmd_desc.status": "Admin status",
    "cmd_desc.language": "Change admin language",
    "cmd_desc.pending": "Pending approvals",
    "cmd_desc.users": "List users",
    "cmd_desc.stats": "User statistics",

    # Admin /status (admin never sees the user verification status flow).
    "cmd.admin_status_title": "👑 Admin Status",
    "cmd.admin_status_body": (
        "You are the administrator — full access, no verification or approval needed.\n"
        "Use the section buttons below to manage the bot."
    ),

    # /approve
    "cmd.approve_invalid_format": (
        "❌ Invalid format. Use: /approve [user_id]\n\nExample: /approve 123456789"
    ),
    "cmd.approve_invalid_id": (
        "❌ Invalid user ID. Please provide a numeric user ID.\n\nExample: /approve 123456789"
    ),
    "cmd.user_not_found": "❌ User {user_id} not found in database.",
    "cmd.approve_not_verified": "❌ User {user_id} has not been verified yet.",
    "cmd.approve_not_requested": "❌ User {user_id} has not requested access yet.",
    "cmd.approve_already": "✅ User {user_id} is already approved.",
    "cmd.approve_not_pending": "❌ User {user_id} is not pending approval.",
    "cmd.approve_failed": "❌ Failed to approve user. Please try again.",
    "cmd.approve_success": (
        "✅ User {user_id} has been approved.\n\n"
        "They were notified in private chat. The VIP invite is sent only after "
        "they have an active subscription (or valid grace)."
    ),
    "cmd.approve_error": "❌ An error occurred while processing the approval.",
    "cmd.approve_not_pending_status": "❌ User {user_id} is not pending approval (status: {status}).",

    # /reject
    "cmd.reject_invalid_format": (
        "❌ **Invalid Format**\n\n"
        "Usage: `/reject [user_id] [reason]`\n\n"
        "Example: `/reject 123456789 Inappropriate content`\n\n"
        "Reason is optional"
    ),
    "cmd.reject_invalid_id": (
        "❌ **Invalid User ID**\n\n"
        "User ID must be a numeric value.\n\n"
        "Example: `/reject 123456789`"
    ),
    "cmd.reject_user_not_found": "❌ **User Not Found**\n\nUser {user_id} not found in database.",
    "cmd.reject_already": "⚠️ **Already Rejected**\n\nUser {user_id} is already rejected.",
    "cmd.reject_db_error": "❌ **Database Error**\n\nFailed to update user status. Please try again.",
    "cmd.reject_db_error_process": "❌ **Database Error**\n\nFailed to process rejection. Please try again.",
    "cmd.reject_system_error": "❌ **System Error**\n\nAn unexpected error occurred. Please try again.",
    "cmd.reject_success": (
        "✅ **User Rejected Successfully**\n\n"
        "User ID: {user_id}\n"
        "Reason: {reason}\n\n"
        "**Operations:**\n"
        "• Database update: ✅ Success\n"
        "• Notification sent: {notif}\n"
    ),
    "cmd.op_success": "✅ Success",
    "cmd.op_failed": "❌ Failed",
    "cmd.reject_group_removal": "• Group removal: {result}\n",
    "cmd.reject_group_skipped": "• Group removal: ⏭ Skipped\n",
    "cmd.reject_db_error_cb": "❌ **Database Error**\n\nFailed to reject user {user_id}. Please try again.",
    "cmd.cb_invalid_user_id": "❌ Invalid user ID in callback data",
    "cmd.cb_approve_error": "❌ Error processing approval",
    "cmd.cb_reject_error": "❌ Error processing rejection",

    # /pending
    "cmd.pending_empty": (
        "<b>📋 Pending Approval Queue</b>\n\n"
        "{sep}\n\n"
        "There are currently no users waiting for approval.\n\n"
        "New access requests will appear here as soon as they come in.\n\n"
        "{sep}"
    ),
    "cmd.pending_header": "📋 Users Pending Approval:\n\n",
    "cmd.pending_row": "🆔 User ID: {user_id}\n💡 Approve with: /approve {user_id}\n\n",
    "cmd.pending_error": "❌ An error occurred while fetching pending users.",

    # /users
    "cmd.users_empty": (
        "<b>👥 User Management Overview</b>\n\n"
        "{sep}\n\n"
        "No users are registered in the system yet.\n\n"
        "Users will appear here as soon as they begin onboarding.\n\n"
        "{sep}"
    ),
    "cmd.users_header": "👥 All Users List:\n\n",
    "cmd.users_row": (
        "{role_emoji} **{first_name}**\n"
        "🆔 ID: `{telegram_id}`\n"
        "👤 Username: {username_display}\n"
        "🔷 Role: {role_name}\n\n"
    ),
    "cmd.users_no_username": "No username",
    "cmd.role_new": "New User",
    "cmd.role_verified": "Verified",
    "cmd.role_pending": "Pending Approval",
    "cmd.role_approved": "Approved",
    "cmd.role_unknown": "Unknown",
    "cmd.users_error": "❌ An error occurred while fetching users list.",

    # /stats
    "cmd.stats": (
        "📊 User Statistics:\n\n"
        "🆕 New Users: {new}\n"
        "✅ Verified Users: {verified}\n"
        "⏳ Pending Approval: {pending}\n"
        "🎉 Approved Users: {approved}\n\n"
        "📈 Total Users: {total}"
    ),
    "cmd.stats_error": "❌ An error occurred while fetching statistics.",

    # /sub_* commands
    "cmd.sub_status_usage": "Usage: /sub_status [user_id]",
    "cmd.sub_activate_usage": "Usage: /sub_activate [user_id]",
    "cmd.sub_expire_usage": "Usage: /sub_expire [user_id]",
    "cmd.sub_grace_usage": "Usage: /sub_grace [user_id] [grace_days]",
    "cmd.invalid_user_id_numeric": "Invalid user_id (must be numeric).",
    "cmd.grace_days_numeric": "grace_days must be numeric.",
    "cmd.sub_activated": "✅ Activated.",
    "cmd.sub_activate_failed": "❌ Activation failed (see logs).",
    "cmd.sub_expired": "✅ Marked EXPIRED.",
    "cmd.sub_expire_failed": "❌ No subscription row to expire.",
    "cmd.sub_grace_ok": "✅ Moved to GRACE.",
    "cmd.sub_grace_failed": "❌ Grace transition failed (see logs).",

    # /admin_help
    "cmd.admin_menu_btn_users": "📋 Show Users List",
    "cmd.admin_menu_btn_pending": "⏳ Show Pending Users",
    "cmd.admin_menu_btn_stats": "📊 Show Statistics",
    "cmd.admin_menu_btn_help": "❓ Admin Help",
    "cmd.admin_menu_text": (
        "🔧 Admin Menu\n\n"
        "Available commands:\n"
        "/approve [user_id] - Approve pending users\n"
        "/reject [user_id] [reason] - Reject pending users\n"
        "/users - Show all users with details\n"
        "/pending - Show all users pending approval\n"
        "/stats - View user statistics\n"
        "/simulate_payment [user_id] [success|failed|renew|cancel] - Simulate payment event\n"
        "/simulate_subscription_expiry [user_id] - Simulate subscription expiry\n"
        "/sub_status [user_id] - Subscription + entitlement snapshot\n"
        "/sub_activate [user_id] - Activate subscription (service layer)\n"
        "/sub_expire [user_id] - Force-expire latest subscription\n"
        "/sub_grace [user_id] [days] - Move subscription to grace\n"
        "/admin_help - Show this menu\n\n"
        "Or use the buttons below for quick actions:"
    ),

    # admin /start welcome
    "cmd.admin_welcome": (
        "👑 **Admin Welcome**\n\n"
        "You are automatically approved as an administrator.\n\n"
        "🔧 **Admin Features Available:**\n"
        "• `/approve [user_id]` - Approve pending users\n"
        "• `/pending` - View pending users\n"
        "• `/users` - View all users\n"
        "• `/stats` - View user statistics\n"
        "• Group message moderation\n"
        "• Question forwarding and replies\n\n"
        "📊 **Your Status:** APPROVED\n"
        "🎯 **Questions:** Unlimited\n\n"
        "Ready to manage the VIP group!"
    ),
    "cmd.admin_setup_error": (
        "❌ **Admin Setup Error**\n\n"
        "There was an error setting up your admin account. Please try again."
    ),

    # /retry
    "cmd.retry_invalid_command": (
        "❌ **Invalid Command**\n\nUsage: `/retry [question_id]`\n\nExample: `/retry 123`"
    ),
    "cmd.retry_invalid_id": (
        "❌ **Invalid Question ID**\n\nQuestion ID must be a number.\n\nExample: `/retry 123`"
    ),
    "cmd.retry_not_found": (
        "❌ **Question Not Found**\n\n"
        "Question {question_id} not found or not in FAILED_DELIVERY status."
    ),
    "cmd.retry_no_bot": "❌ Bot instance not available.",
    "cmd.retry_success": (
        "✅ **Retry Successful**\n\n"
        "Question {question_id} successfully delivered to user {user_id}."
    ),
    "cmd.retry_partial": (
        "⚠️ **Partial Success**\n\n"
        "Message sent to user but failed to update database status."
    ),
    "cmd.retry_failed": (
        "❌ **Retry Failed**\n\nFailed to deliver question {question_id} to user: {err}"
    ),
    "cmd.retry_error": "❌ An error occurred while processing the retry command.",

    # /simulate_payment
    "cmd.sim_payment_invalid": (
        "❌ **Invalid Command**\n\n"
        "Usage: `/simulate_payment [user_id] [success|failed|renew|cancel]`"
    ),
    "cmd.sim_user_id_numeric": "❌ User ID must be numeric.",
    "cmd.sim_action_invalid": "❌ Action must be one of: success, failed, renew, cancel",
    "cmd.sim_payment_ok": "✅ Simulated `{event_type}` for user `{user_id}`",
    "cmd.sim_payment_failed": "❌ Failed to simulate `{event_type}` for user `{user_id}`",

    # /simulate_subscription_expiry
    "cmd.sim_expiry_invalid": (
        "❌ **Invalid Command**\n\nUsage: `/simulate_subscription_expiry [user_id]`"
    ),
    "cmd.sim_expiry_ok": "✅ Simulated subscription expiry for user `{user_id}`",
    "cmd.sim_expiry_failed": "❌ No active subscription found for user `{user_id}`",

    # /reset_user
    "cmd.reset_invalid_command": (
        "❌ **Invalid Command**\n\n"
        "Usage: `/reset_user [telegram_user_id]`\n\n"
        "Example: `/reset_user 7285268952`"
    ),
    "cmd.reset_invalid_id": (
        "❌ **Invalid User ID**\n\nUser ID must be a number.\n\nExample: `/reset_user 7285268952`"
    ),
    "cmd.reset_safety": "❌ **Safety Error**\n\nCannot reset the admin account.",
    "cmd.reset_user_not_found": "❌ **User Not Found**\n\nUser {user_id} not found in database.",
    "cmd.reset_success": (
        "✅ User {user_id} was fully removed from the database.\n\n"
        "All questions, subscription, and payment rows for this ID are deleted.\n"
        "They will be treated as a brand-new user the next time they send /start."
    ),
    "cmd.reset_failed": "❌ **Reset Failed**\n\nFailed to reset user {user_id}. Please try again.",
    "cmd.reset_error": "❌ **Reset Error**\n\nAn error occurred while resetting user {user_id}: {err}",
    "cmd.reset_command_error": "❌ An error occurred while processing reset command.",
}
