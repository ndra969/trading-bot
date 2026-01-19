"""
Unit tests for Enhanced Signal Validator - Week 15.5.3

Tests entry quality improvements to raise win rate from 39% to 50%+.
Current problem: Low confluence entries (33-40%) accepted, no trend validation
Solution: Strict filters - 75% min confluence, trend alignment, volatility check
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.trading_bot.strategies.signal_validator_enhanced import (
    SignalValidatorEnhanced,
    TrendDirection,
)


# Test fixtures
@pytest.fixture
def mock_config():
    """Mock configuration with enhanced validation settings."""
    return {
        "strategy": {
            # Raised from 65% to 75%
            "min_confluence_score": 75.0,
            # New filters
            "trend_alignment_required": True,
            "volatility_filter_enabled": True,
            "max_atr_multiplier": 1.5,  # Reject if ATR > 1.5x average
            # Market condition filters
            "news_event_filter_enabled": True,
            "spread_filter_enabled": True,
            "max_spread_pips": 3.0,
        }
    }


@pytest.fixture
def signal_validator(mock_config):
    """Create SignalValidatorEnhanced instance."""
    return SignalValidatorEnhanced(mock_config)


@pytest.fixture
def high_quality_signal():
    """High quality signal (should pass all filters)."""
    return {
        "symbol": "GBPUSD",
        "direction": "BUY",
        "entry_price": 1.35000,
        "stop_loss": 1.34800,
        "take_profit": 1.35400,
        "final_confidence": 85.0,  # High confluence
        "risk_reward_ratio": 2.0,
        "generated_at": datetime.utcnow(),
    }


@pytest.fixture
def low_quality_signal():
    """Low quality signal (should be rejected)."""
    return {
        "symbol": "GBPUSD",
        "direction": "BUY",
        "entry_price": 1.35000,
        "stop_loss": 1.34800,
        "take_profit": 1.35400,
        "final_confidence": 40.0,  # Low confluence (below 75%)
        "risk_reward_ratio": 1.5,
        "generated_at": datetime.utcnow(),
    }


# Test Suite 1: Minimum Confluence Enforcement (3 tests)
class TestMinimumConfluenceEnforcement:
    """Test minimum confluence threshold enforcement."""

    def test_reject_low_confluence_signal(self, signal_validator, low_quality_signal):
        """Test rejection of signals below 75% confluence."""
        result = signal_validator.validate_signal(low_quality_signal)

        assert result.is_valid is False
        assert "low_confluence" in result.rejection_reasons
        assert low_quality_signal["final_confidence"] < 75.0

    def test_accept_high_confluence_signal(self, signal_validator, high_quality_signal):
        """Test acceptance of signals above 75% confluence."""
        # Mock trend and volatility checks to pass
        with (
            patch.object(signal_validator, "check_trend_alignment", return_value=True),
            patch.object(signal_validator, "check_volatility", return_value=True),
        ):
            result = signal_validator.validate_signal(high_quality_signal)

            assert result.is_valid is True
            assert high_quality_signal["final_confidence"] >= 75.0

    def test_confluence_threshold_configurable(self, signal_validator):
        """Test that confluence threshold is configurable."""
        # Default: 75%
        assert signal_validator.min_confluence == 75.0

        # Update config
        signal_validator.min_confluence = 80.0
        assert signal_validator.min_confluence == 80.0


# Test Suite 2: Trend Alignment Filter (4 tests)
class TestTrendAlignmentFilter:
    """Test trend alignment validation."""

    def test_buy_signal_requires_bullish_trend(self, signal_validator, high_quality_signal):
        """Test BUY signal requires bullish H4 and D1 trend."""
        # Mock trend data
        with patch.object(signal_validator, "get_trend_direction") as mock_trend:
            # H4 and D1 both bullish
            mock_trend.side_effect = lambda symbol, tf: TrendDirection.BULLISH

            result = signal_validator.check_trend_alignment(high_quality_signal)
            assert result is True

    def test_buy_signal_rejected_if_bearish_trend(self, signal_validator, high_quality_signal):
        """Test BUY signal rejected if H4 or D1 is bearish."""
        with patch.object(signal_validator, "get_trend_direction") as mock_trend:
            # H4 bullish but D1 bearish
            mock_trend.side_effect = lambda s, tf: (
                TrendDirection.BULLISH if tf == "H4" else TrendDirection.BEARISH
            )

            result = signal_validator.check_trend_alignment(high_quality_signal)
            assert result is False

    def test_sell_signal_requires_bearish_trend(self, signal_validator, high_quality_signal):
        """Test SELL signal requires bearish H4 and D1 trend."""
        high_quality_signal["direction"] = "SELL"

        with patch.object(signal_validator, "get_trend_direction") as mock_trend:
            # H4 and D1 both bearish
            mock_trend.side_effect = lambda symbol, tf: TrendDirection.BEARISH

            result = signal_validator.check_trend_alignment(high_quality_signal)
            assert result is True

    def test_trend_alignment_can_be_disabled(self, signal_validator, high_quality_signal):
        """Test trend alignment check can be disabled."""
        signal_validator.trend_alignment_required = False

        # Should pass even with misaligned trend
        with patch.object(
            signal_validator, "get_trend_direction", return_value=TrendDirection.BEARISH
        ):
            result = signal_validator.check_trend_alignment(high_quality_signal)
            assert result is True  # Disabled, so always pass


# Test Suite 3: Volatility Filter (3 tests)
class TestVolatilityFilter:
    """Test volatility filtering."""

    def test_reject_signal_during_extreme_volatility(self, signal_validator, high_quality_signal):
        """Test signal rejection when volatility is too high."""
        # Mock ATR: current = 30, average = 15
        # Ratio = 2.0x (exceeds max 1.5x)
        with (
            patch.object(signal_validator, "get_atr", return_value=30.0),
            patch.object(signal_validator, "get_average_atr", return_value=15.0),
        ):
            result = signal_validator.check_volatility(high_quality_signal)

            assert result is False  # Rejected
            assert 2.0 > signal_validator.max_atr_multiplier

    def test_accept_signal_during_normal_volatility(self, signal_validator, high_quality_signal):
        """Test signal acceptance when volatility is normal."""
        # Mock ATR: current = 18, average = 15
        # Ratio = 1.2x (within max 1.5x)
        with (
            patch.object(signal_validator, "get_atr", return_value=18.0),
            patch.object(signal_validator, "get_average_atr", return_value=15.0),
        ):
            result = signal_validator.check_volatility(high_quality_signal)

            assert result is True
            assert 1.2 <= signal_validator.max_atr_multiplier

    def test_volatility_filter_can_be_disabled(self, signal_validator, high_quality_signal):
        """Test volatility filter can be disabled."""
        signal_validator.volatility_filter_enabled = False

        # Should pass even with extreme volatility
        with (
            patch.object(signal_validator, "get_atr", return_value=50.0),
            patch.object(signal_validator, "get_average_atr", return_value=15.0),
        ):
            result = signal_validator.check_volatility(high_quality_signal)
            assert result is True


# Test Suite 4: Market Condition Filters (3 tests)
class TestMarketConditionFilters:
    """Test additional market condition filters."""

    def test_reject_signal_during_news_event(self, signal_validator, high_quality_signal):
        """Test signal rejection during high-impact news events."""
        with patch.object(signal_validator, "is_news_event", return_value=True):
            result = signal_validator.check_market_conditions(high_quality_signal)

            assert result is False

    def test_reject_signal_with_wide_spread(self, signal_validator, high_quality_signal):
        """Test signal rejection when spread is too wide."""
        # Mock spread: 5 pips (exceeds max 3 pips)
        with patch.object(signal_validator, "get_current_spread", return_value=5.0):
            result = signal_validator.check_spread(high_quality_signal)

            assert result is False
            assert 5.0 > signal_validator.max_spread_pips

    def test_accept_signal_with_normal_spread(self, signal_validator, high_quality_signal):
        """Test signal acceptance with normal spread."""
        # Mock spread: 2 pips (within max 3 pips)
        with patch.object(signal_validator, "get_current_spread", return_value=2.0):
            result = signal_validator.check_spread(high_quality_signal)

            assert result is True


# Test Suite 5: Complete Validation Flow (2 tests)
class TestCompleteValidationFlow:
    """Test complete signal validation workflow."""

    def test_high_quality_signal_passes_all_filters(self, signal_validator, high_quality_signal):
        """Test high quality signal passes all validation filters."""
        # Mock all checks to pass
        with (
            patch.object(signal_validator, "check_trend_alignment", return_value=True),
            patch.object(signal_validator, "check_volatility", return_value=True),
            patch.object(signal_validator, "check_market_conditions", return_value=True),
            patch.object(signal_validator, "check_spread", return_value=True),
        ):
            result = signal_validator.validate_signal(high_quality_signal)

            assert result.is_valid is True
            assert len(result.rejection_reasons) == 0
            assert result.quality_score >= 80.0

    def test_low_quality_signal_fails_multiple_filters(self, signal_validator, low_quality_signal):
        """Test low quality signal fails multiple filters."""
        # Mock some checks to fail
        with (
            patch.object(signal_validator, "check_trend_alignment", return_value=False),
            patch.object(signal_validator, "check_volatility", return_value=False),
        ):
            result = signal_validator.validate_signal(low_quality_signal)

            assert result.is_valid is False
            assert len(result.rejection_reasons) >= 2
            assert "low_confluence" in result.rejection_reasons
            assert (
                "trend_misalignment" in result.rejection_reasons
                or "extreme_volatility" in result.rejection_reasons
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
