"""
Tests for MTFAnalyzer - Multi-Timeframe Analysis Engine.

TDD Approach: Uses mocks to isolate MTF logic from FoundationEngine complexity.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from trading_bot.strategies.foundation.zone_detector import DetectedZone, ZoneType
from trading_bot.strategies.models import SignalDirection, StrategyResult
from trading_bot.strategies.mtf_analyzer import MTFAnalyzer


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
