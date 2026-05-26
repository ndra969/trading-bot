"""
Unit tests for ConfigRepository.

Tests CRUD operations for config snapshots.
"""

import pytest

from trading_bot.data.repositories import ConfigRepository
from trading_bot.utils.config_hasher import hash_config


class TestConfigRepository:
    """Test ConfigRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_config_snapshot(self, setup_test_database):
        """Test creating config snapshot."""
        repo = ConfigRepository()
        config_data = {"risk": {"max_risk": 1.0}, "trading": {"symbols": ["EURUSD"]}}
        
        snapshot = await repo.create(config_data, description="Test config", environment="development")
        
        assert snapshot is not None
        assert snapshot.config_hash == hash_config(config_data)
        assert snapshot.config_json == config_data
        assert snapshot.description == "Test config"
        assert snapshot.environment == "development"

    @pytest.mark.asyncio
    async def test_create_duplicate_returns_existing(self, setup_test_database):
        """Test creating duplicate config returns existing snapshot."""
        repo = ConfigRepository()
        config_data = {"risk": {"max_risk": 1.0}}
        
        # Create first time
        snapshot1 = await repo.create(config_data)
        
        # Try to create same config again
        snapshot2 = await repo.create(config_data)
        
        assert snapshot1.config_hash == snapshot2.config_hash
        assert snapshot1.created_at == snapshot2.created_at

    @pytest.mark.asyncio
    async def test_get_by_hash(self, setup_test_database):
        """Test getting config snapshot by hash."""
        repo = ConfigRepository()
        config_data = {"risk": {"max_risk": 1.0}}
        
        created = await repo.create(config_data)
        
        # Get by hash
        snapshot = await repo.get_by_hash(created.config_hash)
        
        assert snapshot is not None
        assert snapshot.config_hash == created.config_hash
        assert snapshot.config_json == config_data

    @pytest.mark.asyncio
    async def test_get_or_create_existing(self, setup_test_database):
        """Test get_or_create returns existing snapshot."""
        repo = ConfigRepository()
        config_data = {"risk": {"max_risk": 1.0}}
        
        # Create first time
        await repo.create(config_data)
        
        # Get or create
        snapshot, created = await repo.get_or_create(config_data)
        
        assert snapshot is not None
        assert created is False

    @pytest.mark.asyncio
    async def test_get_or_create_new(self, setup_test_database):
        """Test get_or_create creates new snapshot."""
        repo = ConfigRepository()
        config_data = {"risk": {"max_risk": 1.0}}
        
        snapshot, created = await repo.get_or_create(config_data)
        
        assert snapshot is not None
        assert created is True

    @pytest.mark.asyncio
    async def test_exists(self, setup_test_database):
        """Test checking if config snapshot exists."""
        repo = ConfigRepository()
        config_data = {"risk": {"max_risk": 1.0}}
        
        created = await repo.create(config_data)
        
        exists = await repo.exists(created.config_hash)
        
        assert exists is True

    @pytest.mark.asyncio
    async def test_list_recent(self, setup_test_database):
        """Test listing recent config snapshots."""
        repo = ConfigRepository()
        
        # Create multiple snapshots
        await repo.create({"risk": {"max_risk": 1.0}}, environment="development")
        await repo.create({"risk": {"max_risk": 2.0}}, environment="production")
        await repo.create({"risk": {"max_risk": 3.0}}, environment="backtest")
        
        snapshots = await repo.list_recent(limit=10)
        
        assert len(snapshots) >= 3

    @pytest.mark.asyncio
    async def test_list_recent_with_environment_filter(self, setup_test_database):
        """Test listing recent configs with environment filter."""
        repo = ConfigRepository()
        
        # Create configs with different environments
        await repo.create({"risk": {"max_risk": 1.0}}, environment="development")
        await repo.create({"risk": {"max_risk": 2.0}}, environment="production")
        await repo.create({"risk": {"max_risk": 3.0}}, environment="backtest")
        
        # Get only development configs
        dev_configs = await repo.list_recent(limit=10, environment="development")
        
        assert len(dev_configs) >= 1
        assert all(c.environment == "development" for c in dev_configs)

    @pytest.mark.asyncio
    async def test_delete(self, setup_test_database):
        """Test deleting config snapshot."""
        repo = ConfigRepository()
        config_data = {"risk": {"max_risk": 1.0}}
        
        created = await repo.create(config_data)
        
        # Delete
        deleted = await repo.delete(created.config_hash)
        
        assert deleted is True
        
        # Verify deleted
        exists = await repo.exists(created.config_hash)
        assert exists is False

    @pytest.mark.asyncio
    async def test_delete_not_found(self, setup_test_database):
        """Test deleting non-existent config returns False."""
        repo = ConfigRepository()
        
        deleted = await repo.delete("nonexistent_hash")
        
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_error_handling(self, setup_test_database, monkeypatch):
        """Test delete error handling path."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from sqlalchemy.exc import SQLAlchemyError
        from contextlib import asynccontextmanager
        
        repo = ConfigRepository()
        config_data = {"risk": {"max_risk": 1.0}}
        created = await repo.create(config_data)
        
        # Create mock session that raises on commit
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: created))
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Database error"))
        mock_session.rollback = AsyncMock()
        
        # Create async context manager mock
        @asynccontextmanager
        async def mock_get_session():
            yield mock_session
        
        # Patch get_session
        with patch("trading_bot.data.repositories.config_repository.get_session", mock_get_session):
            # Should raise exception
            with pytest.raises(SQLAlchemyError):
                await repo.delete(created.config_hash)

