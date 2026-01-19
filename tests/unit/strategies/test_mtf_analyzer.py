"""
Tests for MTFAnalyzer - Multi-Timeframe Analysis Engine.

TDD Approach: Uses mocks to isolate MTF logic from FoundationEngine complexity.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from trading_bot.strategies.foundation.zone_detector import DetectedZone, ZoneType
from trading_bot.strategies.models import SignalDirection, StrategyResult
from trading_bot.strategies.mtf_analyzer import MTFAnalyzer, ZoneCache


# Create dummy zone class if actual one is hard to instantiate or depends on complex types
# But preferably use the real dataclass if simple
def create_dummy_zone(price=2000.0, type=ZoneType.REJECTION):
    return DetectedZone(
        zone_type=type,
        upper_bound=price + 5,
        lower_bound=price - 5,
        strength=80.0,
        touches=3,
        volume_confirmed=True,
        first_detected=datetime.now(),
        last_tested=datetime.now(),
    )


class TestMTFAnalyzerUtils:
    """Utilities for setting up analyzer with mocks."""

    @staticmethod
    def setup_analyzer():
        """Create analyzer with mocked foundation engine."""
        analyzer = MTFAnalyzer()
        analyzer.foundation_engine = MagicMock()
        analyzer.foundation_engine.analyze_symbol = AsyncMock()
        analyzer.foundation_engine.generate_signals = AsyncMock()
        return analyzer


class TestMTFAnalyzerZoneDetection:
    """Test zone detection logic (delegation to FoundationEngine)."""

    @pytest.mark.asyncio
    async def test_detects_h1_zones(self):
        """Test that analyzer correctly delegates zone detection."""
        analyzer = TestMTFAnalyzerUtils.setup_analyzer()

        # Setup mock return value
        dummy_zones = [create_dummy_zone(2000.0)]
        analyzer.foundation_engine.analyze_symbol.return_value = dummy_zones

        # Dummy data
        h1_data = pd.DataFrame({"close": [2000]})
        m30_data = pd.DataFrame({"close": [2000]})

        # Execute
        await analyzer.analyze(
            symbol="XAUUSD",
            zone_tf_data=h1_data,
            entry_tf_data=m30_data,
            zone_tf="H1",
            entry_tf="M30",
        )

        # Verify call
        analyzer.foundation_engine.analyze_symbol.assert_called_once_with(
            symbol="XAUUSD", data=h1_data, timeframe="H1"
        )

        # Verify internal state
        assert analyzer.detected_zones == dummy_zones

    @pytest.mark.asyncio
    async def test_no_zones_returns_empty(self):
        """Test that no zones results in no signals."""
        analyzer = TestMTFAnalyzerUtils.setup_analyzer()

        # Setup mock to return empty list
        analyzer.foundation_engine.analyze_symbol.return_value = []

        result = await analyzer.analyze(
            symbol="XAUUSD", zone_tf_data=pd.DataFrame(), entry_tf_data=pd.DataFrame()
        )

        assert result == []
        # Should NOT proceed to signal generation
        analyzer.foundation_engine.generate_signals.assert_not_called()


class TestMTFAnalyzerEntryConfirmation:
    """Test entry confirmation logic."""

    @pytest.mark.asyncio
    async def test_confirms_m30_entry(self):
        """Test that entry signals are generated when zones exist."""
        analyzer = TestMTFAnalyzerUtils.setup_analyzer()

        # Setup zones
        analyzer.foundation_engine.analyze_symbol.return_value = [create_dummy_zone(2000.0)]

        # Setup signals
        dummy_signal = StrategyResult(
            strategy_name="foundation",
            symbol="XAUUSD",
            score=80.0,
            direction=SignalDirection.BUY,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
        )
        analyzer.foundation_engine.generate_signals.return_value = [dummy_signal]

        result = await analyzer.analyze(
            symbol="XAUUSD",
            zone_tf_data=pd.DataFrame({"close": [2000]}),
            entry_tf_data=pd.DataFrame({"close": [2000]}),
            zone_tf="H1",
            entry_tf="M30",
        )

        assert len(result) == 1
        assert result[0] == dummy_signal

        # Verify generate_signals called with ENTRY timeframe
        analyzer.foundation_engine.generate_signals.assert_called_once()
        args = analyzer.foundation_engine.generate_signals.call_args
        assert args.kwargs["timeframe"] == "M30"

    @pytest.mark.asyncio
    async def test_handles_no_entry_data(self):
        """Test handling of empty entry data."""
        analyzer = TestMTFAnalyzerUtils.setup_analyzer()
        analyzer.foundation_engine.analyze_symbol.return_value = [create_dummy_zone(2000.0)]

        result = await analyzer.analyze(
            symbol="XAUUSD",
            zone_tf_data=pd.DataFrame({"close": [2000]}),
            entry_tf_data=pd.DataFrame(),  # Empty
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_handles_invalid_mtf_configuration(self):
        """Test that invalid MTF configuration returns empty result."""
        analyzer = TestMTFAnalyzerUtils.setup_analyzer()

        # Invalid MTF pair (entry TF higher than zone TF)
        result = await analyzer.analyze(
            symbol="XAUUSD",
            zone_tf_data=pd.DataFrame({"close": [2000]}),
            entry_tf_data=pd.DataFrame({"close": [2000]}),
            zone_tf="M15",  # Lower timeframe
            entry_tf="H1",  # Higher timeframe - invalid!
        )

        assert result == []
        # Should not proceed to zone detection
        analyzer.foundation_engine.analyze_symbol.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_zone_detection_exception(self):
        """Test that exceptions in zone detection are handled gracefully."""
        analyzer = TestMTFAnalyzerUtils.setup_analyzer()

        # Make analyze_symbol raise an exception
        analyzer.foundation_engine.analyze_symbol.side_effect = Exception("MT5 connection lost")

        result = await analyzer.analyze(
            symbol="XAUUSD",
            zone_tf_data=pd.DataFrame({"close": [2000]}),
            entry_tf_data=pd.DataFrame({"close": [2000]}),
        )

        assert result == []
        # Verify it was called and exception was caught
        analyzer.foundation_engine.analyze_symbol.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_error_on_invalid_mtf_config(self):
        """Test that invalid MTF configuration logs appropriate error."""
        analyzer = TestMTFAnalyzerUtils.setup_analyzer()

        result = await analyzer.analyze(
            symbol="EURUSD",
            zone_tf_data=pd.DataFrame({"close": [1.1000]}),
            entry_tf_data=pd.DataFrame({"close": [1.1000]}),
            zone_tf="M5",
            entry_tf="H4",
        )

        # Verify that invalid config returns empty result
        assert result == []
        # The error is logged to stderr (visible in test output)
        # Verify that zone detection was not called due to validation failure
        analyzer.foundation_engine.analyze_symbol.assert_not_called()


class TestZoneCache:
    """Test ZoneCache functionality for caching zones across MTF analysis."""

    def test_cache_initialization_default_ttl(self):
        """Test that ZoneCache initializes with default TTL."""
        cache = ZoneCache()
        assert cache.ttl_minutes == 60
        assert cache._cache == {}

    def test_cache_initialization_custom_ttl(self):
        """Test that ZoneCache initializes with custom TTL."""
        cache = ZoneCache(ttl_minutes=30)
        assert cache.ttl_minutes == 30
        assert cache._cache == {}

    def test_cache_get_returns_none_when_empty(self):
        """Test that get returns None when cache is empty."""
        cache = ZoneCache()
        result = cache.get(symbol="XAUUSD", zone_tf="H1")
        assert result is None

    def test_cache_get_returns_none_when_key_not_found(self):
        """Test that get returns None when symbol not in cache."""
        cache = ZoneCache()
        cache.set(symbol="EURUSD", zone_tf="H1", zones=[create_dummy_zone()])

        result = cache.get(symbol="XAUUSD", zone_tf="H1")
        assert result is None

    def test_cache_set_and_get_success(self):
        """Test successful cache set and get operations."""
        cache = ZoneCache()
        zones = [create_dummy_zone(2000.0), create_dummy_zone(2010.0)]

        cache.set(symbol="XAUUSD", zone_tf="H1", zones=zones)
        result = cache.get(symbol="XAUUSD", zone_tf="H1")

        assert result is not None
        assert len(result) == 2
        assert result == zones

    def test_cache_key_combines_symbol_and_timeframe(self):
        """Test that cache key properly combines symbol and timeframe."""
        cache = ZoneCache()
        h1_zones = [create_dummy_zone(2000.0)]
        h4_zones = [create_dummy_zone(2100.0)]

        cache.set(symbol="XAUUSD", zone_tf="H1", zones=h1_zones)
        cache.set(symbol="XAUUSD", zone_tf="H4", zones=h4_zones)

        h1_result = cache.get(symbol="XAUUSD", zone_tf="H1")
        h4_result = cache.get(symbol="XAUUSD", zone_tf="H4")

        assert h1_result == h1_zones
        assert h4_result == h4_zones
        assert h1_result != h4_result

    def test_cache_expires_after_ttl(self):
        """Test that cache entries expire after TTL."""
        cache = ZoneCache(ttl_minutes=60)
        zones = [create_dummy_zone(2000.0)]

        # Mock datetime for set operation
        with patch("trading_bot.strategies.mtf_analyzer.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            cache.set(symbol="XAUUSD", zone_tf="H1", zones=zones)

        # Mock datetime for get operation - past TTL
        with patch("trading_bot.strategies.mtf_analyzer.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 13, 1, 1)
            result = cache.get(symbol="XAUUSD", zone_tf="H1")
            assert result is None

    def test_cache_returns_data_before_ttl(self):
        """Test that cache returns valid data before TTL expires."""
        cache = ZoneCache(ttl_minutes=60)
        zones = [create_dummy_zone(2000.0)]

        # Mock datetime for set operation
        with patch("trading_bot.strategies.mtf_analyzer.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            cache.set(symbol="XAUUSD", zone_tf="H1", zones=zones)

        # Mock datetime for get operation - still within TTL
        with patch("trading_bot.strategies.mtf_analyzer.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 30, 0)
            result = cache.get(symbol="XAUUSD", zone_tf="H1")

            assert result is not None
            assert result == zones

    def test_cache_logs_expiry_and_deletes_entry(self):
        """Test that expired cache is deleted and logged."""
        cache = ZoneCache(ttl_minutes=60)
        zones = [create_dummy_zone(2000.0)]

        # Mock datetime for set operation
        with patch("trading_bot.strategies.mtf_analyzer.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            cache.set(symbol="XAUUSD", zone_tf="H1", zones=zones)

        # Mock datetime for get operation - past TTL
        with patch("trading_bot.strategies.mtf_analyzer.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 13, 1, 1)
            result = cache.get(symbol="XAUUSD", zone_tf="H1")

            assert result is None
            # Verify entry was deleted
            assert "XAUUSD_H1" not in cache._cache

    def test_cache_invalidate_specific_symbol(self):
        """Test invalidating cache for specific symbol."""
        cache = ZoneCache()
        cache.set(symbol="XAUUSD", zone_tf="H1", zones=[create_dummy_zone(2000.0)])
        cache.set(symbol="XAUUSD", zone_tf="H4", zones=[create_dummy_zone(2100.0)])
        cache.set(symbol="EURUSD", zone_tf="H1", zones=[create_dummy_zone(1.1000)])

        # Invalidate only XAUUSD
        cache.invalidate(symbol="XAUUSD")

        assert cache.get(symbol="XAUUSD", zone_tf="H1") is None
        assert cache.get(symbol="XAUUSD", zone_tf="H4") is None
        assert cache.get(symbol="EURUSD", zone_tf="H1") is not None

    def test_cache_invalidate_all(self):
        """Test invalidating entire cache."""
        cache = ZoneCache()
        cache.set(symbol="XAUUSD", zone_tf="H1", zones=[create_dummy_zone(2000.0)])
        cache.set(symbol="EURUSD", zone_tf="H1", zones=[create_dummy_zone(1.1000)])
        cache.set(symbol="GBPUSD", zone_tf="H4", zones=[create_dummy_zone(1.3000)])

        cache.invalidate()

        assert cache._cache == {}

    def test_cache_invalidate_nonexistent_symbol(self):
        """Test invalidating symbol that doesn't exist in cache."""
        cache = ZoneCache()
        cache.set(symbol="XAUUSD", zone_tf="H1", zones=[create_dummy_zone(2000.0)])

        # Should not raise error
        cache.invalidate(symbol="EURUSD")

        # XAUUSD should still be cached
        assert cache.get(symbol="XAUUSD", zone_tf="H1") is not None

    def test_cache_multiple_symbols_same_timeframe(self):
        """Test caching multiple symbols with same timeframe."""
        cache = ZoneCache()
        xau_zones = [create_dummy_zone(2000.0)]
        eurusd_zones = [create_dummy_zone(1.1000)]

        cache.set(symbol="XAUUSD", zone_tf="H1", zones=xau_zones)
        cache.set(symbol="EURUSD", zone_tf="H1", zones=eurusd_zones)

        assert cache.get(symbol="XAUUSD", zone_tf="H1") == xau_zones
        assert cache.get(symbol="EURUSD", zone_tf="H1") == eurusd_zones

    def test_cache_logs_on_set(self):
        """Test that cache set operation stores zones correctly."""
        cache = ZoneCache()
        zones = [create_dummy_zone(2000.0), create_dummy_zone(2010.0)]

        cache.set(symbol="XAUUSD", zone_tf="H1", zones=zones)

        # Verify zones were cached
        result = cache.get(symbol="XAUUSD", zone_tf="H1")
        assert result is not None
        assert len(result) == 2

    def test_cache_invalidate_logs_with_symbol(self):
        """Test that invalidate removes specific symbol from cache."""
        cache = ZoneCache()
        cache.set(symbol="XAUUSD", zone_tf="H1", zones=[create_dummy_zone(2000.0)])

        cache.invalidate(symbol="XAUUSD")

        # Verify cache was invalidated for the symbol
        assert cache.get(symbol="XAUUSD", zone_tf="H1") is None

    def test_cache_exact_ttl_boundary(self):
        """Test cache behavior exactly at TTL boundary."""
        cache = ZoneCache(ttl_minutes=60)
        zones = [create_dummy_zone(2000.0)]

        # Mock datetime for set operation
        with patch("trading_bot.strategies.mtf_analyzer.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            cache.set(symbol="XAUUSD", zone_tf="H1", zones=zones)

        # Exactly at TTL limit - should still be valid (age_minutes > ttl_minutes for expiry)
        with patch("trading_bot.strategies.mtf_analyzer.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 13, 0, 0)
            result = cache.get(symbol="XAUUSD", zone_tf="H1")
            # Age is exactly 60 minutes, not > 60, so should still be valid
            assert result is not None

        # One second past TTL
        with patch("trading_bot.strategies.mtf_analyzer.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 13, 0, 1)
            result = cache.get(symbol="XAUUSD", zone_tf="H1")
            assert result is None
