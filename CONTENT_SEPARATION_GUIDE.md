# Content Separation System - Testing Guide

## Overview

The content separation system keeps the VIP group clean by automatically moderating user messages and redirecting questions to private chat with the bot.

## System Architecture

### 1. Group Moderation Flow
```
User sends message in VIP group
    ↓
Check if user is admin
    ↓ (if not admin)
Delete the message
    ↓
Send private redirect message
    ↓
Log the event
```

### 2. Private Question Flow
```
User sends message in private chat
    ↓
Check if user is approved
    ↓ (if approved)
Check question limit
    ↓ (if limit available)
Accept question
    ↓
Forward to admin
    ↓
Increment usage count
```

## Setup Instructions

### 1. Configure VIP Group ID

1. Add your bot to the VIP group as an administrator
2. Get the group ID:
   - Send a message to the group
   - Use a bot like @userinfobot to get the group ID
   - Or check the bot logs for message.chat.id
3. Update `.env` file:

```env
VIP_GROUP_ID=-1001234567890
```

### 2. Bot Permissions

Make sure the bot has the following permissions in the VIP group:
- **Delete Messages**: Required to remove user messages
- **Send Messages**: Required for admin announcements

## Testing Steps

### Phase 1: Group Moderation Testing

#### Test 1: Admin Message (Should Pass)
1. **Action**: Admin sends a message in VIP group
2. **Expected**: Message stays in group, no deletion
3. **Check logs**: Should show "Admin message in VIP group allowed"

#### Test 2: Approved User Message (Should Be Deleted)
1. **Action**: Approved user sends "Hello everyone" in VIP group
2. **Expected**: 
   - Message is immediately deleted
   - User receives private message: "Your message has been removed..."
3. **Check logs**: Should show message deletion and private redirect

#### Test 3: Non-Approved User Message (Should Be Deleted)
1. **Action**: Non-approved user sends message in VIP group
2. **Expected**: Same as approved user - deletion + private redirect
3. **Check logs**: Should show unauthorized message handling

#### Test 4: Content Types (Should Be Deleted)
1. **Action**: User sends photo, document, sticker in VIP group
2. **Expected**: All content types deleted + private redirect
3. **Check logs**: Should show content deletion

#### Test 5: Wrong Group (Should Be Ignored)
1. **Action**: User sends message in other group
2. **Expected**: No action taken
3. **Check logs**: No group moderation logs

### Phase 2: Private Question Testing

#### Test 6: Approved User Question (Should Pass)
1. **Action**: Approved user sends "How do I use this feature?" in private chat
2. **Expected**:
   - User receives: "✅ Question Received... Remaining questions: X/5"
   - Admin receives forward with user details
   - Question count increments
3. **Check logs**: Should show question acceptance and admin forwarding

#### Test 7: Non-Approved User Question (Should Be Rejected)
1. **Action**: Non-approved user sends question in private chat
2. **Expected**: User receives "❌ Access Required" message
3. **Check logs**: Should show rejection for non-approved user

#### Test 8: Unregistered User Question (Should Be Rejected)
1. **Action**: New user (not in database) sends question
2. **Expected**: User receives "❌ Access Required" with /start instructions
3. **Check logs**: Should show rejection for unregistered user

#### Test 9: Question Limit Exceeded (Should Be Rejected)
1. **Action**: User with 0 remaining questions sends question
2. **Expected**: User receives "❌ Question Limit Reached" message
3. **Check logs**: Should show limit exceeded event

#### Test 10: Admin Question (Should Be Ignored)
1. **Action**: Admin sends message in private chat
2. **Expected**: No processing, message treated as normal
3. **Check logs**: Should show "Admin message received, skipping"

#### Test 11: Non-Text Content (Should Be Rejected)
1. **Action**: User sends photo/file in private chat
2. **Expected**: User receives "❌ Text Only" message
3. **Check logs**: Should show content type rejection

### Phase 3: Admin Reply Testing

#### Test 12: Admin Reply to Question (Should Forward to User)
1. **Action**: Admin replies to forwarded question message
2. **Expected**:
   - User receives admin response
   - Admin gets confirmation "✅ Reply sent to user"
3. **Check logs**: Should show successful reply forwarding

#### Test 13: Admin Reply to Non-Question (Should Fail)
1. **Action**: Admin replies to regular message
2. **Expected**: Admin receives error "Could not find user ID"
3. **Check logs**: Should show reply processing error

## Edge Cases Testing

### Test 14: Bot Cannot DM User
1. **Scenario**: User has blocked the bot or disabled DMs
2. **Action**: User sends message in VIP group
3. **Expected**: Message deleted, but private message fails gracefully
4. **Check logs**: Should show "Cannot send private message to user" warning

### Test 15: Message Already Deleted
1. **Scenario**: Multiple users send messages simultaneously
2. **Action**: Bot tries to delete already deleted message
3. **Expected**: No error, graceful handling
4. **Check logs**: Should show "message already deleted" warning

### Test 16: Database Connection Error
1. **Scenario**: Database unavailable during message processing
2. **Action**: User sends message in VIP group or private chat
3. **Expected**: Error message to user, graceful degradation
4. **Check logs**: Should show database error logs

## Monitoring and Logging

### Key Log Messages to Watch

**Group Moderation:**
- `Admin message in VIP group allowed`
- `Deleted message X from user Y in VIP group`
- `Sent private redirect message to user Y`
- `Cannot send private message to user Y`

**Private Questions:**
- `Accepted question from user X, remaining: Y`
- `User X exceeded daily question limit`
- `Forwarded question from user X to admin`
- `Admin replied to user X`

**Errors:**
- `Bot doesn't have permission to delete messages`
- `Error processing question from user X`
- `Error forwarding question to admin`

## Performance Considerations

### Rate Limits
- Bot respects Telegram API rate limits automatically
- Private redirects use exponential backoff on failures
- Admin forwarding is immediate for real-time support

### Database Efficiency
- Question limit checks use single database query
- User status validation is cached per request
- Question usage increments are atomic

## Troubleshooting

### Common Issues

**1. Messages not being deleted in group**
- Check bot has "Delete Messages" permission
- Verify VIP_GROUP_ID is correct
- Check bot is admin in the group

**2. Users not receiving private messages**
- User may have blocked the bot
- User may have disabled private messages from bots
- Check logs for TelegramForbiddenError

**3. Admin not receiving question forwards**
- Check ADMIN_ID is correct
- Verify admin hasn't blocked the bot
- Check bot can send messages to admin

**4. Question limits not working**
- Check database connection
- Verify user.question_limit field is set
- Check questions_used field is incrementing

### Debug Mode

Enable debug logging by updating `app/main.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Production Deployment

### Required Environment Variables
```env
BOT_TOKEN=your_bot_token
ADMIN_ID=your_admin_id
GROUP_INVITE_LINK=your_group_link
DATABASE_URL=your_database_url
VIP_GROUP_ID=your_vip_group_id
```

### Bot Permissions in VIP Group
- Delete Messages ✅
- Send Messages ✅
- Pin Messages (optional for announcements)
- Invite Users (optional)

### Monitoring Setup
- Monitor log files for error patterns
- Set up alerts for high question volumes
- Track group moderation effectiveness

## Success Metrics

### Group Cleanliness
- Zero non-admin messages visible in VIP group
- All user questions redirected to private chat
- Admin announcements remain visible

### User Experience
- Users receive clear redirect instructions
- Question limits enforced consistently
- Admin responses delivered promptly

### System Reliability
- Graceful handling of permission errors
- No message deletion failures
- Consistent question counting
