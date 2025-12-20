#!/usr/bin/env python3
"""
Database Creation Script

Creates PostgreSQL databases for development and production environments.
Automatically detects PostgreSQL installation path.
"""

import os
import subprocess
import sys


def find_postgresql_bin():
    """Find PostgreSQL bin directory on Windows"""
    possible_paths = [
        r"C:\Program Files\PostgreSQL\18\bin",
        r"C:\Program Files\PostgreSQL\17\bin",
        r"C:\Program Files\PostgreSQL\16\bin",
        r"C:\Program Files\PostgreSQL\15\bin",
        r"C:\Program Files\PostgreSQL\14\bin",
        r"C:\Program Files (x86)\PostgreSQL\*\bin",
    ]

    for path_pattern in possible_paths:
        if "*" in path_pattern:
            from glob import glob

            matches = glob(path_pattern)
            for match in matches:
                if os.path.exists(os.path.join(match, "psql.exe")):
                    return match
        else:
            if os.path.exists(os.path.join(path_pattern, "psql.exe")):
                return path_pattern

    return None


def test_postgres_password(postgresql_bin, password):
    """Test if PostgreSQL password works"""
    psql_path = os.path.join(postgresql_bin, "psql.exe")
    env = os.environ.copy()
    env["PGPASSWORD"] = password

    try:
        result = subprocess.run(
            [psql_path, "-U", "postgres", "-c", "SELECT 1;"],
            capture_output=True,
            text=True,
            check=True,
            env=env,
            timeout=5,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def find_postgres_password(postgresql_bin):
    """Try common PostgreSQL passwords"""
    common_passwords = [
        "kosonginaja",
        "",
        "admin",
        "postgres",
        "password",
        "123456",
        "root",
        "sa",
        "PostgreSQL",
        "pgadmin",
    ]

    print("[INFO] Testing PostgreSQL passwords...")
    for password in common_passwords:
        print(f"[INFO] Trying password: '{password}'")
        if test_postgres_password(postgresql_bin, password):
            print(f"[SUCCESS] Password found: '{password}'")
            return password
        else:
            print(f"[INFO] Password '{password}' failed")

    print("[ERROR] Could not find valid PostgreSQL password")
    print("[INFO] Please check your PostgreSQL installation")
    return None


def run_psql_command(command, description, postgresql_bin, password):
    """Run PostgreSQL command with error handling"""
    psql_path = os.path.join(postgresql_bin, "psql.exe")

    print(f"[INFO] {description}")

    # Set environment variable for password
    env = os.environ.copy()
    env["PGPASSWORD"] = password

    try:
        result = subprocess.run(
            [psql_path, "-U", "postgres"] + command,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        print(f"[SUCCESS] {description}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description}")
        print(f"[ERROR] {e}")
        if e.stderr:
            print(f"[ERROR] {e.stderr}")
        return False


def create_databases():
    """Create development and production databases"""

    print("=" * 60)
    print("PostgreSQL Database Creation for Trading Bot")
    print("=" * 60)

    # Find PostgreSQL installation
    postgresql_bin = find_postgresql_bin()
    if not postgresql_bin:
        print("[ERROR] PostgreSQL installation not found")
        print("[INFO] Please install PostgreSQL from postgresql.org")
        return False

    print(f"[INFO] PostgreSQL found at: {postgresql_bin}")

    # Find PostgreSQL password
    postgres_password = find_postgres_password(postgresql_bin)
    if not postgres_password:
        print("[ERROR] Could not authenticate with PostgreSQL")
        print("[INFO] Please check your PostgreSQL password or reset it")
        return False

    print(f"[INFO] Using PostgreSQL password: {postgres_password}")

    # Database configurations from .env files
    databases = [
        {
            "name": "trading_bot_dev",
            "user": "trading_bot_dev_user",
            "password": "dev_password_123",
            "description": "Development Database",
        },
        {
            "name": "trading_bot_db",
            "user": "trading_bot_prod_user",
            "password": "prod_password_456",
            "description": "Production Database",
        },
    ]

    success_count = 0

    for db in databases:
        print(f"\n[INFO] Setting up {db['description']}")
        print(f"[INFO] Database: {db['name']}")
        print(f"[INFO] User: {db['user']}")

        # Create user (if not exists)
        user_sql = f"CREATE USER {db['user']} WITH PASSWORD '{db['password']}';"
        if run_psql_command(
            ["-c", user_sql], f"Creating user {db['user']}", postgresql_bin, postgres_password
        ):
            print(f"[SUCCESS] User {db['user']} created")
        else:
            print(f"[INFO] User {db['user']} may already exist")

        # Create database (if not exists)
        db_sql = f"CREATE DATABASE {db['name']} OWNER {db['user']};"
        if run_psql_command(
            ["-c", db_sql], f"Creating database {db['name']}", postgresql_bin, postgres_password
        ):
            print(f"[SUCCESS] Database {db['name']} created")
            success_count += 1
        else:
            print(f"[INFO] Database {db['name']} may already exist")

        # Grant privileges
        grant_sql = f"GRANT ALL PRIVILEGES ON DATABASE {db['name']} TO {db['user']};"
        run_psql_command(
            ["-c", grant_sql],
            f"Granting privileges to {db['user']}",
            postgresql_bin,
            postgres_password,
        )

    print("\n" + "=" * 60)
    print(f"Database Setup Complete! ({success_count}/{len(databases)} databases created)")
    print("=" * 60)

    for db in databases:
        print(f"\n{db['Description']}:")
        print(f"  Database: {db['name']}")
        print(f"  User: {db['user']}")
        print(
            f"  Connection URL: postgresql+asyncpg://{db['user']}:{db['password']}@localhost:5432/{db['name']}"
        )

    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        create_databases()
    except KeyboardInterrupt:
        print("\n[INFO] Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
