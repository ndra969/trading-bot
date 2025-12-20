#!/usr/bin/env python3
"""
Environment Setup Script

This script automatically copies the appropriate environment file
based on the current environment (development/production).
"""

import os
import sys
from pathlib import Path


def setup_environment():
    """Setup environment file based on environment variable"""

    # Get environment from environment variable or default to development
    env = os.getenv("TRADING_BOT_ENV", "development").lower()

    # Map environment to correct file
    env_files = {
        "development": ".env.dev",
        "dev": ".env.dev",
        "production": ".env.prd",
        "prod": ".env.prd",
    }

    if env not in env_files:
        print(f"[ERROR] Invalid environment: {env}")
        print(f"[INFO] Valid environments: {', '.join(env_files.keys())}")
        sys.exit(1)

    source_file = env_files[env]
    target_file = ".env"

    # Check if source file exists
    if not Path(source_file).exists():
        print(f"[ERROR] Source environment file not found: {source_file}")
        sys.exit(1)

    # Copy the appropriate environment file
    try:
        import shutil

        shutil.copy2(source_file, target_file)
        print(f"[SUCCESS] Environment setup complete: {target_file} <- {source_file}")
        print(f"[INFO] Environment: {env}")

        # Show database URL being used
        with open(target_file) as f:
            content = f.read()
            for line in content.split("\n"):
                if line.startswith("DATABASE_URL="):
                    print(f"[INFO] Database URL: {line.split('=', 1)[1]}")
                    break
            else:
                print("[INFO] Database URL: DATABASE_URL not found in environment file")

    except Exception as e:
        print(f"[ERROR] Failed to setup environment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    setup_environment()
