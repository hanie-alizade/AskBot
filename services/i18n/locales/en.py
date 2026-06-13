"""English locale (source of truth — all keys defined here)."""

MESSAGES = {
    # ===== Command palette ("/" menu) descriptions =====
    "cmd_desc.start": "Start / restart the bot",
    "cmd_desc.menu": "Open the main menu",
    "cmd_desc.status": "Check your status",
    "cmd_desc.subscription": "Subscription & billing",
    "cmd_desc.language": "Change language",
    "cmd_desc.help": "Show help",

    # ===== Language picker =====
    "lang.picker_first_time": "🌐 Welcome! Please choose your language:",
    "lang.picker_change": "🌐 Select a language:",
    "lang.set_confirmation": "✅ Language set to English.",

    # ===== Buttons =====
    "btn.verify": "✅ Verify",
    "btn.check_status": "📊 Check Status",
    "btn.help": "❓ Help",
    "btn.request_access": "🔑 Request Access",
    "btn.join_vip": "🎉 Join VIP Group",
    "btn.subscription": "📊 Subscription",

    # ===== Verify =====
    "verify.welcome_new": (
        "👋 Welcome to AskBot!\n\n"
        "To get started, please verify your account by clicking the button below."
    ),

    # ===== Legal acceptance flow =====
    "legal.intro": (
        "📄 <b>Onboarding — Legal acceptance</b>\n\n"
        "Please review and accept each document below. "
        "You must accept all four to continue."
    ),
    "legal.finalize_btn": "✅ All accepted — continue",
    "legal.back_btn": "↩️ Back to documents",
    "legal.alert_accepted": "Recorded ✅",
    "legal.alert_incomplete": "Please accept all four documents to continue.",
    "legal.gate_message": (
        "📄 You must accept the legal documents before you can continue."
    ),
    "legal.gate_message_alert": (
        "Please complete legal acceptance to continue. Tap below to resume."
    ),
    "verify.welcome_verified": (
        "✅ You are verified!\n\n"
        "You can now request access to the VIP group by clicking the button below."
    ),
    "verify.welcome_pending": (
        "⏳ Your access request is currently under review.\n\n"
        "Please wait for an admin to approve your request. "
        "You'll be notified once a decision is made."
    ),
    "verify.welcome_approved_vip": (
        "You are approved and your subscription is active.\n\n"
        "Use the button below to open the VIP group invite."
    ),
    "verify.welcome_approved_no_sub": (
        "You are approved. Activate a subscription to get the VIP group invite.\n\n"
        "Use /subscription and /subscribe (or /renew) in private chat with this bot."
    ),
    "verify.complete": (
        "✅ Verification complete!\n\n"
        "You can now request access to VIP group by clicking the button below."
    ),
    "verify.alert_already_verified": "❌ You are already verified!",
    "verify.alert_success": "✅ Successfully verified!",

    # ===== Status =====
    "status.not_registered_callback": (
        "📊 Your Current Status: ❓ Not Registered\n\n"
        "You haven't started the verification process yet.\n\n"
        "👉 Please click the '✅ Verify' button to begin the registration process."
    ),
    "status.not_registered_dm": (
        "📊 Your Current Status: ❓ Not Registered\n\n"
        "You haven't started the verification process yet.\n\n"
        "👉 Please send /start to begin the registration process."
    ),
    "status.label": "📊 Your Current Status: {status}",
    "status.new": "🆕 New User - Please verify your account",
    "status.verified": "✅ Verified - You can request access",
    "status.pending": "⏳ Pending Approval - Your request is under review",
    "status.approved": "🎉 Approved - You have access to the VIP group",
    "status.rejected": "❌ Rejected - Your access request has been denied",
    "status.unknown": "❓ Unknown Status",
    "status.vip_active": "\n💳 VIP entitlement: Active",
    "status.vip_inactive": "\n💳 VIP entitlement: Inactive (subscription required)",
    "status.billing_link": "\n\n📎 Billing & access: /subscription",

    # ===== Help =====
    "help.title": "🤖 AskBot Help\n\n",
    "help.new": (
        "Available commands:\n"
        "/start - Begin verification process\n"
        "/help - Show this help message\n"
        "/status - Check your current status\n"
        "/language - Change language\n\n"
        "Click the 'Verify' button to get started!"
    ),
    "help.verified": (
        "Available commands:\n"
        "/start - Show access request option\n"
        "/help - Show this help message\n"
        "/status - Check your current status\n"
        "/language - Change language\n\n"
        "Click the 'Request Access' button to continue!"
    ),
    "help.pending": (
        "Available commands:\n"
        "/start - Show pending status\n"
        "/help - Show this help message\n"
        "/status - Check your current status\n"
        "/language - Change language\n\n"
        "Your request is under review. Please wait for admin approval."
    ),
    "help.approved_with_vip": (
        "Available commands:\n"
        "/start - Show approved status\n"
        "/menu - Your dashboard\n"
        "/benefits - Membership benefits\n"
        "/rules - Community rules\n"
        "/privacy - Privacy policy\n"
        "/terms - Terms & Conditions\n"
        "/disclaimer - Disclaimer\n"
        "/help - Show this help message\n"
        "/status - Check your current status\n"
        "/language - Change language\n\n"
        "You have access to the VIP group! Check your messages for the invite link."
    ),
    "help.approved_billing": (
        "Available commands:\n"
        "/start - Show approved status\n"
        "/menu - Your dashboard\n"
        "/benefits - Membership benefits\n"
        "/rules - Community rules\n"
        "/privacy - Privacy policy\n"
        "/terms - Terms & Conditions\n"
        "/disclaimer - Disclaimer\n"
        "/help - Show this help message\n"
        "/status - Check your current status\n"
        "/language - Change language\n\n"
        "You are approved. After an active subscription, you get the VIP invite "
        "in private chat. Use /subscription."
    ),

    # ===== Access =====
    "access.alert_cannot_request": "❌ You cannot request access at this stage!",
    "access.alert_already_pending": "⏳ Your request is already under review!",
    "access.submitted": (
        "📝 Your access request has been submitted!\n\n"
        "⏳ Your request is now under review. "
        "An admin will review your request and you'll be notified once a decision is made.\n\n"
        "Please be patient - this usually takes a few hours."
    ),
    "access.alert_submitted": "✅ Request submitted!",

    # ===== Questions =====
    "q.access_required_status": (
        "❌ Access required\n\n"
        "Your current status: {status}\n\n"
        "You need to be approved to ask questions.\n"
        "Please start the verification process by sending /start"
    ),
    "q.subscription_inactive": (
        "❌ Your subscription is inactive or expired.\n"
        "Use /renew to restore access."
    ),
    "q.empty": "❌ Empty Question\n\nPlease send a meaningful question.",
    "q.too_short": (
        "❌ Question Too Short\n\n"
        "Please send a more detailed question (at least 3 characters)."
    ),
    "q.too_long": (
        "❌ Question Too Long\n\n"
        "Please shorten your question to {limit} characters or fewer. "
        "Your message is currently {length} characters."
    ),
    "q.invalid": "❌ Invalid Question\n\nPlease send a meaningful question.",
    "q.cooldown": "⏳ Please Wait\n\nPlease wait a few seconds before sending another question.",
    "q.duplicate": "⚠️ Duplicate Question\n\nYou already sent this question recently.",
    "q.limit_reached": (
        "❌ VIP Legal Question Limit Reached\n\n"
        "You have used your monthly allowance of {limit} VIP Legal questions.\n\n"
        "Your quota resets on the 1st of next month."
    ),
    "q.access_required_simple": (
        "❌ Access Required\n\n"
        "You need to be approved to ask questions.\n\n"
        "Please start the verification process by sending /start"
    ),

    # ===== State-aware deny messages =====
    # Used when the user has no row in our DB at all — they really do need to /start.
    "q.deny_not_registered": (
        "👋 Welcome!\n\n"
        "You're not registered yet. Send /start to begin."
    ),
    # Legal acceptance missing during initial onboarding (no documents accepted yet).
    "q.deny_legal_pending": (
        "📄 <b>Legal Acceptance Required</b>\n\n"
        "You must complete the legal acceptance process before continuing.\n\n"
        "Tap the button below to resume where you left off."
    ),
    # Legal acceptance missing because a document version was bumped (some accepted).
    "q.deny_legal_updated": (
        "📄 <b>Updated Legal Documents</b>\n\n"
        "We've updated one or more of our legal documents. "
        "Please re-accept the latest versions to continue.\n\n"
        "Tap the button below to resume."
    ),
    # user_not_approved + status=NEW (verified but didn't tap Verify yet — shouldn't happen,
    # but be defensive).
    "q.deny_new_user": (
        "📄 <b>Onboarding Required</b>\n\n"
        "Please complete the onboarding flow first. "
        "Use /menu to see where you are, or send /start to resume."
    ),
    # user_not_approved + status=VERIFIED (accepted legals, has not requested access yet).
    "q.deny_must_request_access": (
        "✅ You're verified.\n\n"
        "You still need to request access before you can ask questions. "
        "Tap the button below."
    ),
    # user_not_approved + status=PENDING_APPROVAL.
    "q.deny_pending_approval": (
        "⏳ <b>Awaiting Admin Approval</b>\n\n"
        "Your request has been submitted and is waiting for admin approval. "
        "You'll be notified once a decision is made."
    ),
    # user_not_approved + status=REJECTED.
    "q.deny_rejected": (
        "❌ <b>Access Rejected</b>\n\n"
        "Your access request was rejected. "
        "If you believe this is a mistake, please contact an admin."
    ),
    # user_not_approved + unknown status (shouldn't happen — kept as a safety net).
    "q.deny_unknown_status": (
        "❌ Access Required\n\n"
        "Your current status is {status}. "
        "Use /menu to see your dashboard."
    ),
    # APPROVED but no subscription row at all → needs to subscribe.
    "q.deny_no_subscription": (
        "💳 <b>Subscription Required</b>\n\n"
        "You're approved! To ask VIP Legal questions, please subscribe.\n\n"
        "Use /subscribe to start your subscription."
    ),
    # APPROVED, has a sub, but it ended.
    "q.deny_subscription_expired": (
        "💳 <b>Subscription Expired</b>\n\n"
        "Your subscription has expired. Use /subscribe to renew and restore access."
    ),
    # APPROVED, sub was CANCELLED and the paid period has now passed.
    "q.deny_subscription_cancelled": (
        "💳 <b>Subscription Cancelled</b>\n\n"
        "Your subscription was cancelled and the paid period has ended. "
        "Use /subscribe to start a new subscription."
    ),
    # APPROVED, sub in GRACE/PAST_DUE but grace window expired.
    "q.deny_grace_expired": (
        "💳 <b>Grace Period Ended</b>\n\n"
        "Your payment grace period has ended. "
        "Use /subscribe to restore access."
    ),
    # APPROVED, sub INACTIVE / PENDING_PAYMENT / SUSPENDED.
    "q.deny_subscription_inactive": (
        "💳 <b>Subscription Inactive</b>\n\n"
        "Your subscription is not active. Use /subscribe to activate it."
    ),
    # ===== Buttons used by state-aware deny replies =====
    "btn.resume_legal": "📄 Resume Legal Acceptance",
    "btn.request_access_now": "🔑 Request Access",
    "q.system_error": (
        "❌ System Error\n\n"
        "Sorry, there was an error processing your question. Please try again later."
    ),
    "q.system_error_user_not_found": "❌ System Error\n\nUser not found. Please try again.",
    "q.system_error_generic": (
        "❌ System Error\n\n"
        "There was an error processing your question. Please try again."
    ),
    "q.received": (
        "✅ Question Received\n\n"
        "Your question has been sent to the admin.\n\n"
        "📊 Remaining VIP Legal questions this month: {remaining}/{limit}\n\n"
        "You'll receive a response as soon as possible."
    ),
    "q.received_quick": (
        "✅ Quick Question Received\n\n"
        "Your question has been sent to the admin.\n\n"
        "🟢 Quick Questions are unlimited and do not consume your monthly VIP Legal quota.\n\n"
        "You'll receive a response as soon as possible."
    ),
    "q.pick_type_prompt": (
        "❓ <b>What type of question is this?</b>\n\n"
        "🟢 <b>Quick Question</b> — fast clarifications. Unlimited, no quota.\n"
        "⚖️ <b>VIP Legal Question</b> — uses 1 of your {limit} monthly slots ({remaining} remaining).\n\n"
        "<i>Your message:</i>\n{preview}"
    ),
    "q.pick_type_quick_btn": "🟢 Quick Question",
    "q.pick_type_vip_btn": "⚖️ VIP Legal Question",
    "q.pick_type_cancel_btn": "❌ Cancel",
    "q.pick_type_cancelled": "❌ Cancelled — your question was not sent.",
    "q.pick_type_expired": (
        "⏳ Your question expired before you picked a type.\n\n"
        "Please send the question again to retry."
    ),
    # ===== Admin-driven question-type override notifications =====
    "q.admin_typed_to_quick": (
        "🟢 <b>Question Type Updated</b>\n\n"
        "After review, your question has been classified as a <b>Quick Question</b>.\n\n"
        "This question does not consume any of your monthly VIP Legal question allowance.\n\n"
        "Remaining VIP Legal questions this month: {remaining}/{limit}"
    ),
    "q.admin_typed_to_vip": (
        "⚖️ <b>Question Type Updated</b>\n\n"
        "After review, your question has been classified as a <b>VIP Legal Question</b>.\n\n"
        "VIP Legal questions count toward your monthly allowance.\n\n"
        "Remaining VIP Legal questions this month: {remaining}/{limit}\n\n"
        "Thank you for your understanding."
    ),
    "q.admin_typed_to_vip_blocked": (
        "⚖️ <b>Question Review Result</b>\n\n"
        "After review, your question has been classified as a <b>VIP Legal Question</b>.\n\n"
        "Your monthly VIP Legal allowance has already been fully used ({used}/{limit}).\n\n"
        "Because no remaining VIP Legal questions are available this month, "
        "this question cannot be processed.\n\n"
        "Your allowance will reset at the beginning of next month."
    ),
    "q.error_generic": "❌ Error\n\nThere was an error processing your question. Please try again.",
    "q.error_forwarding": (
        "❌ Error\n\n"
        "Your question was received but there was an error forwarding it. Please try again."
    ),
    "q.text_only": (
        "❌ Text Only\n\n"
        "Please send your questions as text messages only.\n\n"
        "Images, files, and other content are not supported at this time."
    ),
    "q.admin_response": (
        "📨 Admin Response\n\n"
        "❓ Your Question:\n{question}\n\n"
        "💬 Response:\n{reply}\n\n"
        "---\n"
        "This is a response to your question. You can reply to this message if you need clarification."
    ),

    # ===== Subscription commands =====
    "sub.cmd_not_approved": (
        "You need an approved account before subscribing.\n"
        "Use /start to continue onboarding."
    ),
    "sub.cmd_mock_success": (
        "✅ Mock payment applied. Your subscription has been updated.\n"
        "Use /subscription to see details."
    ),
    "sub.cmd_mock_failed": "❌ Mock activation failed. Please try again or contact an admin.",

    # ===== Stripe Checkout prompt (inline button — no raw URL in body) =====
    "btn.subscribe_now": "💳 Subscribe Now",
    "sub.checkout_prompt": (
        "💳 Subscription\n\n"
        "Click the button below to complete your subscription."
    ),
    "sub.checkout_reuse_prompt": (
        "💳 Subscription\n\n"
        "You already have an active payment session. "
        "Tap the button below to complete it."
    ),

    # ===== Subscription readout =====
    "sub.readout_title": "📋 Subscription",
    "sub.readout_account_status": "• Account status: {status}",
    "sub.readout_sub_state": "• Subscription state: {state}",
    "sub.readout_billing_mode": "• Billing mode: {mode}",
    "sub.readout_plan": "• Plan: {plan}",
    "sub.readout_period_end": "• Period end: {date}",
    "sub.readout_grace_until": "• Grace until: {date}",
    "sub.readout_can_ask": "• Can ask questions: {yes_no}",
    "sub.readout_access_detail": "• Access detail: {reason}",
    "sub.readout_yes": "Yes",
    "sub.readout_no": "No",
    "sub.readout_dash": "—",
    "sub.next_good_to_go": "✅ You are good to go. Use /status anytime.",
    "sub.next_complete_onboarding": "➡️ Complete onboarding: /start",
    "sub.next_mock_subscribe": (
        "➡️ Try /subscribe to activate (mock), or ask an admin if you need help."
    ),
    "sub.next_not_configured": "➡️ Billing is not live yet. Watch for updates from admins.",
    "sub.next_use_renew": "➡️ Use /renew when checkout is available, or contact support.",
    "sub.placeholder_msg": (
        "💳 Subscribe\n\n"
        "Online checkout is not enabled yet. "
        "You will be able to renew here once billing goes live.\n\n"
        "If you need access urgently, contact an admin."
    ),

    # ===== Persistent reply-keyboard menu =====
    "menu.btn_check_status": "📊 Check approval status",
    "menu.btn_subscription": "💳 Subscription",
    "menu.btn_change_language": "🌐 Change language",
    "menu.btn_benefits": "🎁 Membership benefits",
    "menu.btn_rules": "📋 Rules",
    "menu.btn_rights": "⚖️ Rights & Obligations",
    "menu.btn_privacy": "📄 Privacy Policy",
    "menu.btn_terms": "📄 Terms",
    "menu.btn_disclaimer": "📄 Disclaimer",
    "menu.btn_my_questions": "📚 My Questions",
    "menu.installed": "📋 Use the menu below to navigate.",

    # ===== User segmentation (onboarding category step) =====
    "category.prompt": (
        "🗂 <b>Please select your category</b>\n\n"
        "This helps us tailor support to your situation."
    ),
    "category.btn_students": "🎓 Students",
    "category.btn_work_permits": "💼 Work Permits",
    "category.btn_residency": "🏠 Residency",
    "category.btn_other": "✳️ Other",
    "category.other_prompt": (
        "✍️ Please type your category in a few words "
        "(for example: “Family reunification”)."
    ),
    "category.saved": "✅ Category saved.",
    "category.invalid_custom": "Please send your category as a short line of text.",

    # ===== VIP invite (sent from services/vip_invite.py) =====
    "vip.invite": (
        "🎉 Your subscription is active.\n\n"
        "You can join the VIP group using this invite link:\n\n"
        "{link}\n\n"
        "Welcome to the community."
    ),

    # ===== Admin → user notifications (admin.py) =====
    "admin.user_approved": (
        "🎉 Your access request was approved.\n\n"
        "Use /subscription to see your billing status, and /subscribe or /renew "
        "to activate a plan when available.\n\n"
        "You will receive a separate private message with the VIP group invite link "
        "once your subscription is active (including a valid grace period)."
    ),
    "admin.user_rejected": (
        "❌ Access Request Rejected\n\n"
        "Your request for VIP group access has been denied.\n\n"
        "Reason: {reason}\n\n"
        "If you believe this is an error, please contact an administrator.\n\n"
        "You may submit a new request after addressing the issue."
    ),

    # ===== Group moderation private DMs (group_moderation.py) =====
    "group.private_subscription_required": (
        "Your message in the VIP group was removed (announcements only).\n\n"
        "You need an active subscription to forward questions from the group. "
        "Use /subscription to check status, then /subscribe or /renew when eligible."
    ),
    "group.private_redirect_unapproved": (
        "Your message in the VIP group was removed to keep the channel clean.\n\n"
        "Please use private chat with this bot to continue onboarding or ask questions "
        "once you are approved and subscribed."
    ),
    "group.forward_offer": (
        "Your message in the VIP group was removed (announcements only).\n\n"
        "Would you like to send this question to the admin instead?\n\n"
        "—\n{preview}"
    ),
    "group.non_text_notice": (
        "Your post in the VIP group was removed. Only text can be forwarded as a question.\n\n"
        "Send your question in private chat with this bot if you need help."
    ),
    "group.btn_yes": "Yes",
    "group.btn_no": "No",
    "group.offer_cancelled_toast": "Cancelled",
    "group.offer_expired": (
        "That offer expired. Please send your question again from the group or in private chat."
    ),
}
