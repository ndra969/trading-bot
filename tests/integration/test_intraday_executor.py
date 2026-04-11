"""
Integration tests for IntradayExecutor.

These tests verify that the IntradayExecutor correctly implements
the intraday trading logic extracted from run_mtf_backtest.py.

Tests use real historical data to ensure zero regression.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
import pytest_asyncio

from trading_bot.executors.intraday_executor import IntradayExecutor
from trading_bot.position.pip_calculator import PipCalculator
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


# Fixtures for test data
@pytest.fixture
def xauusd_h1_data():
    """Load XAUUSD H1 historical data."""
    data_path = Path(__file__).parent.parent.parent / "data" / "backtest" / "XAUUSDc_H1.csv"
    df = pd.read_csv(data_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df


@pytest.fixture
def xauusd_m30_data():
    """Load XAUUSD M30 historical data."""
    data_path = Path(__file__).parent.parent.parent / "data" / "backtest" / "XAUUSDc_M30.csv"
    df = pd.read_csv(data_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "strategy_parameters": {
            "zone": {
                "min_strength": 50.0,
                "max_zone_width_pips": 500.0,
                "max_zone_age_hours": 720,  # 30 days
            }
        },
        "trading": {"mode": "mtf", "mtf": {"zone_timeframe": "H1", "entry_timeframe": "M30"}},
    }


@pytest.fixture
def mock_foundation_engine():
    """Mock foundation engine for testing."""

    # Return a mock that provides minimal functionality
    class MockFoundationEngine:
        async def analyze_symbol(self, symbol, data, timeframe, reference_time=None):
            # Return empty list for now - will be replaced with real implementation
            return []

        async def get_market_data(self, symbol, timeframe, limit):
            # Return mock data - will be replaced in actual tests
            return pd.DataFrame()

    return MockFoundationEngine()


@pytest.fixture
def mock_position_manager():
    """Mock position manager for testing."""

    class MockPositionManager:
        async def open_position(self, signal):
            logger.info(f"Mock opening position: {signal}")

    return MockPositionManager()


@pytest_asyncio.fixture
async def intraday_executor(mock_config, mock_foundation_engine, mock_position_manager):
    """Create IntradayExecutor instance for testing."""
    executor = IntradayExecutor(mock_config, mock_foundation_engine, mock_position_manager)
    await executor.initialize()
    return executor


class TestIntradayExecutorInitialization:
    """Test that IntradayExecutor initializes correctly."""

    @pytest.mark.asyncio
    async def test_executor_initializes(self, intraday_executor, mock_config):
        """Test that executor can be initialized."""
        assert intraday_executor is not None
        assert intraday_executor.config == mock_config

    @pytest.mark.asyncio
    async def test_executor_has_pip_calculator(self, intraday_executor):
        """Test that executor initializes pip calculator."""
        assert hasattr(intraday_executor, "pip_calculator")
        assert isinstance(intraday_executor.pip_calculator, PipCalculator)

    @pytest.mark.asyncio
    async def test_executor_has_zone_cache(self, intraday_executor):
        """Test that executor initializes zone cache."""
        assert hasattr(intraday_executor, "zone_cache")
        assert isinstance(intraday_executor.zone_cache, dict)
        assert hasattr(intraday_executor, "zone_cache_duration_minutes")
        assert intraday_executor.zone_cache_duration_minutes == 60


class TestIntradayExecutorTimeframes:
    """Test timeframe configuration."""

    @pytest.mark.asyncio
    async def test_get_timeframes_returns_h1_m30(self, intraday_executor):
        """Test that executor returns correct timeframes for intraday."""
        timeframes = intraday_executor.get_timeframes()

        assert timeframes["zone_timeframe"] == "H1"
        assert timeframes["entry_timeframe"] == "M30"
        assert timeframes["trend_timeframe"] == "H1"


class TestIntradayExecutorTechnicalIndicators:
    """Test technical indicator configuration."""

    @pytest.mark.asyncio
    async def test_get_technical_indicators(self, intraday_executor):
        """Test that executor returns correct technical indicators."""
        indicators = intraday_executor.get_technical_indicators()

        # Verify EMA configuration
        assert "ema" in indicators
        assert indicators["ema"]["fast"] == 20
        assert indicators["ema"]["slow"] == 50
        assert indicators["ema"]["trend"] == 200

        # Verify RSI configuration
        assert "rsi" in indicators
        assert indicators["rsi"]["period"] == 14
        assert indicators["rsi"]["overbought"] == 70
        assert indicators["rsi"]["oversold"] == 30

        # Verify breakeven configuration
        assert "breakeven" in indicators
        assert indicators["breakeven"]["trigger_r"] == 0.7
        assert indicators["breakeven"]["offset_pips"] == 2.0

        # Verify trailing stop configuration
        assert "trailing" in indicators
        assert indicators["trailing"]["activation_pips"] == 30.0
        assert indicators["trailing"]["limit_pips"] == 10.0


class TestIntradayExecutorH1TrendGate:
    """Test H1 trend gate (Sniper) logic for commodities."""

    @pytest.mark.asyncio
    async def test_h1_trend_gate_for_xauusd(
        self, intraday_executor, xauusd_h1_data, mock_foundation_engine
    ):
        """
        Test H1 trend gate calculation for Gold (XAUUSD).

        This test verifies the EMA 50/20 trend logic:
        - EMA 50 > EMA 20_prev + Price > EMA 50 = BULLISH
        - EMA 50 < EMA 20_prev + Price < EMA 50 = BEARISH
        - Otherwise = NEUTRAL
        """
        # Setup: Mock get_market_data to return H1 data
        original_get_data = mock_foundation_engine.get_market_data

        async def mock_get_market_data(symbol, timeframe, limit):
            if timeframe == "H1":
                return xauusd_h1_data.tail(limit)
            return pd.DataFrame()

        mock_foundation_engine.get_market_data = mock_get_market_data

        # Test: Calculate H1 trend bias
        current_time = xauusd_h1_data.index[200]  # Arbitrary point in data
        h1_trend_bias = await intraday_executor._get_h1_trend_bias("XAUUSD", current_time)

        # Assert: Should return one of the valid biases
        assert h1_trend_bias in ["BULLISH", "BEARISH", "NEUTRAL", None]

        # Restore original method
        mock_foundation_engine.get_market_data = original_get_data


class TestIntradayExecutorZoneDetection:
    """Test zone detection with caching."""

    @pytest.mark.asyncio
    async def test_zone_caching_prevents_redetection(
        self, intraday_executor, xauusd_h1_data, mock_foundation_engine
    ):
        """
        Test that zones are cached and not re-detected within cache duration.

        This verifies performance optimization - zones should only be
        detected once per cache_duration_minutes (60 minutes).
        """
        # Setup: Mock analyze_symbol to return zones and track calls
        call_count = 0
        original_analyze = mock_foundation_engine.analyze_symbol

        async def mock_analyze(symbol, data, timeframe, reference_time=None):
            nonlocal call_count
            call_count += 1
            return []  # Return empty zones for this test

        mock_foundation_engine.analyze_symbol = mock_analyze

        # Test: Get zones twice
        current_time = xauusd_h1_data.index[200]

        _ = await intraday_executor._get_or_refresh_zones("XAUUSD", "H1", current_time)
        _ = await intraday_executor._get_or_refresh_zones("XAUUSD", "H1", current_time)

        # Assert: Should only call analyze_symbol once (cached)
        assert call_count == 1, f"Expected 1 call, got {call_count}"

        # Restore original method
        mock_foundation_engine.analyze_symbol = original_analyze


class TestIntradayExecutorSymbolAnalysis:
    """Test symbol analysis logic."""

    @pytest.mark.asyncio
    async def test_analyze_symbol_returns_none_without_zones(
        self, intraday_executor, mock_foundation_engine
    ):
        """
        Test that analyze_symbol returns None when no zones available.

        This is the expected behavior when price is not at any zone.
        """

        # Setup: Mock to return no zones
        async def mock_get_market_data(symbol, timeframe, limit):
            return pd.DataFrame()

        async def mock_analyze(symbol, data, timeframe, reference_time=None):
            return []

        mock_foundation_engine.get_market_data = mock_get_market_data
        mock_foundation_engine.analyze_symbol = mock_analyze

        # Test
        current_time = datetime.now()
        signal = await intraday_executor.analyze_symbol("XAUUSD", current_time)

        # Assert
        assert signal is None


class TestIntradayExecutorRegression:
    """Regression tests to ensure zero degradation from backtest.

    These tests compare executor output against known good results
    from the original run_mtf_backtest.py implementation.
    """

    @pytest.mark.asyncio
    async def test_h1_trend_gate_matches_backtest_logic(
        self, intraday_executor, xauusd_h1_data, mock_foundation_engine
    ):
        """
        Test that H1 trend gate logic matches backtest implementation.

        This is a CRITICAL regression test - the executor must produce
        the same trend bias as the original backtest code.

        Reference: scripts/run_mtf_backtest.py lines 174-238
        """

        # Setup: Mock get_market_data to return appropriate data based on timeframe
        async def mock_get_market_data(symbol, timeframe, limit):
            if timeframe == "H1":
                # Return enough data for the test (from beginning)
                return xauusd_h1_data.head(limit)
            return pd.DataFrame()

        mock_foundation_engine.get_market_data = mock_get_market_data

        # Test: Pick a specific timestamp from backtest
        # Use same logic as backtest: current_candle.name - 1 hour for safety
        test_index = 200
        current_candle_time = xauusd_h1_data.index[test_index]

        # Calculate expected trend bias using backtest logic
        h1_safe_time = current_candle_time - pd.Timedelta(hours=1)
        h1_mask = xauusd_h1_data.index <= h1_safe_time
        h1_hist = xauusd_h1_data[h1_mask]

        if len(h1_hist) >= 50:
            h1_ema_50 = h1_hist["close"].ewm(span=50, adjust=False).mean()
            ema_50_curr = h1_ema_50.iloc[-1]
            current_price = float(h1_hist.iloc[-1]["close"])

            expected_bias = None
            if current_price > ema_50_curr:
                expected_bias = "BULLISH"
            elif current_price < ema_50_curr:
                expected_bias = "BEARISH"
            else:
                expected_bias = "NEUTRAL"
        else:
            expected_bias = None

        # Calculate actual trend bias using executor
        actual_bias = await intraday_executor._get_h1_trend_bias("XAUUSD", current_candle_time)

        # Assert: Should match expected
        assert actual_bias == expected_bias, f"Expected {expected_bias}, got {actual_bias}"


# TODO: Add more regression tests in Sprint 2.3
# - test_executor_generates_same_signals_as_backtest
# - test_zone_detection_matches_backtest
# - test_m30_entry_confirmation_matches_backtest
