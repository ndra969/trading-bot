"""
Unit tests for config_hasher utility.

Tests SHA256 hashing for configuration dictionaries.
"""

from trading_core.utils.config_hasher import (
    compare_configs,
    hash_config,
    verify_config_hash,
)


class TestConfigHasher:
    """Test config_hasher utility functions."""

    def test_hash_config_simple(self):
        """Test hashing simple configuration."""
        config = {"risk": {"max_risk": 1.0}, "trading": {"symbols": ["EURUSD"]}}

        hash_val = hash_config(config)

        assert isinstance(hash_val, str)
        assert len(hash_val) == 64  # SHA256 produces 64 hex characters

    def test_same_config_same_hash(self):
        """Test that identical configs produce identical hashes."""
        config1 = {"risk": {"max_risk": 1.0}, "trading": {"symbols": ["EURUSD"]}}
        config2 = {"risk": {"max_risk": 1.0}, "trading": {"symbols": ["EURUSD"]}}

        hash1 = hash_config(config1)
        hash2 = hash_config(config2)

        assert hash1 == hash2

    def test_different_config_different_hash(self):
        """Test that different configs produce different hashes."""
        config1 = {"risk": {"max_risk": 1.0}}
        config2 = {"risk": {"max_risk": 2.0}}

        hash1 = hash_config(config1)
        hash2 = hash_config(config2)

        assert hash1 != hash2

    def test_order_independent_hashing(self):
        """Test that key order doesn't affect hash."""
        config1 = {"a": 1, "b": 2, "c": 3}
        config2 = {"c": 3, "a": 1, "b": 2}

        hash1 = hash_config(config1)
        hash2 = hash_config(config2)

        assert hash1 == hash2

    def test_nested_config_hashing(self):
        """Test hashing nested configuration."""
        config = {
            "risk": {
                "max_risk": 1.0,
                "position_limits": {
                    "max_positions": 5,
                    "max_per_symbol": 1,
                },
            },
            "trading": {
                "symbols": ["EURUSD", "GBPUSD"],
                "timeframes": ["H1", "H4"],
            },
        }

        hash_val = hash_config(config)

        assert isinstance(hash_val, str)
        assert len(hash_val) == 64

    def test_verify_config_hash_valid(self):
        """Test verifying valid config hash."""
        config = {"risk": {"max_risk": 1.0}}
        expected_hash = hash_config(config)

        is_valid = verify_config_hash(config, expected_hash)

        assert is_valid is True

    def test_verify_config_hash_invalid(self):
        """Test verifying invalid config hash."""
        config = {"risk": {"max_risk": 1.0}}
        wrong_hash = "0" * 64

        is_valid = verify_config_hash(config, wrong_hash)

        assert is_valid is False

    def test_compare_configs_identical(self):
        """Test comparing identical configs."""
        config1 = {"risk": {"max_risk": 1.0}}
        config2 = {"risk": {"max_risk": 1.0}}

        result = compare_configs(config1, config2)

        assert result["same_hash"] is True
        assert len(result["added"]) == 0
        assert len(result["removed"]) == 0
        assert len(result["modified"]) == 0

    def test_compare_configs_added_keys(self):
        """Test comparing configs with added keys."""
        config1 = {"risk": {"max_risk": 1.0}}
        config2 = {"risk": {"max_risk": 1.0}, "trading": {"symbols": ["EURUSD"]}}

        result = compare_configs(config1, config2)

        assert result["same_hash"] is False
        assert "trading" in result["added"]

    def test_compare_configs_removed_keys(self):
        """Test comparing configs with removed keys."""
        config1 = {"risk": {"max_risk": 1.0}, "trading": {"symbols": ["EURUSD"]}}
        config2 = {"risk": {"max_risk": 1.0}}

        result = compare_configs(config1, config2)

        assert result["same_hash"] is False
        assert "trading" in result["removed"]

    def test_compare_configs_modified_values(self):
        """Test comparing configs with modified values."""
        config1 = {"risk": {"max_risk": 1.0}}
        config2 = {"risk": {"max_risk": 2.0}}

        result = compare_configs(config1, config2)

        assert result["same_hash"] is False
        assert len(result["modified"]) == 1
        assert result["modified"][0]["key"] == "risk"
        assert result["modified"][0]["old_value"] == {"max_risk": 1.0}
        assert result["modified"][0]["new_value"] == {"max_risk": 2.0}

    def test_hash_consistency(self):
        """Test that hash is consistent across multiple calls."""
        config = {"risk": {"max_risk": 1.0}, "trading": {"symbols": ["EURUSD", "GBPUSD"]}}

        hash1 = hash_config(config)
        hash2 = hash_config(config)
        hash3 = hash_config(config)

        assert hash1 == hash2 == hash3
