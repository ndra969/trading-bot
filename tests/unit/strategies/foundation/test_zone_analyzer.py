"""
Unit tests for ZoneAnalyzer.

Testing zone analysis and quality filtering with TDD methodology.
"""

from datetime import datetime

import pytest

from trading_bot.strategies.foundation.zone_analyzer import ZoneAnalyzer
from trading_bot.strategies.foundation.zone_detector import DetectedZone, ZoneType


class TestZoneAnalyzerInitialization:
    """Test ZoneAnalyzer initialization."""

    def test_zone_analyzer_initialization_default(self):
        """Test zone analyzer with default parameters."""
        analyzer = ZoneAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, "analyze_zones")
        assert analyzer.min_zone_strength == 60.0

    def test_zone_analyzer_initialization_with_config(self):
        """Test zone analyzer with custom configuration."""
        config = {"min_zone_strength": 70.0}
        analyzer = ZoneAnalyzer(config=config)
        assert analyzer.min_zone_strength == 70.0

    def test_zone_analyzer_initialization_empty_config(self):
        """Test zone analyzer with empty config uses defaults."""
        analyzer = ZoneAnalyzer(config={})
        assert analyzer.min_zone_strength == 60.0


class TestZoneAnalyzerAnalyzeZones:
    """Test zone analysis functionality."""

    @pytest.fixture
    def sample_zones(self):
        """Create sample zones with different strengths."""
        return [
            DetectedZone(
                zone_type=ZoneType.REJECTION,
                upper_bound=1.1000,
                lower_bound=1.0950,
                strength=75.0,  # High strength
                touches=3,
                volume_confirmed=True,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
            DetectedZone(
                zone_type=ZoneType.CONSOLIDATION,
                upper_bound=1.1050,
                lower_bound=1.1000,
                strength=50.0,  # Low strength (below default 60.0)
                touches=2,
                volume_confirmed=False,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
            DetectedZone(
                zone_type=ZoneType.BREAKOUT_ORIGIN,
                upper_bound=1.1100,
                lower_bound=1.1050,
                strength=80.0,  # Very high strength
                touches=4,
                volume_confirmed=True,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
            DetectedZone(
                zone_type=ZoneType.REJECTION,
                upper_bound=1.1150,
                lower_bound=1.1100,
                strength=60.0,  # Exactly at threshold
                touches=2,
                volume_confirmed=True,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
        ]

    def test_analyze_zones_filters_by_strength(self, sample_zones):
        """Test that zones are filtered by minimum strength."""
        analyzer = ZoneAnalyzer(config={"min_zone_strength": 60.0})
        quality_zones = analyzer.analyze_zones(sample_zones)

        # Should filter out zone with strength 50.0
        assert len(quality_zones) == 3
        for zone in quality_zones:
            assert zone.strength >= 60.0

    def test_analyze_zones_sorts_by_strength(self, sample_zones):
        """Test that zones are sorted by strength (descending)."""
        analyzer = ZoneAnalyzer(config={"min_zone_strength": 60.0})
        quality_zones = analyzer.analyze_zones(sample_zones)

        # Should be sorted by strength descending
        assert len(quality_zones) == 3
        assert quality_zones[0].strength == 80.0  # Highest
        assert quality_zones[1].strength == 75.0
        assert quality_zones[2].strength == 60.0  # Lowest

    def test_analyze_zones_custom_threshold(self, sample_zones):
        """Test analysis with custom strength threshold."""
        analyzer = ZoneAnalyzer(config={"min_zone_strength": 70.0})
        quality_zones = analyzer.analyze_zones(sample_zones)

        # Should only include zones with strength >= 70.0
        assert len(quality_zones) == 2
        assert quality_zones[0].strength == 80.0
        assert quality_zones[1].strength == 75.0

    def test_analyze_zones_empty_list(self):
        """Test analyzing empty zone list."""
        analyzer = ZoneAnalyzer()
        quality_zones = analyzer.analyze_zones([])

        assert isinstance(quality_zones, list)
        assert len(quality_zones) == 0

    def test_analyze_zones_all_filtered(self):
        """Test when all zones are filtered out."""
        analyzer = ZoneAnalyzer(config={"min_zone_strength": 90.0})

        zones = [
            DetectedZone(
                zone_type=ZoneType.REJECTION,
                upper_bound=1.1000,
                lower_bound=1.0950,
                strength=50.0,  # Below threshold
                touches=2,
                volume_confirmed=False,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
            DetectedZone(
                zone_type=ZoneType.CONSOLIDATION,
                upper_bound=1.1050,
                lower_bound=1.1000,
                strength=60.0,  # Below threshold
                touches=2,
                volume_confirmed=False,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
        ]

        quality_zones = analyzer.analyze_zones(zones)
        assert len(quality_zones) == 0

    def test_analyze_zones_all_pass(self, sample_zones):
        """Test when all zones pass the threshold."""
        analyzer = ZoneAnalyzer(config={"min_zone_strength": 40.0})
        quality_zones = analyzer.analyze_zones(sample_zones)

        # All zones should pass
        assert len(quality_zones) == 4

    def test_analyze_zones_exact_threshold(self):
        """Test zones exactly at threshold are included."""
        analyzer = ZoneAnalyzer(config={"min_zone_strength": 60.0})

        zones = [
            DetectedZone(
                zone_type=ZoneType.REJECTION,
                upper_bound=1.1000,
                lower_bound=1.0950,
                strength=60.0,  # Exactly at threshold
                touches=2,
                volume_confirmed=True,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
        ]

        quality_zones = analyzer.analyze_zones(zones)
        assert len(quality_zones) == 1
        assert quality_zones[0].strength == 60.0


class TestZoneAnalyzerSorting:
    """Test zone sorting behavior."""

    def test_analyze_zones_preserves_order_for_same_strength(self):
        """Test that zones with same strength maintain relative order."""
        analyzer = ZoneAnalyzer(config={"min_zone_strength": 50.0})

        zones = [
            DetectedZone(
                zone_type=ZoneType.REJECTION,
                upper_bound=1.1000,
                lower_bound=1.0950,
                strength=60.0,
                touches=2,
                volume_confirmed=False,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
            DetectedZone(
                zone_type=ZoneType.CONSOLIDATION,
                upper_bound=1.1050,
                lower_bound=1.1000,
                strength=60.0,  # Same strength
                touches=2,
                volume_confirmed=False,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
            DetectedZone(
                zone_type=ZoneType.BREAKOUT_ORIGIN,
                upper_bound=1.1100,
                lower_bound=1.1050,
                strength=80.0,  # Highest
                touches=4,
                volume_confirmed=True,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
        ]

        quality_zones = analyzer.analyze_zones(zones)

        # Should be sorted: 80.0 first, then 60.0 zones
        assert len(quality_zones) == 3
        assert quality_zones[0].strength == 80.0
        assert quality_zones[1].strength == 60.0
        assert quality_zones[2].strength == 60.0


class TestZoneAnalyzerEdgeCases:
    """Test edge cases and error handling."""

    def test_analyze_zones_single_zone(self):
        """Test analyzing single zone."""
        analyzer = ZoneAnalyzer()

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

        quality_zones = analyzer.analyze_zones([zone])
        assert len(quality_zones) == 1
        assert quality_zones[0] == zone

    def test_analyze_zones_very_high_threshold(self):
        """Test with very high strength threshold."""
        analyzer = ZoneAnalyzer(config={"min_zone_strength": 95.0})

        zones = [
            DetectedZone(
                zone_type=ZoneType.REJECTION,
                upper_bound=1.1000,
                lower_bound=1.0950,
                strength=90.0,  # High but below threshold
                touches=5,
                volume_confirmed=True,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
        ]

        quality_zones = analyzer.analyze_zones(zones)
        assert len(quality_zones) == 0

    def test_analyze_zones_very_low_threshold(self):
        """Test with very low strength threshold."""
        analyzer = ZoneAnalyzer(config={"min_zone_strength": 10.0})

        zones = [
            DetectedZone(
                zone_type=ZoneType.REJECTION,
                upper_bound=1.1000,
                lower_bound=1.0950,
                strength=20.0,
                touches=1,
                volume_confirmed=False,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
        ]

        quality_zones = analyzer.analyze_zones(zones)
        assert len(quality_zones) == 1

    def test_analyze_zones_zero_threshold(self):
        """Test with zero strength threshold."""
        analyzer = ZoneAnalyzer(config={"min_zone_strength": 0.0})

        zones = [
            DetectedZone(
                zone_type=ZoneType.REJECTION,
                upper_bound=1.1000,
                lower_bound=1.0950,
                strength=5.0,
                touches=1,
                volume_confirmed=False,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            ),
        ]

        quality_zones = analyzer.analyze_zones(zones)
        assert len(quality_zones) == 1
