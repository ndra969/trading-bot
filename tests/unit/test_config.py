"""
Unit tests for configuration system.

Tests configuration loading, validation, and environment variable overrides.
"""

import os
from pathlib import Path

from trading_bot.config import Configuration, DatabaseConfig, TelegramConfig, TradingConfig


class TestConfiguration:
    """Test Configuration class."""

    def test_load_default_config(self):
        """Test loading default configuration."""
        config = Configuration(env="development")

        assert config.env == "development"
        assert config.config_dir == Path("config")

    def test_database_config(self):
        """Test database configuration."""
        config = Configuration(env="development")
        db = config.database

        assert isinstance(db, DatabaseConfig)
        assert db.url is not None
        assert db.pool_size > 0

    def test_trading_config(self):
        """Test trading configuration."""
        config = Configuration(env="development")
        trading = config.trading

        assert isinstance(trading, TradingConfig)
        assert 0.001 <= trading.risk_per_trade <= 0.05
        assert trading.max_concurrent_positions >= 1
        assert 50.0 <= trading.confluence_threshold <= 100.0

    def test_telegram_config(self):
        """Test telegram configuration."""
        config = Configuration(env="development")
        telegram = config.telegram

        assert isinstance(telegram, TelegramConfig)
        assert telegram.enabled in [True, False]

    def test_environment_override(self):
        """Test environment variable override."""
        # Set environment variable
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test.db"

        config = Configuration(env="development")
        assert config.database.url == "sqlite+aiosqlite:///test.db"

        # Cleanup
        del os.environ["DATABASE_URL"]

    def test_get_config_value(self):
        """Test getting configuration value by key."""
        config = Configuration(env="development")

        # Test dot notation
        risk = config.get("trading.risk_per_trade")
        assert risk is not None

        # Test default value
        unknown = config.get("unknown.key", "default")
        assert unknown == "default"

    def test_config_validation(self):
        """Test configuration validation."""
        config = Configuration(env="development")

        # Should not raise exception
        assert config.validate() is True
