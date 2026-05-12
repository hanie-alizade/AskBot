# AskBot - Telegram Bot with User Management

A production-ready Telegram bot with structured user flow, verification, access requests, and admin approval system.

## Features

- ✅ Python 3.11+ compatible
- ✅ Latest aiogram (v3.4.1) for Telegram bot API
- ✅ SQLAlchemy ORM with SQLite database
- ✅ Environment variables with python-dotenv
- ✅ Structured logging
- ✅ Clean, scalable architecture
- ✅ Async/await support
- ✅ Graceful shutdown handling
- ✅ User verification system
- ✅ Access request workflow
- ✅ Admin approval system
- ✅ Persistent user state management
- ✅ Telegram command menu buttons

## Project Structure

```
AskBot/
├── app/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── bot.py               # Bot initialization and setup
│   └── handlers/
│       ├── __init__.py
│       ├── start.py         # /start command handler
│       ├── verify.py        # User verification handlers
│       ├── access.py        # Access request handlers
│       └── admin.py         # Admin approval handlers
├── database/
│   ├── __init__.py          # Database package exports
│   ├── db.py                # Database configuration and sessions
│   ├── models.py            # SQLAlchemy ORM models
│   └── crud.py              # Database CRUD operations
├── init_db.py               # Database initialization script
├── .env                     # Environment variables (template)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Get Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token provided by BotFather

### 4. Configure Environment Variables

1. Open `.env` file in project root
2. Replace the values with your actual configuration:

```env
# Telegram Bot Token (get from @BotFather)
BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789

# Admin user ID (get from @userinfobot)
ADMIN_ID=8235652033

# Private group invite link
GROUP_INVITE_LINK=https://t.me/+x9eWH8a5Tb1mMTY0

# Database configuration
DATABASE_URL=sqlite:///./ask_bot.db
```

### 5. Initialize Database

Before running the bot for the first time, initialize the database:

```bash
python init_db.py
```

This will create the SQLite database file and set up the necessary tables.

### 6. Run the Bot

```bash
python -m app.main
```

Or alternatively:

```bash
python app/main.py
```

## Usage

Once the bot is running, users can interact with the following flow:

### User Flow

1. **Start**: Send `/start` to begin verification
2. **Verify**: Click the verification button to verify account
3. **Request Access**: After verification, request access to VIP group
4. **Wait for Approval**: Admin will review and approve/deny requests
5. **Join Group**: Once approved, receive invite link to join

### Available Commands

- `/start` - Begin the verification process
- `/status` - Check your current status
- `/help` - Show available commands

### Admin Commands

- `/approve <user_id>` - Approve a user's access request
- `/pending` - Show users pending approval
- `/users` - Show all users with details
- `/stats` - Show user statistics
- `/admin_help` - Show admin command help

## Development

### Adding New Handlers

1. Create a new file in `app/handlers/` (e.g., `help.py`)
2. Define your router and handlers:

```python
# app/handlers/help.py
from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("help"))
async def handle_help(message: types.Message):
    await message.answer("This is the help message!")
```

3. Import and register the router in `app/bot.py`:

```python
# In setup_bot() function
from .handlers import help
dp.include_router(help.router)
```

### Project Architecture

- **`config.py`**: Handles environment variables and configuration
- **`bot.py`**: Bot initialization, dispatcher setup, and handler registration
- **`handlers/`**: Contains all command and message handlers
- **`main.py`**: Application entry point with graceful shutdown handling

### Logging

The bot uses Python's built-in logging with INFO level by default. Logs include timestamps, module names, and log levels for easy debugging.

## Database Migration to PostgreSQL

For production use, you can easily migrate from SQLite to PostgreSQL:

1. **Install PostgreSQL driver**:

```bash
pip install psycopg2-binary
```

2. **Update DATABASE_URL in .env**:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/ask_bot
```

3. **Run the bot** - SQLAlchemy will automatically create the PostgreSQL tables.

The database layer is abstracted, so switching between SQLite and PostgreSQL requires only changing the `DATABASE_URL` environment variable.

## Environment Variables

| Variable            | Description                        | Required |
| ------------------- | ---------------------------------- | -------- |
| `BOT_TOKEN`         | Telegram bot token from @BotFather | ✅ Yes   |
| `ADMIN_ID`          | Admin user ID from @userinfobot    | ✅ Yes   |
| `GROUP_INVITE_LINK` | Private group invite link          | ✅ Yes   |
| `DATABASE_URL`      | Database connection URL            | ✅ Yes   |

## Dependencies

- **aiogram** (v3.4.1): Modern and fully asynchronous framework for Telegram Bot API
- **python-dotenv** (v1.0.0): Load environment variables from .env files
- **sqlalchemy** (v2.0.23): SQL toolkit and ORM for database operations
- **alembic** (v1.13.1): Database migration tool (for future use)

## License

This project is provided as a starter template. Feel free to modify and use it for your own projects.

## Support

For issues related to:

- **aiogram**: Check the [aiogram documentation](https://docs.aiogram.dev/)
- **Telegram Bot API**: Check the [Telegram Bot API documentation](https://core.telegram.org/bots/api)
