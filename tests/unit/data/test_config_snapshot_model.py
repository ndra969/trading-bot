"""
Unit tests for ConfigSnapshot model.

Tests configuration snapshot creation and utility methods.
"""

from datetime import UTC, datetime

from trading_core.data.models import ConfigSnapshot
from trading_core.utils.config_hasher import hash_config


class TestConfigSnapshotModel:
    """Test ConfigSnapshot model."""

    def test_create_config_snapshot(self):
        """Test creating config snapshot."""
        config_data = {"risk": {"max_risk": 1.0}}
        config_hash = hash_config(config_data)

        snapshot = ConfigSnapshot(
            config_hash=config_hash,
            config_json=config_data,
            description="Test config",
            environment="development",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )

        assert snapshot.config_hash == config_hash
        assert snapshot.config_json == config_data
        assert snapshot.description == "Test config"
        assert snapshot.environment == "development"

    def test_get_config_value_simple(self):
        """Test getting config value by path."""
        config_data = {"risk": {"max_risk": 1.0, "max_positions": 5}}
        snapshot = ConfigSnapshot(
            config_hash=hash_config(config_data),
            config_json=config_data,
        )

        value = snapshot.get_config_value("risk.max_risk")

        assert value == 1.0

    def test_get_config_value_nested(self):
        """Test getting nested config value."""
        config_data = {"risk": {"position_limits": {"max_positions": 5}}}
        snapshot = ConfigSnapshot(
            config_hash=hash_config(config_data),
            config_json=config_data,
        )

        value = snapshot.get_config_value("risk.position_limits.max_positions")

        assert value == 5

    def test_get_config_value_not_found(self):
        """Test getting non-existent config value returns default."""
        config_data = {"risk": {"max_risk": 1.0}}
        snapshot = ConfigSnapshot(
            config_hash=hash_config(config_data),
            config_json=config_data,
        )

        value = snapshot.get_config_value("trading.symbols", default=[])

        assert value == []

    def test_compare_with_identical_config(self):
        """Test comparing with identical config."""
        config_data = {"risk": {"max_risk": 1.0}}
        snapshot = ConfigSnapshot(
            config_hash=hash_config(config_data),
            config_json=config_data,
        )

        diff = snapshot.compare_with(config_data)

        assert len(diff["added"]) == 0
        assert len(diff["removed"]) == 0
        assert len(diff["modified"]) == 0

    def test_compare_with_different_config(self):
        """Test comparing with different config."""
        config_data1 = {"risk": {"max_risk": 1.0}}
        config_data2 = {"risk": {"max_risk": 2.0}, "trading": {"symbols": ["EURUSD"]}}

        snapshot = ConfigSnapshot(
            config_hash=hash_config(config_data1),
            config_json=config_data1,
        )

        diff = snapshot.compare_with(config_data2)

        assert "trading" in diff["added"]
        assert len(diff["modified"]) == 1
        assert diff["modified"][0]["key"] == "risk"
