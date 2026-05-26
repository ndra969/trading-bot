"""
Database Management System

Async database layer using SQLAlchemy 2.0 with support for both SQLite and PostgreSQL.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from ..utils.logger import get_logger

logger = get_logger(__name__)

# SQLAlchemy declarative base
Base = declarative_base()


class DatabaseManager:
    """
    Database manager for async operations.

    Handles connection pooling, session management, and schema creation.
    """

    def __init__(self, database_url: str, echo: bool = False):
        """
        Initialize database manager.

        Args:
            database_url: Database connection URL
            echo: Whether to echo SQL statements
        """
        self.database_url = database_url
        self.echo = echo
        self._engine = None
        self._session_maker = None

    @staticmethod
    def _get_database_name(database_url: str) -> str:
        """
        Extract database name from URL for safe logging.

        Args:
            database_url: Database connection URL

        Returns:
            Database name without credentials
        """
        try:
            if "sqlite" in database_url:
                # Extract filename from sqlite path
                return database_url.split("///")[-1].split("/")[-1]
            else:
                # Extract database name from PostgreSQL URL
                # Format: postgresql+asyncpg://user:pass@host:port/dbname
                return database_url.split("/")[-1].split("?")[0]
        except Exception:
            return "unknown"

    def create_engine(self) -> None:
        """Create async database engine."""
        # Engine configuration
        engine_kwargs = {
            "echo": self.echo,
            "future": True,
        }

        # Use NullPool for both SQLite and PostgreSQL to avoid connection pool conflicts
        # This ensures each session gets a fresh connection and prevents
        # "another operation is in progress" errors with asyncpg
        engine_kwargs["poolclass"] = NullPool

        self._engine = create_async_engine(self.database_url, **engine_kwargs)
        self._session_maker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Extract database name from URL for logging (security)
        db_name = self._get_database_name(self.database_url)
        db_type = "PostgreSQL" if "postgresql" in self.database_url else "SQLite"
        logger.info(f"Database engine created: {db_type} ({db_name})")

    async def create_tables(self) -> None:
        """Create all database tables."""
        if self._engine is None:
            self.create_engine()

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created")

    async def drop_tables(self) -> None:
        """Drop all database tables."""
        if self._engine is None:
            self.create_engine()

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        logger.info("Database tables dropped")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session context manager.

        Yields:
            AsyncSession: Database session

        Example:
            async with db_manager.get_session() as session:
                result = await session.execute(query)
                await session.commit()
        """
        if self._session_maker is None:
            self.create_engine()

        async with self._session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """Close database engine."""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database engine closed")


# Global database manager instance
_db_manager: DatabaseManager = None


def init_database(database_url: str, echo: bool = False) -> DatabaseManager:
    """
    Initialize global database manager.

    Args:
        database_url: Database connection URL
        echo: Whether to echo SQL statements

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    _db_manager = DatabaseManager(database_url, echo)
    _db_manager.create_engine()
    return _db_manager


def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session from global manager.

    Returns:
        AsyncSession context manager
    """
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_manager.get_session()
