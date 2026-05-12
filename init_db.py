#!/usr/bin/env python3
"""
Database initialization script for AskBot.
Creates the database tables and performs initial setup.
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import init_db


def main():
    """Initialize the database."""
    print("🔧 Initializing AskBot database...")
    
    try:
        init_db()
        print("✅ Database initialized successfully!")
        print("📊 Database file: ./ask_bot.db")
        print("\n🚀 You can now start the bot with:")
        print("   python -m app.main")
        
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
