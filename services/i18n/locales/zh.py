"""Simplified Chinese locale."""

MESSAGES = {
    # ===== Command palette ("/" menu) descriptions =====
    "cmd_desc.start": "启动 / 重启机器人",
    "cmd_desc.menu": "打开主菜单",
    "cmd_desc.status": "查看你的状态",
    "cmd_desc.subscription": "订阅与账单",
    "cmd_desc.language": "切换语言",
    "cmd_desc.help": "显示帮助",

    # ===== Language picker =====
    "lang.picker_first_time": "🌐 欢迎！请选择您的语言：",
    "lang.picker_change": "🌐 选择语言：",
    "lang.set_confirmation": "✅ 语言已切换为中文。",

    # ===== Buttons =====
    "btn.verify": "✅ 验证",
    "btn.check_status": "📊 查看状态",
    "btn.help": "❓ 帮助",
    "btn.request_access": "🔑 申请访问",
    "btn.join_vip": "🎉 加入 VIP 群",
    "btn.subscription": "📊 订阅",

    # ===== Verify =====
    "verify.welcome_new": (
        "👋 欢迎使用 AskBot！\n\n"
        "请点击下方按钮验证您的账户以开始使用。"
    ),
    "verify.welcome_verified": (
        "✅ 您已通过验证！\n\n"
        "请点击下方按钮申请加入 VIP 群。"
    ),
    "verify.welcome_pending": (
        "⏳ 您的访问申请正在审核中。\n\n"
        "请等待管理员批准。审核结果出来后会通知您。"
    ),
    "verify.welcome_approved_vip": (
        "您的账户已通过批准，且订阅有效。\n\n"
        "请点击下方按钮打开 VIP 群邀请。"
    ),
    "verify.welcome_approved_no_sub": (
        "您的账户已通过批准。请激活订阅以获取 VIP 群邀请。\n\n"
        "在与本机器人的私聊中使用 /subscription 和 /subscribe（或 /renew）。"
    ),
    "verify.complete": (
        "✅ 验证完成！\n\n"
        "请点击下方按钮申请加入 VIP 群。"
    ),
    "verify.alert_already_verified": "❌ 您已通过验证！",
    "verify.alert_success": "✅ 验证成功！",

    # ===== Status =====
    "status.not_registered_callback": (
        "📊 当前状态：❓ 未注册\n\n"
        "您还没有开始验证流程。\n\n"
        "👉 请点击 '✅ 验证' 按钮开始注册流程。"
    ),
    "status.not_registered_dm": (
        "📊 当前状态：❓ 未注册\n\n"
        "您还没有开始验证流程。\n\n"
        "👉 请发送 /start 开始注册流程。"
    ),
    "status.label": "📊 当前状态：{status}",
    "status.new": "🆕 新用户 - 请先验证账户",
    "status.verified": "✅ 已验证 - 可申请访问",
    "status.pending": "⏳ 等待批准 - 申请审核中",
    "status.approved": "🎉 已批准 - 您可以访问 VIP 群",
    "status.rejected": "❌ 已拒绝 - 您的访问申请被拒绝",
    "status.unknown": "❓ 未知状态",
    "status.vip_active": "\n💳 VIP 权益：有效",
    "status.vip_inactive": "\n💳 VIP 权益：无效（需要订阅）",
    "status.billing_link": "\n\n📎 账单与访问：/subscription",

    # ===== Help =====
    "help.title": "🤖 AskBot 帮助\n\n",
    "help.new": (
        "可用命令：\n"
        "/start - 开始验证流程\n"
        "/help - 显示此帮助\n"
        "/status - 查看您的当前状态\n"
        "/language - 切换语言\n\n"
        "请点击 '验证' 按钮开始使用！"
    ),
    "help.verified": (
        "可用命令：\n"
        "/start - 显示访问申请选项\n"
        "/help - 显示此帮助\n"
        "/status - 查看您的当前状态\n"
        "/language - 切换语言\n\n"
        "请点击 '申请访问' 按钮继续！"
    ),
    "help.pending": (
        "可用命令：\n"
        "/start - 显示等待批准状态\n"
        "/help - 显示此帮助\n"
        "/status - 查看您的当前状态\n"
        "/language - 切换语言\n\n"
        "您的申请正在审核中。请等待管理员批准。"
    ),
    "help.approved_with_vip": (
        "可用命令：\n"
        "/start - 显示已批准状态\n"
        "/help - 显示此帮助\n"
        "/status - 查看您的当前状态\n"
        "/language - 切换语言\n\n"
        "您可以访问 VIP 群！请查收邀请链接。"
    ),
    "help.approved_billing": (
        "可用命令：\n"
        "/start - 显示已批准状态\n"
        "/help - 显示此帮助\n"
        "/status - 查看您的当前状态\n"
        "/language - 切换语言\n\n"
        "您的账户已通过批准。激活订阅后，您将在私聊中收到 VIP 邀请。"
        "请使用 /subscription。"
    ),

    # ===== Access =====
    "access.alert_cannot_request": "❌ 当前阶段无法申请访问！",
    "access.alert_already_pending": "⏳ 您的申请已在审核中！",
    "access.submitted": (
        "📝 您的访问申请已提交！\n\n"
        "⏳ 申请正在审核中。"
        "管理员将进行审核，审核结果出来后会通知您。\n\n"
        "请耐心等待 - 通常需要几个小时。"
    ),
    "access.alert_submitted": "✅ 申请已提交！",

    # ===== Questions =====
    "q.access_required_status": (
        "❌ 需要访问权限\n\n"
        "当前状态：{status}\n\n"
        "您需要被批准才能提问。\n"
        "请发送 /start 开始验证流程"
    ),
    "q.subscription_inactive": (
        "❌ 您的订阅未激活或已过期。\n"
        "请使用 /renew 恢复访问。"
    ),
    "q.empty": "❌ 问题为空\n\n请发送有效的问题。",
    "q.too_short": (
        "❌ 问题过短\n\n"
        "请发送更详细的问题（至少 3 个字符）。"
    ),
    "q.invalid": "❌ 无效的问题\n\n请发送有效的问题。",
    "q.cooldown": "⏳ 请稍候\n\n请等待几秒后再发送下一个问题。",
    "q.duplicate": "⚠️ 重复的问题\n\n您最近已发送过此问题。",
    "q.limit_reached": (
        "❌ 已达问题上限\n\n"
        "您今天已用完 {limit} 次提问机会。\n\n"
        "计数器将在明天重置。届时再试。"
    ),
    "q.access_required_simple": (
        "❌ 需要访问权限\n\n"
        "您需要被批准才能提问。\n\n"
        "请发送 /start 开始验证流程"
    ),
    "q.system_error": (
        "❌ 系统错误\n\n"
        "抱歉，处理您的问题时出错。请稍后再试。"
    ),
    "q.system_error_user_not_found": "❌ 系统错误\n\n找不到用户。请重试。",
    "q.system_error_generic": (
        "❌ 系统错误\n\n"
        "处理您的问题时出错。请重试。"
    ),
    "q.received": (
        "✅ 问题已收到\n\n"
        "您的问题已发送给管理员。\n\n"
        "📊 今日剩余提问次数：{remaining}/{limit}\n\n"
        "我们将尽快回复您。"
    ),
    "q.error_generic": "❌ 错误\n\n处理您的问题时出错。请重试。",
    "q.error_forwarding": (
        "❌ 错误\n\n"
        "已收到您的问题，但转发时出错。请重试。"
    ),
    "q.text_only": (
        "❌ 仅支持文本\n\n"
        "请仅以文本消息发送问题。\n\n"
        "暂不支持图片、文件和其他内容。"
    ),
    "q.admin_response": (
        "📨 管理员回复\n\n"
        "❓ 您的问题：\n{question}\n\n"
        "💬 回复：\n{reply}\n\n"
        "---\n"
        "这是对您问题的回复。如需进一步说明，可回复此消息。"
    ),

    # ===== Subscription commands =====
    "sub.cmd_not_approved": (
        "您需要先获得账户批准才能订阅。\n"
        "请使用 /start 继续注册流程。"
    ),
    "sub.cmd_mock_success": (
        "✅ 模拟支付成功。您的订阅已更新。\n"
        "请使用 /subscription 查看详情。"
    ),
    "sub.cmd_mock_failed": "❌ 模拟激活失败。请重试或联系管理员。",

    # ===== Stripe Checkout 提示（内联按钮 — 正文不含链接）=====
    "btn.subscribe_now": "💳 立即订阅",
    "sub.checkout_prompt": (
        "💳 订阅\n\n"
        "请点击下方按钮完成订阅。"
    ),
    "sub.checkout_reuse_prompt": (
        "💳 订阅\n\n"
        "您已有一个进行中的支付会话。请点击下方按钮完成支付。"
    ),

    # ===== Subscription readout =====
    "sub.readout_title": "📋 订阅",
    "sub.readout_account_status": "• 账户状态：{status}",
    "sub.readout_sub_state": "• 订阅状态：{state}",
    "sub.readout_billing_mode": "• 计费模式：{mode}",
    "sub.readout_plan": "• 套餐：{plan}",
    "sub.readout_period_end": "• 周期结束：{date}",
    "sub.readout_grace_until": "• 宽限期至：{date}",
    "sub.readout_can_ask": "• 可提问:{yes_no}",
    "sub.readout_access_detail": "• 访问详情：{reason}",
    "sub.readout_yes": "是",
    "sub.readout_no": "否",
    "sub.readout_dash": "—",
    "sub.next_good_to_go": "✅ 一切就绪。可随时使用 /status。",
    "sub.next_complete_onboarding": "➡️ 完成注册流程：/start",
    "sub.next_mock_subscribe": (
        "➡️ 尝试 /subscribe 激活（模拟），如需帮助请联系管理员。"
    ),
    "sub.next_not_configured": (
        "➡️ 账单功能尚未上线。请留意管理员的通知。"
    ),
    "sub.next_use_renew": (
        "➡️ 结账功能可用后，请使用 /renew，或联系客服。"
    ),
    "sub.placeholder_msg": (
        "💳 订阅\n\n"
        "在线结账暂未启用。"
        "账单功能上线后，您可以在此续订。\n\n"
        "如急需访问权限，请联系管理员。"
    ),

    # ===== Persistent reply-keyboard menu =====
    "menu.btn_check_status": "📊 查看审批状态",
    "menu.btn_subscription": "💳 订阅",
    "menu.btn_change_language": "🌐 切换语言",
    "menu.installed": "📋 请使用下方菜单进行操作。",

    # ===== 用户分类（引导流程中的类别步骤）=====
    "category.prompt": (
        "🗂 <b>请选择您的类别</b>\n\n"
        "这有助于我们根据您的情况提供支持。"
    ),
    "category.btn_students": "🎓 学生",
    "category.btn_work_permits": "💼 工作许可",
    "category.btn_residency": "🏠 居留",
    "category.btn_other": "✳️ 其他",
    "category.other_prompt": (
        "✍️ 请用简短的几个字输入您的类别"
        "（例如：“家庭团聚”）。"
    ),
    "category.saved": "✅ 类别已保存。",
    "category.invalid_custom": "请用一行简短文字发送您的类别。",

    # ===== VIP invite =====
    "vip.invite": (
        "🎉 您的订阅已激活。\n\n"
        "您可以通过此邀请链接加入 VIP 群：\n\n"
        "{link}\n\n"
        "欢迎加入社区。"
    ),

    # ===== Admin → user notifications =====
    "admin.user_approved": (
        "🎉 您的访问申请已获批准。\n\n"
        "请使用 /subscription 查看账单状态，并在可用时使用 /subscribe 或 /renew "
        "激活套餐。\n\n"
        "订阅生效后（包含有效的宽限期），您将收到一条单独的私聊消息，"
        "其中包含 VIP 群邀请链接。"
    ),
    "admin.user_rejected": (
        "❌ 访问申请被拒绝\n\n"
        "您的 VIP 群访问申请已被拒绝。\n\n"
        "原因：{reason}\n\n"
        "如果您认为这是错误，请联系管理员。\n\n"
        "解决问题后，您可以重新提交申请。"
    ),

    # ===== Group moderation private DMs =====
    "group.private_subscription_required": (
        "您在 VIP 群中的消息已被移除（仅限公告）。\n\n"
        "您需要有效的订阅才能从群中转发问题。"
        "请使用 /subscription 查看状态，符合条件后使用 /subscribe 或 /renew。"
    ),
    "group.private_redirect_unapproved": (
        "为保持频道整洁，您在 VIP 群中的消息已被移除。\n\n"
        "请在获得批准并完成订阅后，在与本机器人的私聊中继续注册流程或提问。"
    ),
    "group.forward_offer": (
        "您在 VIP 群中的消息已被移除（仅限公告）。\n\n"
        "是否要将此问题改为发送给管理员？\n\n"
        "—\n{preview}"
    ),
    "group.non_text_notice": (
        "您在 VIP 群中的消息已被移除。仅支持以文本形式转发问题。\n\n"
        "如需帮助，请在与本机器人的私聊中发送您的问题。"
    ),
    "group.btn_yes": "是",
    "group.btn_no": "否",
    "group.offer_cancelled_toast": "已取消",
    "group.offer_expired": (
        "该选项已过期。请重新从群中或在私聊中发送您的问题。"
    ),
}
