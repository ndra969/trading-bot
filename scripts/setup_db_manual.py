#!/usr/bin/env python3
"""
Manual Database Setup Instructions

This script provides instructions for manual database setup.
"""

def print_manual_instructions():
    """Print manual setup instructions"""

    print("=" * 70)
    print("MANUAL POSTGRESQL DATABASE SETUP INSTRUCTIONS")
    print("=" * 70)

    print("\nOPTION 1: Use pgAdmin (Recommended)")
    print("-" * 40)
    print("1. Open pgAdmin 4 (installed with PostgreSQL)")
    print("2. Connect to server with your postgres password")
    print("3. Run these SQL queries:")
    print("""
-- Create Development User
CREATE USER trading_bot_dev_user WITH PASSWORD 'dev_password_123';

-- Create Development Database
CREATE DATABASE trading_bot_dev OWNER trading_bot_dev_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE trading_bot_dev TO trading_bot_dev_user;

-- Create Production User
CREATE USER trading_bot_prod_user WITH PASSWORD 'prod_password_456';

-- Create Production Database
CREATE DATABASE trading_bot_db OWNER trading_bot_prod_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE trading_bot_db TO trading_bot_prod_user;
""")

    print("\nOPTION 2: Use Command Line")
    print("-" * 40)
    print("1. Open Command Prompt as Administrator")
    print("2. Navigate to PostgreSQL bin:")
    print('   cd "C:\\Program Files\\PostgreSQL\\18\\bin"')
    print("3. Connect to PostgreSQL:")
    print("   psql -U postgres")
    print("4. Enter your postgres password when prompted")
    print("5. Run the SQL commands above")

    print("\nOPTION 3: Reset PostgreSQL Password")
    print("-" * 40)
    print("If you forgot your postgres password:")
    print("1. Open Services (services.msc)")
    print("2. Stop 'postgresql-x64-18' service")
    print("3. Edit pg_hba.conf file:")
    print('   "C:\\Program Files\\PostgreSQL\\18\\data\\pg_hba.conf"')
    print("4. Change 'md5' to 'trust' for local connections")
    print("5. Restart PostgreSQL service")
    print("6. Connect without password: psql -U postgres")
    print("7. Set new password: ALTER USER postgres PASSWORD 'your_password';")
    print("8. Revert pg_hba.conf changes and restart service")

    print("\nDATABASE CONNECTION INFO")
    print("-" * 40)
    print("Development:")
    print("  Database: trading_bot_dev")
    print("  User: trading_bot_dev_user")
    print("  Password: dev_password_123")
    print("  Connection: postgresql+asyncpg://trading_bot_dev_user:dev_password_123@localhost:5432/trading_bot_dev")

    print("\nProduction:")
    print("  Database: trading_bot_db")
    print("  User: trading_bot_prod_user")
    print("  Password: prod_password_456")
    print("  Connection: postgresql+asyncpg://trading_bot_prod_user:prod_password_456@localhost:5432/trading_bot_db")

    print("\n🧪 TEST CONNECTION")
    print("-" * 40)
    print("After setup, test with:")
    print("  TRADING_BOT_ENV=development uv run trading-bot start --dry-run")
    print("  TRADING_BOT_ENV=production uv run trading-bot start --dry-run")

    print("=" * 70)

if __name__ == "__main__":
    print_manual_instructions()