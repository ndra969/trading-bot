"""
Pytest fixtures for data layer tests.
"""

import os

import pytest_asyncio
from trading_core.data.database import init_database


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_database():
    """
    Setup test database before each test.

    This fixture initializes the database connection for each test function.
    Uses SQLite file database for testing (in-memory doesn't work with aiosqlite connection pooling).
    """
    # Use SQLite file database for testing
    # Note: Using :memory: doesn't work with aiosqlite's connection pooling
    import tempfile

    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    database_url = f"sqlite+aiosqlite:///{db_path}"

    # Initialize database and get manager
    db_manager = init_database(database_url, echo=False)

    # Import all models to ensure they're registered

    # Create all tables
    await db_manager.create_tables()

    yield

    # Teardown - drop tables and remove file
    await db_manager.drop_tables()
    await db_manager.close()

    # Remove temp database file
    try:
        os.unlink(db_path)
    except Exception:
        pass  # Best effort cleanup
