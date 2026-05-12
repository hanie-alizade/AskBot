# Admin Reset Utility - Complete Implementation

## 🛠️ Temporary Testing Utility

### **Purpose**
Admin-only command to completely reset user data for testing purposes.

## ✅ Implementation Details

### **1. Command Format**
```bash
/reset_user <telegram_user_id>
```

**Example:**
```bash
/reset_user 7285268952
```

### **2. Complete Reset Behavior**
The utility deletes and resets:

- ✅ **Access State** - Status reset to "NEW"
- ✅ **Questions** - All user questions deleted
- ✅ **Usage Counters** - `questions_used` reset to 0
- ✅ **Approval Status** - `approved_at` cleared
- ✅ **Question Limits** - Reset to default (5)
- ✅ **Last Question Date** - Cleared

### **3. Safety Features**

#### **Admin Protection**
```python
# Safety: do not allow resetting admin account
if target_user_id == config.admin_id:
    await message.answer("❌ Safety Error - Cannot reset the admin account.")
    return
```

#### **User Existence Check**
```python
# Check if user exists first
target_user = get_user(db, target_user_id)
if not target_user:
    await message.answer(f"❌ User Not Found - User {target_user_id} not found in database.")
    return
```

### **4. Database Cascade Safety**
```python
# Delete all questions from this user first (avoid foreign key errors)
from .models import Question
deleted_questions = db.query(Question).filter(Question.user_id == user.id).delete()
logger.info(f"Deleted {deleted_questions} questions for user {telegram_id}")
```

### **5. Confirmation Message**
```
✅ **User Reset Successfully**

User 7285268952 has been reset successfully.
```

### **6. Error Handling**

#### **Invalid Command**
```
❌ **Invalid Command**

Usage: /reset_user <telegram_user_id>

Example: /reset_user 7285268952
```

#### **Invalid User ID**
```
❌ **Invalid User ID**

User ID must be a number.

Example: /reset_user 7285268952
```

#### **User Not Found**
```
❌ **User Not Found**

User 999999999 not found in database.
```

#### **Safety Error**
```
❌ **Safety Error**

Cannot reset the admin account.
```

### **7. Logging**

#### **Success Log**
```python
logger.info(f"Admin reset user {target_user_id}")
```

#### **Questions Deleted Log**
```python
logger.info(f"Deleted {deleted_questions} questions for user {telegram_id}")
```

#### **Error Logs**
```python
logger.error(f"Error resetting user {target_user_id}: {e}")
logger.error(f"Error in reset_user command: {e}")
```

## 📁 Files Modified

### **1. database/crud.py**
- Added `reset_user_completely()` function
- Includes TODO comment for production removal
- Handles cascade deletion and user reset

### **2. app/handlers/admin.py**
- Added `/reset_user` command handler
- Added import for `reset_user_completely`
- Includes comprehensive error handling
- Admin-only access protection

## 🔧 Technical Implementation

### **Database Operations**
```python
# 1. Find user
user = db.query(User).filter(User.telegram_id == telegram_id).first()

# 2. Delete related questions (cascade safety)
deleted_questions = db.query(Question).filter(Question.user_id == user.id).delete()

# 3. Reset user fields
user.status = "NEW"
user.approved_at = None
user.questions_used = 0
user.question_limit = 5
user.last_question_date = None

# 4. Commit changes
db.commit()
```

### **Command Validation**
```python
# Extract and validate command parts
command_parts = message.text.split()
if len(command_parts) != 2:
    # Show usage error
    return

try:
    target_user_id = int(command_parts[1])
except ValueError:
    # Show invalid ID error
    return
```

## 🚨 Important Notes

### **Temporary Utility**
- **TODO Comment:** Added to both files
- **Production Removal:** Should be removed if not needed in production
- **Testing Purpose:** Designed for user testing scenarios

### **Admin-Only Access**
```python
if not message.from_user or message.from_user.id != config.admin_id:
    return  # Silent ignore for non-admin users
```

### **Complete Reset Effect**
After reset, the user is as if they never used the bot:
- Status: "NEW"
- Questions Used: 0
- Questions in DB: 0
- Approval: None
- Last Question: Never

## 🧪 Testing Scenarios

### **Valid Reset**
```bash
/reset_user 7285268952
```
✅ Expected: User completely reset with success message

### **Invalid Command**
```bash
/reset_user
```
❌ Expected: Usage error message

### **Invalid User ID**
```bash
/reset_user abc
```
❌ Expected: Invalid ID error message

### **User Not Found**
```bash
/reset_user 999999999
```
❌ Expected: User not found error message

### **Admin Reset Attempt**
```bash
/reset_user 453888838  # (assuming admin ID)
```
❌ Expected: Safety error message

## 🎯 Usage Guidelines

### **When to Use**
- Testing user registration flow
- Debugging user state issues
- Resetting problematic test accounts
- Cleaning up test data

### **Safety Precautions**
- Double-check user ID before resetting
- Never reset the admin account
- Use only for legitimate testing purposes
- Confirm user consent when appropriate

## ✅ Implementation Complete

The admin reset utility is now fully implemented with:
- ✅ Complete user data reset
- ✅ Admin-only access protection
- ✅ Database cascade safety
- ✅ Comprehensive error handling
- ✅ Clear confirmation messages
- ✅ Proper logging
- ✅ TODO comments for production cleanup

**Ready for testing!** 🚀
