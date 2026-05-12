# Quick Setup Guide - Content Separation System

## 🚀 Bot is Running!

The content separation system is now fully implemented and your bot is running successfully.

## 📋 Next Steps

### 1. Get VIP Group ID

To enable group moderation, you need to get your VIP group ID:

#### Method 1: Using BotFather

1. Forward any message from your VIP group to @BotFather
2. BotFather will reply with the group ID

#### Method 2: Using a Test Bot

1. Create a temporary bot or use existing one
2. Add the bot to your VIP group
3. Send a message in the group
4. Check bot logs for the group ID (it will show in message.chat.id)

#### Method 3: Using User Info Bot

1. Add @userinfobot to your VIP group
2. Send a message in the group
3. The bot will show the group ID

### 2. Update Configuration

Once you have the group ID, update your `.env` file:

```env
VIP_GROUP_ID=-1001234567890
```

**Important**: Group IDs are always negative numbers for groups/channels.

### 3. Add Bot to VIP Group

Add your bot as an administrator in the VIP group with these permissions:

- ✅ **Delete Messages** (Required for moderation)
- ✅ **Send Messages** (Required for admin announcements)
- ✅ **Pin Messages** (Optional, for important announcements)
- ✅ **Invite Users** (Optional, for manual invites)

## 🧪 Testing the System

### Test Group Moderation

1. **Send a message as regular user in VIP group**

   - Expected: Message deleted + private redirect
   - Check bot logs for moderation actions

2. **Send a message as admin in VIP group**
   - Expected: Message stays in group
   - Should not trigger moderation

### Test Private Questions

1. **Send a question in private chat (as approved user)**

   - Expected: Question accepted + forwarded to admin
   - Check remaining questions count

2. **Send a question as non-approved user**
   - Expected: Access denied message
   - Check status rejection

## 📊 System Features Now Active

### ✅ Group Moderation

- Automatic deletion of non-admin messages
- Private redirect messages to users
- Support for all content types
- Comprehensive error handling

### ✅ Private Question System

- User status validation
- Daily question limits (default: 5)
- Question usage tracking
- Admin forwarding with context

### ✅ Admin Reply System

- Reply-to functionality
- User ID extraction
- Forwarding to private chat

### ✅ Monitoring & Logging

- All actions logged
- Error tracking
- Performance metrics

## 🔧 Configuration

Your bot now has these configuration options:

```env
BOT_TOKEN=your_bot_token
ADMIN_ID=your_admin_id
GROUP_INVITE_LINK=your_group_link
DATABASE_URL=sqlite:///./ask_bot.db
VIP_GROUP_ID=your_vip_group_id
```

## 📞 Troubleshooting

### If group moderation doesn't work:

1. Check VIP_GROUP_ID is correct
2. Verify bot is admin in the group
3. Check bot has "Delete Messages" permission

### If private questions don't work:

1. Verify user is APPROVED in database
2. Check user hasn't exceeded question limit
3. Verify bot can send private messages to user

### If admin doesn't receive forwards:

1. Check ADMIN_ID is correct
2. Verify admin hasn't blocked the bot
3. Check bot can send messages to admin

## 🎯 Success Indicators

Your system is working correctly when:

- ✅ Bot starts without errors
- ✅ Non-admin messages are deleted from VIP group
- ✅ Users receive private redirect messages
- ✅ Approved users can ask questions
- ✅ Admin receives question forwards
- ✅ Question limits are enforced

## 📈 Monitoring

Monitor these log messages:

- `Deleted message from user X in VIP group`
- `Sent private redirect message to user X`
- `Accepted question from user X, remaining: Y`
- `Forwarded question from user X to admin`

## 🚀 Ready for Production

Your content separation system is now fully implemented and ready for production use!
