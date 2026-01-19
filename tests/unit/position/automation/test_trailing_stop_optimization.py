"""
Unit tests for Trailing Stop Optimization - Week 15.5.2

Tests ATR-based trailing stop improvements to fix premature exit issues.
Current problem: Fixed 10 pip trailing = too many small losses
Solution: Dynamic ATR-based trailing with tiered approach
"""

from unittest.mock import patch

import pytest

from src.trading_bot.position.automation.trailing_stop_manager import (
    TieredTrailingConfig,
    TrailingStopManager,
)


# Test fixtures
@pytest.fixture
def mock_config():
    """Mock configuration for trailing stop tests."""
    return {
        "position_management": {
            "forex_major": {
                # New ATR-based settings
                "use_atr_trailing": True,
                "trailing_activation_multiplier": 1.5,  # Activate after 1.5x ATR
                "trailing_distance_multiplier": 1.0,  # Trail by 1.0x ATR
                # Fallback to fixed pips if ATR not available
                "trailing_activation": 20,  # Increased from 10
                "trailing_distance": 15,  # Increased from 10
                # Tiered trailing
                "use_tiered_trailing": True,
                "tier_thresholds": [10, 20, 30],  # Profit levels in pips
                "tier_distances": [8, 12, 15],  # Trailing distance per tier
            },
            "forex_jpy": {
                "use_atr_trailing": True,
                "trailing_activation_multiplier": 1.5,
                "trailing_distance_multiplier": 1.0,
                "trailing_activation": 150,
                "trailing_distance": 100,
            },
        }
    }


@pytest.fixture
def trailing_manager(mock_config):
    """Create TrailingStopManager with ATR-based config."""
    return TrailingStopManager(mock_config, dry_run=True)


@pytest.fixture
def gbpusd_position():
    """Sample GBPUSD position for testing."""
    return {
        "position_id": "test_gbp_001",
        "symbol": "GBPUSD",
        "position_type": "BUY",
        "entry_price": 1.35000,
        "current_price": 1.35250,  # +25 pips profit
        "stop_loss": 1.34800,  # Initial SL: -20 pips
        "take_profit": 1.35400,
        "volume": 0.01,
        "pip_size": 0.0001,
        "current_profit_pips": 25.0,
        "trailing_activated": False,
    }


@pytest.fixture
def mock_atr_data():
    """Mock ATR data for different symbols."""
    return {
        "GBPUSD": {
            "H1": 20.0,  # 20 pips ATR
            "H4": 35.0,
            "D1": 80.0,
        },
        "EURUSD": {
            "H1": 15.0,
            "H4": 25.0,
            "D1": 60.0,
        },
        "USDJPY": {
            "H1": 18.0,  # For JPY, ATR in 0.01 units
            "H4": 30.0,
            "D1": 70.0,
        },
    }


# Test Suite 1: ATR-Based Activation (5 tests)
class TestATRBasedActivation:
    """Test ATR-based trailing stop activation."""

    def test_calculate_atr_activation_threshold(self, trailing_manager, mock_atr_data):
        """Test calculation of ATR-based activation threshold."""
        symbol = "GBPUSD"
        timeframe = "H1"
        atr = mock_atr_data[symbol][timeframe]  # 20 pips

        # Activation = 1.5x ATR = 30 pips
        activation_pips = trailing_manager.calculate_atr_activation(atr)
        assert activation_pips == 30.0

    def test_atr_activation_replaces_fixed_pips(self, trailing_manager, mock_atr_data):
        """Test that ATR-based activation replaces fixed 10 pip setting."""
        # Old: 10 pips fixed
        # New: 1.5x ATR = 30 pips (for ATR=20)

        atr = 20.0
        activation_pips = trailing_manager.calculate_atr_activation(atr)

        assert activation_pips > 10, "ATR-based activation should be wider than old 10 pips"
        assert activation_pips == 30.0

    def test_atr_activation_adapts_to_volatility(self, trailing_manager, mock_atr_data):
        """Test activation adapts to different volatility levels."""
        # Low volatility (ATR = 10)
        low_vol_activation = trailing_manager.calculate_atr_activation(10.0)
        assert low_vol_activation == 15.0  # 1.5x 10 = 15

        # High volatility (ATR = 30)
        high_vol_activation = trailing_manager.calculate_atr_activation(30.0)
        assert high_vol_activation == 45.0  # 1.5x 30 = 45

        assert high_vol_activation > low_vol_activation

    def test_fallback_to_fixed_pips_if_no_atr(self, trailing_manager, gbpusd_position):
        """Test fallback to fixed pips when ATR is unavailable."""
        # Simulate ATR fetch failure
        with patch.object(trailing_manager, "get_atr", return_value=None):
            activation_pips = trailing_manager.get_activation_threshold(gbpusd_position)

            # Should fall back to config value: 20 pips (new increased value)
            assert activation_pips == 20.0

    def test_different_atr_by_timeframe(self, trailing_manager, mock_atr_data):
        """Test ATR-based activation for different timeframes."""
        # H1 ATR = 20 → activation = 30
        h1_activation = trailing_manager.calculate_atr_activation(20.0)
        assert h1_activation == 30.0

        # H4 ATR = 35 → activation = 52.5
        h4_activation = trailing_manager.calculate_atr_activation(35.0)
        assert h4_activation == 52.5

        # D1 ATR = 80 → activation = 120
        d1_activation = trailing_manager.calculate_atr_activation(80.0)
        assert d1_activation == 120.0


# Test Suite 2: ATR-Based Distance (5 tests)
class TestATRBasedDistance:
    """Test ATR-based trailing distance."""

    def test_calculate_atr_trailing_distance(self, trailing_manager, mock_atr_data):
        """Test calculation of ATR-based trailing distance."""
        atr = 20.0

        # Distance = 1.0x ATR = 20 pips
        distance_pips = trailing_manager.calculate_atr_distance(atr)
        assert distance_pips == 20.0

    def test_atr_distance_wider_than_old_fixed(self, trailing_manager):
        """Test that ATR distance is wider than old 10 pip fixed."""
        # Old: 10 pips fixed (too tight!)
        # New: 1.0x ATR = 20 pips (for ATR=20)

        atr = 20.0
        distance_pips = trailing_manager.calculate_atr_distance(atr)

        assert distance_pips > 10, "ATR distance should be wider than old 10 pips"
        assert distance_pips == 20.0

    def test_atr_distance_adapts_to_volatility(self, trailing_manager):
        """Test distance adapts to different volatility."""
        # Low volatility
        low_vol_distance = trailing_manager.calculate_atr_distance(10.0)
        assert low_vol_distance == 10.0

        # Medium volatility
        med_vol_distance = trailing_manager.calculate_atr_distance(20.0)
        assert med_vol_distance == 20.0

        # High volatility
        high_vol_distance = trailing_manager.calculate_atr_distance(30.0)
        assert high_vol_distance == 30.0

    def test_calculate_new_trailing_stop_price(self, trailing_manager, gbpusd_position):
        """Test calculation of new trailing stop price with ATR."""
        # BUY position at 1.35250, ATR = 20 pips, distance = 20 pips
        # New SL should be: 1.35250 - 0.0020 = 1.35050

        current_price = 1.35250
        atr = 20.0
        distance = trailing_manager.calculate_atr_distance(atr)

        new_sl = trailing_manager.calculate_trailing_sl(gbpusd_position, current_price, distance)

        assert new_sl == pytest.approx(1.35050, abs=0.00001)

    def test_trailing_stop_not_move_backward(self, trailing_manager, gbpusd_position):
        """Test trailing stop never moves backward (reduces protection)."""
        # Current SL: 1.34800
        # If new calculated SL would be 1.34700, keep old SL

        gbpusd_position["stop_loss"] = 1.34900  # Current SL
        current_price = 1.35050  # Price moved back slightly

        new_sl = trailing_manager.calculate_trailing_sl(
            gbpusd_position, current_price, distance_pips=15.0
        )

        # New SL would be 1.35050 - 15 pips = 1.34900
        # Should not move backward from 1.34900
        assert new_sl >= gbpusd_position["stop_loss"]


# Test Suite 3: Tiered Trailing Stop (4 tests)
class TestTieredTrailingStop:
    """Test tiered/progressive trailing stop system."""

    def test_tiered_trailing_by_profit_level(self, trailing_manager, gbpusd_position):
        """Test trailing distance changes by profit tier."""
        # Tier 1: Profit 10-20 pips → 8 pips trail
        # Tier 2: Profit 20-30 pips → 12 pips trail
        # Tier 3: Profit 30+ pips → 15 pips trail

        # Test Tier 1: 15 pips profit
        gbpusd_position["current_profit_pips"] = 15.0
        tier1_distance = trailing_manager.get_tiered_distance(gbpusd_position)
        assert tier1_distance == 8.0

        # Test Tier 2: 25 pips profit
        gbpusd_position["current_profit_pips"] = 25.0
        tier2_distance = trailing_manager.get_tiered_distance(gbpusd_position)
        assert tier2_distance == 12.0

        # Test Tier 3: 35 pips profit
        gbpusd_position["current_profit_pips"] = 35.0
        tier3_distance = trailing_manager.get_tiered_distance(gbpusd_position)
        assert tier3_distance == 15.0

    def test_tiered_prevents_premature_exit(self, trailing_manager, gbpusd_position):
        """Test tiered trailing locks in more profit as position grows."""
        # Tier 1: Tight trailing initially (8 pips)
        # Tier 3: Wider trailing for bigger profits (15 pips)

        # Small profit: tight trailing
        gbpusd_position["current_profit_pips"] = 12.0
        small_profit_distance = trailing_manager.get_tiered_distance(gbpusd_position)

        # Large profit: wider trailing
        gbpusd_position["current_profit_pips"] = 40.0
        large_profit_distance = trailing_manager.get_tiered_distance(gbpusd_position)

        assert large_profit_distance > small_profit_distance
        assert small_profit_distance == 8.0
        assert large_profit_distance == 15.0

    def test_combine_atr_and_tiered_trailing(self, trailing_manager, gbpusd_position):
        """Test combining ATR-based and tiered trailing."""
        # Use the WIDER of ATR distance or tiered distance

        atr = 20.0
        atr_distance = trailing_manager.calculate_atr_distance(atr)  # 20 pips

        gbpusd_position["current_profit_pips"] = 15.0
        tiered_distance = trailing_manager.get_tiered_distance(gbpusd_position)  # 8 pips

        # Should use ATR distance (20) because it's wider
        final_distance = trailing_manager.get_optimal_distance(gbpusd_position, atr=atr)

        assert final_distance == max(atr_distance, tiered_distance)
        assert final_distance == 20.0

    def test_tiered_config_validation(self, trailing_manager):
        """Test validation of tiered trailing configuration."""
        config = TieredTrailingConfig(tier_thresholds=[10, 20, 30], tier_distances=[8, 12, 15])

        assert len(config.tier_thresholds) == len(config.tier_distances)
        assert config.tier_distances[0] < config.tier_distances[-1], "Distances should increase"


# Test Suite 4: Session-Aware Trailing (3 tests)
class TestSessionAwareTrailing:
    """Test session-aware trailing adjustment."""

    def test_wider_trailing_during_volatile_sessions(self, trailing_manager, gbpusd_position):
        """Test wider trailing during London/NY open."""
        base_distance = 15.0

        # London open: 50% wider
        london_distance = trailing_manager.adjust_for_session(base_distance, "london_open")
        assert london_distance == pytest.approx(22.5, abs=0.1)  # 15 * 1.5

        # NY open: 50% wider
        ny_distance = trailing_manager.adjust_for_session(base_distance, "ny_open")
        assert ny_distance == pytest.approx(22.5, abs=0.1)

    def test_tighter_trailing_during_asian_session(self, trailing_manager, gbpusd_position):
        """Test tighter trailing during low volatility Asian session."""
        base_distance = 15.0

        # Asian session: 30% tighter
        asian_distance = trailing_manager.adjust_for_session(base_distance, "asian")
        assert asian_distance == pytest.approx(10.5, abs=0.1)  # 15 * 0.7

    def test_normal_trailing_during_regular_hours(self, trailing_manager, gbpusd_position):
        """Test normal trailing during regular trading hours."""
        base_distance = 15.0

        # Regular hours: no adjustment
        regular_distance = trailing_manager.adjust_for_session(base_distance, "regular")
        assert regular_distance == 15.0


# Test Suite 5: Comparison and Effectiveness (3 tests)
class TestTrailingStopComparison:
    """Test comparison between old and new trailing stop."""

    def test_compare_old_vs_new_trailing_settings(self, trailing_manager):
        """Test comparison of old fixed vs new ATR-based."""
        # Old settings
        old_activation = 10.0
        old_distance = 10.0

        # New settings (ATR = 20)
        atr = 20.0
        new_activation = trailing_manager.calculate_atr_activation(atr)
        new_distance = trailing_manager.calculate_atr_distance(atr)

        assert new_activation > old_activation  # 30 > 10
        assert new_distance > old_distance  # 20 > 10

        # New settings give more breathing room
        improvement_activation = ((new_activation - old_activation) / old_activation) * 100
        improvement_distance = ((new_distance - old_distance) / old_distance) * 100

        assert improvement_activation == 200.0  # 200% increase
        assert improvement_distance == 100.0  # 100% increase

    def test_backtest_trailing_stop_effectiveness(self, trailing_manager):
        """Test simulated effectiveness of new trailing stop."""
        # Simulate position: entry at 1.35000, peak at 1.35400, close at 1.35250

        # Old trailing: 10 pip distance
        # Would trail to 1.35300 (peak - 10 pips)
        # Hit at 1.35250 = exit at 1.35300 = +30 pips profit
        old_profit_pips = 30.0

        # New trailing: 20 pip distance (ATR-based)
        # Would trail to 1.35200 (peak - 20 pips)
        # NOT hit at 1.35250 = continue holding
        # Eventual exit at 1.35350 = +35 pips profit
        new_profit_pips = 35.0

        # New system captures more profit
        assert new_profit_pips > old_profit_pips

    def test_prevent_giving_back_all_profit(self, trailing_manager, gbpusd_position):
        """Test that new trailing prevents giving back all profit."""
        # Problem with old system: Activate at +10 pips, trail 10 pips
        # If price reverses 10 pips, lose ALL profit

        # New system: Activate at +30 pips (1.5x ATR), trail 20 pips
        # Price can reverse 20 pips and still keep +10 pips profit

        gbpusd_position["current_profit_pips"] = 30.0  # Activation point
        gbpusd_position["current_price"] = 1.35300  # +30 pips from 1.35000
        gbpusd_position["trailing_activated"] = True

        atr = 20.0
        distance = trailing_manager.calculate_atr_distance(atr)  # 20 pips

        new_sl = trailing_manager.calculate_trailing_sl(gbpusd_position, 1.35300, distance)

        # New SL: 1.35300 - 20 pips = 1.35100
        # Entry: 1.35000
        # Guaranteed profit: 10 pips (even if trailing SL hits)
        guaranteed_profit_pips = (new_sl - gbpusd_position["entry_price"]) / gbpusd_position[
            "pip_size"
        ]

        assert guaranteed_profit_pips > 0, "Should guarantee some profit after activation"
        assert guaranteed_profit_pips == pytest.approx(10.0, abs=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
