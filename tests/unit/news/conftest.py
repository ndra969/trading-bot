"""Fixtures for news tests that touch the DB (NewsRepository).

Mirrors tests/unit/data/conftest.py: a per-test SQLite file database with all
tables created (NewsEventRecord registers on Base.metadata via trading_core's
data package import). Pure-parser tests don't use this fixture.
"""

import os
import tempfile

import pytest_asyncio
from trading_core.data.database import init_database


@pytest_asyncio.fixture(scope="function")
async def db():
    """Per-test SQLite database with tables created (opt-in, not autouse)."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    database_url = f"sqlite+aiosqlite:///{db_path}"

    db_manager = init_database(database_url, echo=False)
    await db_manager.create_tables()

    yield

    await db_manager.drop_tables()
    await db_manager.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass
