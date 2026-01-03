"""
Tests for TimeframeManager.

Following TDD approach - tests written first!
"""

import pytest

from trading_bot.utils.timeframe_manager import TimeframeManager


class TestTimeframeRanking:
    """Test timeframe ranking and comparison."""

    def test_timeframe_ranking_correct_order(self):
        """Test that timeframes are ranked correctly."""
        manager = TimeframeManager()

        assert manager.rank("M1") < manager.rank("M5")
        assert manager.rank("M5") < manager.rank("M15")
        assert manager.rank("M15") < manager.rank("M30")
        assert manager.rank("M30") < manager.rank("H1")
        assert manager.rank("H1") < manager.rank("H4")
        assert manager.rank("H4") < manager.rank("D1")

    def test_is_lower_timeframe(self):
        """Test checking if one TF is lower than another."""
        manager = TimeframeManager()

        assert manager.is_lower("M30", "H1") is True
        assert manager.is_lower("H1", "M30") is False
        assert manager.is_lower("M15", "H4") is True
        assert manager.is_lower("D1", "H1") is False

    def test_invalid_timeframe_raises_error(self):
        """Test that invalid timeframe raises ValueError."""
        manager = TimeframeManager()

        with pytest.raises(ValueError, match="Unknown timeframe"):
            manager.rank("INVALID")


class TestTimeframeAlignment:
    """Test timeframe alignment detection."""

    def test_m30_aligns_with_h1_on_hour(self):
        """Test M30 alignment with H1 at top of hour."""
        manager = TimeframeManager()

        from datetime import datetime

        # Top of hour - should align
        dt = datetime(2025, 1, 1, 10, 0, 0)
        assert manager.is_aligned("M30", "H1", dt) is True

        # Half past hour - should align (2nd M30 of the H1)
        dt = datetime(2025, 1, 1, 10, 30, 0)
        assert manager.is_aligned("M30", "H1", dt) is True

        # 15 minutes - should NOT align
        dt = datetime(2025, 1, 1, 10, 15, 0)
        assert manager.is_aligned("M30", "H1", dt) is False

    def test_m15_aligns_with_h1_every_15min(self):
        """Test M15 alignment with H1."""
        manager = TimeframeManager()

        from datetime import datetime

        # All 4 M15 candles align with H1
        for minute in [0, 15, 30, 45]:
            dt = datetime(2025, 1, 1, 10, minute, 0)
            assert manager.is_aligned("M15", "H1", dt) is True

        # Other minutes don't align
        dt = datetime(2025, 1, 1, 10, 10, 0)
        assert manager.is_aligned("M15", "H1", dt) is False

    def test_h1_aligns_with_h4_on_every_hour(self):
        """Test H1 alignment - every H1 close is valid for MTF entry check."""
        manager = TimeframeManager()

        from datetime import datetime

        # For MTF, we check every H1 candle when H1 is entry TF
        # So ALL hours should align (be valid entry points)
        for hour in range(24):
            dt = datetime(2025, 1, 1, hour, 0, 0)
            assert manager.is_aligned("H1", "H4", dt) is True

        # Non-hour times don't align
        dt = datetime(2025, 1, 1, 10, 30, 0)
        assert manager.is_aligned("H1", "H4", dt) is False


class TestMTFValidation:
    """Test MTF configuration validation."""

    def test_validate_mtf_pair_success(self):
        """Test valid MTF pairs pass validation."""
        manager = TimeframeManager()

        # Entry TF must be lower than Zone TF
        manager.validate_mtf_pair(entry_tf="M30", zone_tf="H1")  # Should not raise
        manager.validate_mtf_pair(entry_tf="M15", zone_tf="H1")  # Should not raise
        manager.validate_mtf_pair(entry_tf="H1", zone_tf="H4")  # Should not raise

    def test_validate_mtf_pair_entry_higher_than_zone(self):
        """Test that entry TF higher than zone TF raises error."""
        manager = TimeframeManager()

        with pytest.raises(ValueError, match="Entry timeframe.*must be lower"):
            manager.validate_mtf_pair(entry_tf="H1", zone_tf="M30")

    def test_validate_mtf_pair_same_timeframe(self):
        """Test that same TF for both raises error."""
        manager = TimeframeManager()

        with pytest.raises(ValueError, match="same timeframe"):
            manager.validate_mtf_pair(entry_tf="H1", zone_tf="H1")


class TestTimeframeConversion:
    """Test timeframe string conversions."""

    def test_to_minutes(self):
        """Test converting timeframe to minutes."""
        manager = TimeframeManager()

        assert manager.to_minutes("M1") == 1
        assert manager.to_minutes("M5") == 5
        assert manager.to_minutes("M15") == 15
        assert manager.to_minutes("M30") == 30
        assert manager.to_minutes("H1") == 60
        assert manager.to_minutes("H4") == 240
        assert manager.to_minutes("D1") == 1440

    def test_candles_per_higher_tf(self):
        """Test calculating how many lower TF candles fit in higher TF."""
        manager = TimeframeManager()

        assert manager.candles_per_higher_tf("M30", "H1") == 2  # 2x M30 in 1 H1
        assert manager.candles_per_higher_tf("M15", "H1") == 4  # 4x M15 in 1 H1
        assert manager.candles_per_higher_tf("H1", "H4") == 4  # 4x H1 in 1 H4
        assert manager.candles_per_higher_tf("M30", "H4") == 8  # 8x M30 in 1 H4
