#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script

This script creates PostgreSQL database and user for the trading bot.
Requires PostgreSQL to be installed and running.
"""

import subprocess
from pathlib import Path


def run_command(command, description):
    """Run shell command with error handling"""
    print(f"[INFO] {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"[SUCCESS] {description}")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description}")
        print(f"[ERROR] {e}")
        if e.stderr:
            print(f"[ERROR] {e.stderr}")
        return False
    return True


def setup_postgresql():
    """Setup PostgreSQL database and user"""

    print("=" * 60)
    print("PostgreSQL Database Setup for Trading Bot")
    print("=" * 60)

    # Configuration
    db_name = "trading_bot_dev"
    user_name = "trading_bot_user"
    user_password = "password"

    # Check PostgreSQL installation
    if not run_command("psql --version", "Checking PostgreSQL installation"):
        print("[ERROR] PostgreSQL is not installed. Please install PostgreSQL first.")
        return False

    # Check if PostgreSQL service is running
    if not run_command("pg_isready -q", "Checking PostgreSQL service"):
        print("[WARNING] PostgreSQL service is not running. Starting it...")
        # Try to start PostgreSQL service (Windows)
        if Path("C:\\Program Files\\PostgreSQL").exists():
            print("[INFO] Attempting to start PostgreSQL service...")
            # This would need proper Windows service management
            pass

    print(f"\n[INFO] Setting up database: {db_name}")
    print(f"[INFO] Setting up user: {user_name}")

    # Create user (if not exists)
    user_sql = f"CREATE USER {user_name} WITH PASSWORD '{user_password}';"
    run_command(f'psql -U postgres -c "{user_sql}"', f"Creating user {user_name}")

    # Create database (if not exists)
    db_sql = f"CREATE DATABASE {db_name} OWNER {user_name};"
    run_command(f'psql -U postgres -c "{db_sql}"', f"Creating database {db_name}")

    # Grant privileges
    grant_sql = f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {user_name};"
    run_command(f'psql -U postgres -c "{grant_sql}"', f"Granting privileges to {user_name}")

    print("\n" + "=" * 60)
    print("PostgreSQL Setup Complete!")
    print("=" * 60)
    print(f"Database: {db_name}")
    print(f"User: {user_name}")
    print(
        f"Connection URL: postgresql+asyncpg://{user_name}:{user_password}@localhost:5432/{db_name}"
    )
    print("=" * 60)

    return True


def setup_production_database():
    """Setup PostgreSQL database for production"""

    print("=" * 60)
    print("PostgreSQL Production Database Setup")
    print("=" * 60)

    # Configuration
    db_name = "trading_bot_db"
    user_name = "trading_bot_user"
    user_password = "trading_bot_password"

    print(f"[INFO] Setting up production database: {db_name}")
    print(f"[INFO] Setting up production user: {user_name}")

    # Create user (if not exists)
    user_sql = f"CREATE USER {user_name} WITH PASSWORD '{user_password}';"
    run_command(f'psql -U postgres -c "{user_sql}"', f"Creating user {user_name}")

    # Create database (if not exists)
    db_sql = f"CREATE DATABASE {db_name} OWNER {user_name};"
    run_command(f'psql -U postgres -c "{db_sql}"', f"Creating database {db_name}")

    # Grant privileges
    grant_sql = f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {user_name};"
    run_command(f'psql -U postgres -c "{grant_sql}"', f"Granting privileges to {user_name}")

    print("\n" + "=" * 60)
    print("PostgreSQL Production Setup Complete!")
    print("=" * 60)
    print(f"Database: {db_name}")
    print(f"User: {user_name}")
    print(
        f"Connection URL: postgresql+asyncpg://{user_name}:{user_password}@localhost:5432/{db_name}"
    )
    print("=" * 60)

    return True


if __name__ == "__main__":
    import os

    env = os.getenv("ENVIRONMENT", "development").lower()

    if env in ["production", "prod"]:
        setup_production_database()
    else:
        setup_postgresql()
