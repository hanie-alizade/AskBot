# AskBot Testing Guide

## Setup Instructions

### 1. Configure Environment Variables

Edit the `.env` file and replace the placeholder values:

```env
# Telegram Bot Token (already configured)
BOT_TOKEN=8705043783:AAFvCAYkMqci6G7gm5eZLBH1-SePYhzA5-c

# Admin user ID (get this by sending /start to @userinfobot)
ADMIN_ID=YOUR_ADMIN_ID_HERE

# Private group invite link
GROUP_INVITE_LINK=YOUR_GROUP_INVITE_LINK_HERE
```

**How to get your Admin ID:**

1. Start a chat with @userinfobot on Telegram
2. Send any message
3. The bot will reply with your user ID
4. Replace `YOUR_ADMIN_ID_HERE` with that number

**How to get Group Invite Link:**

1. Create a private Telegram group for VIP users
2. Go to Group Settings > Manage > Invite Links
3. Create an invite link
4. Replace `YOUR_GROUP_INVITE_LINK_HERE` with that link

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Bot

```bash
cd app
python main.py
```

## Testing the Complete User Flow

### Step 1: New User Verification

1. **Test with a regular user account** (not the admin)
2. Send `/start` to your bot
3. **Expected behavior:**

   - Bot should welcome the user
   - Show buttons: "✅ Verify", "📊 Check Status", "❓ Help"
   - User state should be `NEW`

4. Click the "✅ Verify" button
5. **Expected behavior:**

   - Bot should confirm verification
   - Show buttons: "🔑 Request Access", "📊 Check Status", "❓ Help"
   - User state should change to `VERIFIED`

6. Test the other buttons:
   - "📊 Check Status" - Shows current user status
   - "❓ Help" - Shows available commands

### Step 2: Access Request

1. Click the "🔑 Request Access" button
2. **Expected behavior:**
   - Bot should confirm request submission
   - User state should change to `PENDING_APPROVAL`
   - Admin should receive a notification (check logs or admin chat)

### Step 3: Admin Approval

1. **Switch to your admin account**
2. Send `/start` to the bot
3. **Expected behavior:**

   - Bot should show admin welcome message
   - Show buttons: "🔧 Admin Menu", "📊 Check Status", "❓ Help"

4. Click "🔧 Admin Menu" button
5. **Expected behavior:**

   - Bot should show admin menu with buttons:
     - "📋 Show Users List"
     - "⏳ Show Pending Users"
     - "📊 Show Statistics"
     - "❓ Admin Help"

6. Click "📋 Show Users List"
7. **Expected behavior:**

   - Bot should show all users with their:
     - Name and username
     - User ID
     - Current role/status (🆕 New, ✅ Verified, ⏳ Pending, 🎉 Approved)

8. Click "⏳ Show Pending Users"
9. **Expected behavior:**

   - Bot should list all users pending approval
   - Should show the user ID from Step 2

10. Send `/approve <user_id>` (replace with actual user ID)
11. **Expected behavior:**
    - Bot should confirm approval
    - User should receive an invite link via private message
    - User state should change to `APPROVED`

### Step 4: Verify Approved User

1. **Switch back to the regular user account**
2. Send `/start` to the bot
3. **Expected behavior:**
   - Bot should show that the user is already approved
   - Show buttons: "🎉 Join VIP Group", "📊 Check Status", "❓ Help"
   - "🎉 Join VIP Group" button will open the group invite link

## Testing Additional Commands

### User Commands

1. **`/status`** - Shows current user status
2. **`/help`** - Shows available commands based on user state

### Admin Commands

1. **`/approve <user_id>`** - Approve a pending user
2. **`/users`** - Show all users with details (name, username, ID, role)
3. **`/pending`** - Show all users pending approval
4. **`/stats`** - Show user statistics
5. **`/admin_help`** - Show all admin commands

### Admin Quick Access Buttons

- **🔧 Admin Menu** - Opens admin control panel
- **👥 Users List** - Shows all users with their information
- **⏳ Pending Users** - Shows users waiting for approval
- **📊 Statistics** - Shows user statistics
- **📊 Check Status** - Shows admin's current status
- **❓ Help** - Shows available commands

## Error Handling Tests

### Test Invalid Approvals

1. Try `/approve invalid_id` - Should show error
2. Try `/approve 123456789` (non-existent user) - Should show error
3. Try approving already approved user - Should show already approved message

### Test Unauthorized Access

1. **Use a regular user account**
2. Try admin commands: `/pending`, `/stats`, `/approve <id>`
3. **Expected:** All should show "not authorized" message

### Test Duplicate Actions

1. Try to verify an already verified user
2. Try to request access when already pending
3. **Expected:** Should show appropriate error messages

## Logging and Debugging

### Check Logs

The bot logs all important events:

- User state changes
- Verification completions
- Access requests
- Admin approvals
- Errors

Logs will be displayed in the console where you're running the bot.

### Common Issues

1. **Bot doesn't respond:**

   - Check if bot token is correct
   - Ensure bot is running
   - Check internet connection

2. **Admin commands don't work:**

   - Verify ADMIN_ID is correct in .env
   - Make sure you're using the correct Telegram account

3. **Users don't receive notifications:**
   - Check bot has permission to send messages
   - Ensure user hasn't blocked the bot
   - Check logs for any errors

## Production Considerations

For production use, consider:

1. **Database Integration:** Replace in-memory user state with a database
2. **Error Recovery:** Add persistence for user states
3. **Rate Limiting:** Add rate limiting to prevent spam
4. **Multiple Admins:** Extend admin system for multiple administrators
5. **Webhook Mode:** Consider using webhooks instead of polling for better performance

## Troubleshooting

If you encounter issues:

1. Check the console logs for error messages
2. Verify all environment variables are set correctly
3. Ensure the bot has necessary permissions
4. Test with different user accounts to isolate the issue

For additional help, check the aiogram documentation or Telegram Bot API documentation.
