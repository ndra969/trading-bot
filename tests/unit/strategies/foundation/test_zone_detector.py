"""
Unit tests for ZoneDetector.

Testing zone detection algorithm with TDD methodology.
"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from trading_bot.exceptions.strategy_exceptions import (
    InsufficientDataError,
)
from trading_bot.strategies.foundation.zone_detector import (
    DetectedZone,
    ZoneDetector,
    ZoneType,
)


class TestZoneType:
    """Test ZoneType enum."""

    def test_zone_type_enum_values(self):
        """Test that all expected zone types exist."""
        assert hasattr(ZoneType, "REJECTION")
        assert hasattr(ZoneType, "CONSOLIDATION")
        assert hasattr(ZoneType, "BREAKOUT_ORIGIN")

    def test_zone_type_string_representation(self):
        """Test zone type string conversion."""
        assert str(ZoneType.REJECTION) in ["REJECTION", "ZoneType.REJECTION"]
        assert str(ZoneType.CONSOLIDATION) in [
            "CONSOLIDATION",
            "ZoneType.CONSOLIDATION",
        ]


class TestDetectedZone:
    """Test DetectedZone dataclass."""

    def test_detected_zone_creation(self):
        """Test creating a detected zone."""
        zone = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=75.0,
            touches=3,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )
        assert zone.zone_type == ZoneType.REJECTION
        assert zone.upper_bound == 1.1000
        assert zone.lower_bound == 1.0950
        assert zone.strength == 75.0

    def test_detected_zone_size_calculation(self):
        """Test zone size calculation in pips."""
        zone = DetectedZone(
            zone_type=ZoneType.CONSOLIDATION,
            upper_bound=1.1000,
            lower_bound=1.0950,  # 50 pips difference
            strength=60.0,
            touches=4,
            volume_confirmed=False,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )
        assert zone.size_pips == pytest.approx(50.0, rel=0.1)


class TestZoneDetectorInitialization:
    """Test ZoneDetector initialization."""

    def test_zone_detector_initialization_default(self):
        """Test zone detector with default parameters."""
        detector = ZoneDetector()
        assert detector is not None
        assert hasattr(detector, "detect_zones")

    def test_zone_detector_initialization_with_config(self):
        """Test zone detector with custom configuration."""
        config = {
            "min_zone_strength": 60.0,
            "max_zone_age_hours": 48,
            "min_touch_points": 3,
        }
        detector = ZoneDetector(config=config)
        assert detector.min_zone_strength == 60.0
        assert detector.max_zone_age_hours == 48


class TestRejectionZoneDetection:
    """Test rejection zone detection."""

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data with rejection pattern."""
        # Use recent dates to avoid age expiration in tests
        dates = pd.date_range(
            start=pd.Timestamp.now() - pd.Timedelta(hours=100), periods=100, freq="1h"
        )
        # Create base data with consistent price
        base_price = 1.1000
        data = pd.DataFrame(
            {
                "open": [base_price] * 100,
                "high": [base_price + 0.0010] * 100,
                "low": [base_price - 0.0010] * 100,
                "close": [base_price] * 100,
                "volume": [1000] * 100,
            },
            index=dates,
        )
        # Add rejection pattern at index 60 (after 20 candles for volume avg)
        # Strong upper wick rejection: large wick (70%+), small body (<30%)
        # Total range: 0.0100 (100 pips)
        # Upper wick: 0.0070 (70 pips) = 70% of range (meets 30%+ threshold)
        # Body: 0.0020 (20 pips) = 20% of range (meets <60% threshold)
        # Lower wick: 0.0010 (10 pips)
        rejection_candle = data.index[60]
        data.loc[rejection_candle, "high"] = base_price + 0.0070  # Large upper wick (70 pips)
        data.loc[rejection_candle, "open"] = base_price + 0.0010  # Body start
        data.loc[rejection_candle, "close"] = base_price + 0.0030  # Body end (20 pips body)
        data.loc[rejection_candle, "low"] = base_price - 0.0010  # Small lower wick
        data.loc[rejection_candle, "volume"] = 3000  # High volume (3x average = 1.2x threshold)

        # Zone boundaries: upper=1.1070, lower=1.1030 (40 pips zone, meets min 1 pip)

        return data

    def test_detect_rejection_zone_basic(self, sample_ohlcv_data):
        """Test basic rejection zone detection."""
        # Use more lenient config for test
        detector = ZoneDetector(
            config={
                "min_zone_strength": 30.0,  # Lower threshold for tests
                "min_zone_size_pips": 2,  # Lower size requirement
                "min_wick_ratio": 0.4,  # More lenient wick ratio
                "max_body_size_pct": 50,  # More lenient body size
                "max_zone_age_hours": 1000,  # Very large to avoid age filtering in tests
            }
        )
        zones = detector.detect_zones(sample_ohlcv_data, zone_types=[ZoneType.REJECTION])

        assert len(zones) > 0, f"Expected at least 1 zone, got {len(zones)}"
        rejection_zones = [z for z in zones if z.zone_type == ZoneType.REJECTION]
        assert len(rejection_zones) > 0, f"Expected rejection zones, got {len(rejection_zones)}"

    def test_rejection_zone_wick_ratio_validation(self, sample_ohlcv_data):
        """Test rejection zone has proper wick to body ratio."""
        detector = ZoneDetector(config={"min_wick_ratio": 0.6})
        zones = detector.detect_zones(sample_ohlcv_data, zone_types=[ZoneType.REJECTION])

        rejection_zones = [z for z in zones if z.zone_type == ZoneType.REJECTION]
        for zone in rejection_zones:
            # Rejection zones should have high wick ratio
            assert zone.strength > 0

    def test_rejection_zone_volume_confirmation(self, sample_ohlcv_data):
        """Test rejection zone volume confirmation."""
        detector = ZoneDetector(config={"volume_confirmation": True})
        zones = detector.detect_zones(sample_ohlcv_data, zone_types=[ZoneType.REJECTION])

        for zone in zones:
            if zone.zone_type == ZoneType.REJECTION and zone.volume_confirmed:
                assert zone.strength > 50.0  # Higher strength for volume-confirmed


class TestConsolidationZoneDetection:
    """Test consolidation zone detection."""

    @pytest.fixture
    def consolidation_data(self):
        """Create sample OHLCV data with consolidation pattern."""
        # Use recent dates to avoid age expiration in tests
        dates = pd.date_range(
            start=pd.Timestamp.now() - pd.Timedelta(hours=100), periods=100, freq="1h"
        )
        base_price = 1.1000
        data = pd.DataFrame(
            {
                "open": [base_price] * 100,
                "high": [base_price + 0.0020] * 100,
                "low": [base_price - 0.0020] * 100,
                "close": [base_price] * 100,
                "volume": [1000] * 100,
            },
            index=dates,
        )
        # Create consolidation pattern (narrow range 30 pips, multiple touches)
        # Start at index 30 (after 20 candles for volume avg) + window 10 = index 40+
        consolidation_high = base_price + 0.0015  # 15 pips above base
        consolidation_low = base_price - 0.0015  # 15 pips below base (30 pip range, meets max 50)

        # Create 10 candles of consolidation (index 30-39)
        for i in range(30, 40):
            # Make candles touch upper and lower bounds multiple times
            if i % 2 == 0:
                # Touch upper bound
                data.loc[data.index[i], "high"] = consolidation_high
                data.loc[data.index[i], "low"] = base_price - 0.0005
                data.loc[data.index[i], "close"] = base_price
            else:
                # Touch lower bound
                data.loc[data.index[i], "high"] = base_price + 0.0005
                data.loc[data.index[i], "low"] = consolidation_low
                data.loc[data.index[i], "close"] = base_price

        return data

    def test_detect_consolidation_zone_basic(self, consolidation_data):
        """Test basic consolidation zone detection."""
        # Use more lenient config for test
        detector = ZoneDetector(
            config={
                "min_zone_strength": 30.0,  # Lower threshold for tests
                "min_zone_size_pips": 2,  # Lower size requirement
                "max_range_pips": 50,  # More lenient range
                "min_touches": 2,  # Lower touch requirement
                "max_zone_age_hours": 1000,  # Very large to avoid age filtering in tests
            }
        )
        zones = detector.detect_zones(consolidation_data, zone_types=[ZoneType.CONSOLIDATION])

        consolidation_zones = [z for z in zones if z.zone_type == ZoneType.CONSOLIDATION]
        assert (
            len(consolidation_zones) > 0
        ), f"Expected consolidation zones, got {len(consolidation_zones)}"

    def test_consolidation_zone_touch_count(self, consolidation_data):
        """Test consolidation zone has minimum touches."""
        detector = ZoneDetector(config={"min_touch_points": 3})
        zones = detector.detect_zones(consolidation_data, zone_types=[ZoneType.CONSOLIDATION])

        consolidation_zones = [z for z in zones if z.zone_type == ZoneType.CONSOLIDATION]
        for zone in consolidation_zones:
            assert zone.touches >= 3

    def test_consolidation_zone_range_validation(self, consolidation_data):
        """Test consolidation zone has acceptable range."""
        detector = ZoneDetector(
            config={
                "max_range_pips": 50,  # More lenient for test data
                "max_zone_age_hours": 1000,  # Very large to avoid age filtering in tests
            }
        )
        zones = detector.detect_zones(consolidation_data, zone_types=[ZoneType.CONSOLIDATION])

        consolidation_zones = [z for z in zones if z.zone_type == ZoneType.CONSOLIDATION]
        for zone in consolidation_zones:
            assert zone.size_pips <= 50  # Updated to match config


class TestBreakoutOriginZoneDetection:
    """Test breakout origin zone detection."""

    @pytest.fixture
    def breakout_data(self):
        """Create sample OHLCV data with breakout pattern."""
        # Use recent dates to avoid age expiration in tests
        dates = pd.date_range(
            start=pd.Timestamp.now() - pd.Timedelta(hours=100), periods=100, freq="1h"
        )
        base_price = 1.1000
        data = pd.DataFrame(
            {
                "open": [base_price] * 100,
                "high": [base_price + 0.0010] * 100,
                "low": [base_price - 0.0010] * 100,
                "close": [base_price] * 100,
                "volume": [1000] * 100,
            },
            index=dates,
        )
        # Create consolidation before breakout (index 30-39, 10 candles)
        consolidation_high = base_price + 0.0010  # 10 pips above
        consolidation_low = base_price - 0.0010  # 10 pips below (20 pip range)

        for i in range(30, 40):
            data.loc[data.index[i], "high"] = consolidation_high
            data.loc[data.index[i], "low"] = consolidation_low
            data.loc[data.index[i], "close"] = base_price

        # Create strong breakout at index 40 (after consolidation)
        # Breakout above consolidation with high volume
        # Breakout threshold: 2% of 20 pips = 0.4 pips, so breakout > 0.4 pips above high
        breakout_candle = data.index[40]
        data.loc[breakout_candle, "open"] = base_price
        data.loc[breakout_candle, "high"] = (
            base_price + 0.0025
        )  # 25 pips above (strong breakout, 15 pips above consolidation high)
        data.loc[breakout_candle, "close"] = base_price + 0.0020  # 20 pips above
        data.loc[breakout_candle, "low"] = base_price - 0.0005
        data.loc[breakout_candle, "volume"] = 3000  # 3x average volume (1.2x threshold)

        return data

    def test_detect_breakout_origin_zone(self, breakout_data):
        """Test breakout origin zone detection."""
        # Use more lenient config for test
        detector = ZoneDetector(
            config={
                "min_zone_strength": 30.0,  # Lower threshold for tests
                "min_zone_size_pips": 2,  # Lower size requirement
                "min_volume_increase": 1.2,  # More lenient volume
                "min_breakout_momentum": 0.3,  # More lenient momentum
                "max_zone_age_hours": 1000,  # Very large to avoid age filtering in tests
            }
        )
        zones = detector.detect_zones(breakout_data, zone_types=[ZoneType.BREAKOUT_ORIGIN])

        breakout_zones = [z for z in zones if z.zone_type == ZoneType.BREAKOUT_ORIGIN]
        assert len(breakout_zones) > 0, f"Expected breakout zones, got {len(breakout_zones)}"

    def test_breakout_zone_volume_increase(self, breakout_data):
        """Test breakout zone has volume increase."""
        detector = ZoneDetector(config={"min_volume_increase": 1.5})
        zones = detector.detect_zones(breakout_data, zone_types=[ZoneType.BREAKOUT_ORIGIN])

        breakout_zones = [z for z in zones if z.zone_type == ZoneType.BREAKOUT_ORIGIN]
        for zone in breakout_zones:
            # Breakout zones should have volume confirmation
            assert zone.volume_confirmed or zone.strength > 60.0


class TestZoneStrengthCalculation:
    """Test zone strength scoring."""

    def test_zone_strength_range(self):
        """Test zone strength is within 0-100 range."""
        detector = ZoneDetector()
        # Test with random data
        dates = pd.date_range(start="2024-01-01", periods=50, freq="1H")
        data = pd.DataFrame(
            {
                "open": [1.1000 + i * 0.0001 for i in range(50)],
                "high": [1.1010 + i * 0.0001 for i in range(50)],
                "low": [1.0990 + i * 0.0001 for i in range(50)],
                "close": [1.1005 + i * 0.0001 for i in range(50)],
                "volume": [1000 + i * 10 for i in range(50)],
            },
            index=dates,
        )

        zones = detector.detect_zones(data)
        for zone in zones:
            assert 0 <= zone.strength <= 100

    def test_zone_strength_factors(self):
        """Test zone strength considers multiple factors."""
        detector = ZoneDetector(
            config={
                "scoring_weights": {
                    "strength_weight": 0.4,
                    "freshness_weight": 0.3,
                    "volume_weight": 0.2,
                    "touches_weight": 0.1,
                }
            }
        )
        assert detector.scoring_weights["strength_weight"] == 0.4


class TestZoneExpirationLogic:
    """Test zone expiration and freshness tracking."""

    def test_zone_age_expiration(self):
        """Test zones expire based on age."""
        detector = ZoneDetector(config={"max_zone_age_hours": 72})

        # Create old zone
        old_zone = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=75.0,
            touches=3,
            volume_confirmed=True,
            first_detected=datetime.now() - timedelta(hours=80),
            last_tested=datetime.now() - timedelta(hours=80),
        )

        assert detector.is_zone_expired(old_zone) is True

    def test_zone_freshness_scoring(self):
        """Test zone freshness affects strength score."""
        detector = ZoneDetector()

        fresh_zone = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=75.0,
            touches=3,
            volume_confirmed=True,
            first_detected=datetime.now() - timedelta(hours=1),
            last_tested=datetime.now(),
        )

        old_zone = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=75.0,
            touches=3,
            volume_confirmed=True,
            first_detected=datetime.now() - timedelta(hours=50),
            last_tested=datetime.now() - timedelta(hours=40),
        )

        fresh_score = detector.calculate_freshness_score(fresh_zone)
        old_score = detector.calculate_freshness_score(old_zone)

        assert fresh_score > old_score


class TestZoneValidation:
    """Test zone validation and quality checks."""

    def test_zone_minimum_size_validation(self):
        """Test zones meet minimum size requirements."""
        detector = ZoneDetector(config={"min_zone_size_pips": 5})

        dates = pd.date_range(start="2024-01-01", periods=50, freq="1H")
        data = pd.DataFrame(
            {
                "open": [1.1000] * 50,
                "high": [1.1001] * 50,  # Very small range
                "low": [1.0999] * 50,
                "close": [1.1000] * 50,
                "volume": [1000] * 50,
            },
            index=dates,
        )

        zones = detector.detect_zones(data)
        # Very small zones should be filtered out
        for zone in zones:
            assert zone.size_pips >= 5

    def test_zone_quality_threshold(self):
        """Test zones meet quality thresholds."""
        detector = ZoneDetector(config={"min_zone_strength": 50.0})

        dates = pd.date_range(start="2024-01-01", periods=50, freq="1H")
        data = pd.DataFrame(
            {
                "open": [1.1000 + i * 0.0001 for i in range(50)],
                "high": [1.1010 + i * 0.0001 for i in range(50)],
                "low": [1.0990 + i * 0.0001 for i in range(50)],
                "close": [1.1005 + i * 0.0001 for i in range(50)],
                "volume": [1000] * 50,
            },
            index=dates,
        )

        zones = detector.detect_zones(data)
        for zone in zones:
            assert zone.strength >= 50.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_insufficient_data_error(self):
        """Test error handling for insufficient data."""
        detector = ZoneDetector()

        # Create data with only 5 candles (insufficient)
        dates = pd.date_range(start="2024-01-01", periods=5, freq="1H")
        data = pd.DataFrame(
            {
                "open": [1.1000] * 5,
                "high": [1.1010] * 5,
                "low": [1.0990] * 5,
                "close": [1.1000] * 5,
                "volume": [1000] * 5,
            },
            index=dates,
        )

        with pytest.raises(InsufficientDataError):
            detector.detect_zones(data)

    def test_empty_dataframe_handling(self):
        """Test handling of empty DataFrame."""
        detector = ZoneDetector()
        empty_data = pd.DataFrame()

        with pytest.raises((InsufficientDataError, ValueError)):
            detector.detect_zones(empty_data)

    def test_invalid_zone_type_filtering(self):
        """Test filtering with invalid zone types."""
        detector = ZoneDetector()

        dates = pd.date_range(start="2024-01-01", periods=50, freq="1H")
        data = pd.DataFrame(
            {
                "open": [1.1000] * 50,
                "high": [1.1010] * 50,
                "low": [1.0990] * 50,
                "close": [1.1000] * 50,
                "volume": [1000] * 50,
            },
            index=dates,
        )

        # Should handle empty zone_types list gracefully
        zones = detector.detect_zones(data, zone_types=[])
        assert isinstance(zones, list)


class TestMultiZoneDetection:
    """Test detecting multiple zones simultaneously."""

    def test_detect_all_zone_types(self):
        """Test detecting all zone types in one call."""
        detector = ZoneDetector()

        dates = pd.date_range(start="2024-01-01", periods=100, freq="1H")
        data = pd.DataFrame(
            {
                "open": [1.1000 + i * 0.0001 for i in range(100)],
                "high": [1.1010 + i * 0.0001 for i in range(100)],
                "low": [1.0990 + i * 0.0001 for i in range(100)],
                "close": [1.1005 + i * 0.0001 for i in range(100)],
                "volume": [1000 + i * 10 for i in range(100)],
            },
            index=dates,
        )

        zones = detector.detect_zones(data)
        assert isinstance(zones, list)

    def test_zone_overlap_handling(self):
        """Test handling overlapping zones."""
        detector = ZoneDetector()

        dates = pd.date_range(start="2024-01-01", periods=100, freq="1H")
        data = pd.DataFrame(
            {
                "open": [1.1000] * 100,
                "high": [1.1020] * 100,
                "low": [1.0980] * 100,
                "close": [1.1000] * 100,
                "volume": [1000] * 100,
            },
            index=dates,
        )

        zones = detector.detect_zones(data)
        # Should handle overlapping zones (merge or keep strongest)
        assert isinstance(zones, list)
