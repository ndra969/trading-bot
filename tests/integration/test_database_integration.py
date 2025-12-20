"""
Integration tests for database with trading bot components.

Tests database initialization, session management, and integration with
trading bot components.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trading_bot.config import Configuration
from trading_bot.data.database import DatabaseManager, get_session, init_database


class TestDatabaseInitialization:
    """Test database initialization integration."""

    def test_database_init_with_config(self):
        """Test database initialization with configuration."""
        config = Configuration(env="test")
        db_url = config.database.url

        manager = init_database(database_url=db_url, echo=False)

        assert manager is not None
        assert isinstance(manager, DatabaseManager)
        assert manager.database_url == db_url

    def test_database_engine_creation(self):
        """Test database engine creation."""
        db_url = "sqlite+aiosqlite:///:memory:"
        manager = DatabaseManager(database_url=db_url, echo=False)

        manager.create_engine()

        assert manager._engine is not None
        assert manager._session_maker is not None


class TestDatabaseSessionManagement:
    """Test database session management integration."""

    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test session context manager usage."""
        db_url = "sqlite+aiosqlite:///:memory:"
        manager = DatabaseManager(database_url=db_url)
        manager.create_engine()

        mock_session = AsyncMock()
        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value = mock_session_context
        manager._session_maker = mock_session_maker

        async with manager.get_session() as session:
            assert session == mock_session
            # User would call commit explicitly in real usage
            # await session.commit()

        # Session context exits normally (no exception), so rollback is not called
        # Commit is not automatically called - it's user's responsibility
        mock_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self):
        """Test session rollback on error."""
        db_url = "sqlite+aiosqlite:///:memory:"
        manager = DatabaseManager(database_url=db_url)
        manager.create_engine()

        mock_session = AsyncMock()
        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value = mock_session_context
        manager._session_maker = mock_session_maker

        with pytest.raises(ValueError):
            async with manager.get_session():
                raise ValueError("Test error")

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


class TestGlobalDatabaseFunctions:
    """Test global database functions integration."""

    def test_init_database_global(self):
        """Test global database initialization."""
        db_url = "sqlite+aiosqlite:///:memory:"

        with patch.object(DatabaseManager, "create_engine") as mock_create_engine:
            manager = init_database(database_url=db_url, echo=False)

            assert manager is not None
            mock_create_engine.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_global(self):
        """Test global get_session function."""
        db_url = "sqlite+aiosqlite:///:memory:"
        manager = DatabaseManager(database_url=db_url)

        mock_session = AsyncMock()
        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value = mock_session_context
        manager._session_maker = mock_session_maker

        # Set global manager
        import trading_bot.data.database as db_module

        db_module._db_manager = manager

        try:
            async with get_session() as session:
                assert session == mock_session
        finally:
            db_module._db_manager = None

    def test_get_session_not_initialized(self):
        """Test get_session when database not initialized."""
        import trading_bot.data.database as db_module

        original_manager = db_module._db_manager
        db_module._db_manager = None

        try:
            with pytest.raises(RuntimeError, match="Database not initialized"):
                get_session()
        finally:
            db_module._db_manager = original_manager


class TestDatabaseTableOperations:
    """Test database table operations integration."""

    @pytest.mark.asyncio
    async def test_create_tables_integration(self):
        """Test table creation integration."""
        db_url = "sqlite+aiosqlite:///:memory:"
        manager = DatabaseManager(database_url=db_url)

        mock_conn = AsyncMock()
        mock_begin = MagicMock()
        mock_begin.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_begin.__aexit__ = AsyncMock(return_value=None)

        mock_engine = MagicMock()
        mock_engine.begin = MagicMock(return_value=mock_begin)
        manager._engine = mock_engine

        await manager.create_tables()

        mock_engine.begin.assert_called_once()
        mock_conn.run_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_drop_tables_integration(self):
        """Test table dropping integration."""
        db_url = "sqlite+aiosqlite:///:memory:"
        manager = DatabaseManager(database_url=db_url)

        mock_conn = AsyncMock()
        mock_begin = MagicMock()
        mock_begin.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_begin.__aexit__ = AsyncMock(return_value=None)

        mock_engine = MagicMock()
        mock_engine.begin = MagicMock(return_value=mock_begin)
        manager._engine = mock_engine

        await manager.drop_tables()

        mock_engine.begin.assert_called_once()
        mock_conn.run_sync.assert_called_once()


class TestDatabaseCloseIntegration:
    """Test database closing integration."""

    @pytest.mark.asyncio
    async def test_close_database(self):
        """Test closing database connection."""
        db_url = "sqlite+aiosqlite:///:memory:"
        manager = DatabaseManager(database_url=db_url)

        mock_engine = AsyncMock()
        manager._engine = mock_engine

        await manager.close()

        mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_engine(self):
        """Test closing database without engine."""
        db_url = "sqlite+aiosqlite:///:memory:"
        manager = DatabaseManager(database_url=db_url)

        # Should not raise error
        await manager.close()
