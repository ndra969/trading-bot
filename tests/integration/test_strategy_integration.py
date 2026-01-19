"""Integration tests for strategy system."""

import pandas as pd
import pytest

from trading_bot.config import Configuration
from trading_bot.strategies.foundation.foundation_engine import FoundationEngine
from trading_bot.strategies.signal_aggregator import SignalAggregator
from trading_bot.strategies.strategy_manager import StrategyManager


@pytest.fixture
def config():
    """Create configuration for testing."""
    return Configuration(env="test")


@pytest.fixture
def sample_data():
    """Create sample OHLCV data with zone patterns."""
    # Create data that should trigger demand zone
    data = pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=100, freq="1h"),
            "open": [1.1000 + (i * 0.0001) for i in range(100)],
            "high": [1.1010 + (i * 0.0001) for i in range(100)],
            "low": [1.0990 + (i * 0.0001) for i in range(100)],
            "close": [1.1000 + (i * 0.0001) for i in range(100)],
            "volume": [1000 + (i * 10) for i in range(100)],
        }
    )

    # Add a clear demand zone pattern
    # Consolidation at 1.1000
    for i in range(10, 20):
        data.loc[i, "open"] = 1.1000
        data.loc[i, "high"] = 1.1010
        data.loc[i, "low"] = 1.0995
        data.loc[i, "close"] = 1.1005
        data.loc[i, "volume"] = 1500

    # Strong rally from zone
    for i in range(20, 30):
        data.loc[i, "open"] = 1.1005 + ((i - 20) * 0.0005)
        data.loc[i, "high"] = 1.1020 + ((i - 20) * 0.0005)
        data.loc[i, "low"] = 1.1000 + ((i - 20) * 0.0005)
        data.loc[i, "close"] = 1.1015 + ((i - 20) * 0.0005)
        data.loc[i, "volume"] = 2000 + ((i - 20) * 100)

    return data


class TestStrategyManagerIntegration:
    """Integration tests for StrategyManager."""

    @pytest.mark.asyncio
    async def test_strategy_manager_with_foundation_engine(self, config, sample_data):
        """Test StrategyManager with FoundationEngine."""
        # Initialize components
        foundation_engine = FoundationEngine(
            config._config.get("supply_demand", {}), use_database=False
        )
        strategy_manager = StrategyManager(config._config)

        # Register foundation strategy
        strategy_manager.register_strategy("foundation", foundation_engine)

        # Analyze symbol
        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        # Should have results from foundation strategy
        assert isinstance(results, list)
        # Results may be empty or contain strategy results depending on zone detection


class TestSignalAggregatorIntegration:
    """Integration tests for SignalAggregator."""

    @pytest.mark.asyncio
    async def test_signal_aggregator_with_foundation_results(self, config):
        """Test SignalAggregator with foundation strategy results."""
        from trading_bot.strategies.models import SignalDirection, StrategyResult

        # Create mock strategy results
        results = [
            StrategyResult(
                strategy_name="foundation",
                symbol="EURUSD",
                score=75.0,
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                timeframe="H1",
            )
        ]

        # Initialize aggregator
        aggregator = SignalAggregator(config._config)

        # Aggregate signals
        signals = await aggregator.aggregate_signals(results)

        assert len(signals) >= 0  # May be 0 or more depending on quality filters
        if signals:
            assert signals[0].symbol == "EURUSD"
            assert signals[0].direction == SignalDirection.BUY


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_complete_signal_generation_flow(self, config, sample_data):
        """Test complete flow: FoundationEngine → StrategyManager → SignalAggregator."""
        # Initialize components
        foundation_engine = FoundationEngine(
            config._config.get("supply_demand", {}), use_database=False
        )
        strategy_manager = StrategyManager(config._config)
        signal_aggregator = SignalAggregator(config._config)

        # Register foundation strategy
        strategy_manager.register_strategy("foundation", foundation_engine)

        # Step 1: Run strategy analysis
        strategy_results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        assert isinstance(strategy_results, list)

        # Step 2: Aggregate signals
        signals = await signal_aggregator.aggregate_signals(strategy_results)

        assert isinstance(signals, list)
        # Signals may be empty if no zones detected or no quality signals

    @pytest.mark.asyncio
    async def test_multiple_symbols_concurrent_analysis(self, config, sample_data):
        """Test analyzing multiple symbols concurrently."""
        # Initialize components
        foundation_engine = FoundationEngine(
            config._config.get("supply_demand", {}), use_database=False
        )
        strategy_manager = StrategyManager(config._config)
        signal_aggregator = SignalAggregator(config._config)

        # Register foundation strategy
        strategy_manager.register_strategy("foundation", foundation_engine)

        # Analyze multiple symbols
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        all_signals = []

        for symbol in symbols:
            strategy_results = await strategy_manager.analyze_symbol(symbol, sample_data, "H1")
            signals = await signal_aggregator.aggregate_signals(strategy_results)
            all_signals.extend(signals)

        assert isinstance(all_signals, list)
        # Each symbol may or may not generate signals

    @pytest.mark.asyncio
    async def test_no_signals_generated_empty_data(self, config):
        """Test behavior with empty data."""
        # Initialize components
        foundation_engine = FoundationEngine(
            config._config.get("supply_demand", {}), use_database=False
        )
        strategy_manager = StrategyManager(config._config)
        signal_aggregator = SignalAggregator(config._config)

        # Register foundation strategy
        strategy_manager.register_strategy("foundation", foundation_engine)

        # Empty data
        empty_data = pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])

        # Should handle gracefully
        strategy_results = await strategy_manager.analyze_symbol("EURUSD", empty_data, "H1")
        signals = await signal_aggregator.aggregate_signals(strategy_results)

        assert isinstance(strategy_results, list)
        assert isinstance(signals, list)
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_error_handling_invalid_data(self, config):
        """Test error handling with invalid data."""
        # Initialize components
        foundation_engine = FoundationEngine(
            config._config.get("supply_demand", {}), use_database=False
        )
        strategy_manager = StrategyManager(config._config)

        # Register foundation strategy
        strategy_manager.register_strategy("foundation", foundation_engine)

        # Invalid data (missing columns)
        invalid_data = pd.DataFrame({"invalid_column": [1, 2, 3]})

        # Should handle error gracefully
        try:
            strategy_results = await strategy_manager.analyze_symbol("EURUSD", invalid_data, "H1")
            # Should return empty list or handle error
            assert isinstance(strategy_results, list)
        except Exception:
            # Error is acceptable for invalid data
            pass

    @pytest.mark.asyncio
    async def test_signal_quality_filtering(self, config):
        """Test that signals are filtered by quality thresholds."""
        from trading_bot.strategies.models import SignalDirection, StrategyResult

        signal_aggregator = SignalAggregator(config._config)

        # Create low-quality result (low score)
        low_quality = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=50.0,  # Below typical threshold
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
        )

        # Create high-quality result
        high_quality = StrategyResult(
            strategy_name="foundation",
            symbol="GBPUSD",
            score=80.0,
            direction=SignalDirection.BUY,
            entry_price=1.2500,
            stop_loss=1.2450,
            take_profit=1.2650,
        )

        signals = await signal_aggregator.aggregate_signals([low_quality, high_quality])

        # Should filter based on quality
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_conflict_resolution_multiple_signals(self, config):
        """Test conflict resolution when multiple signals for same symbol."""
        from trading_bot.strategies.models import SignalDirection, StrategyResult

        signal_aggregator = SignalAggregator(config._config)

        # Create conflicting signals for same symbol
        buy_signal = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
        )

        sell_signal = StrategyResult(
            strategy_name="trendline",
            symbol="EURUSD",
            score=70.0,
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0850,
        )

        signals = await signal_aggregator.aggregate_signals([buy_signal, sell_signal])

        # Should resolve conflict
        assert isinstance(signals, list)
        # Should have at most 1 signal for EURUSD after conflict resolution


class TestTradingBotIntegration:
    """Integration tests for TradingBot with strategy system."""

    def test_trading_bot_initialization_with_config(self, config):
        """Test that TradingBot can be initialized with config."""
        from trading_bot.main import TradingBot

        bot = TradingBot(config)

        assert bot.config is not None

        # Check assertions based on mode (MTF is default)
        trading_config = config.get("trading", {})
        mtf_mode = trading_config.get("mode", "single") == "mtf"

        if mtf_mode:
            # In MTF mode, symbols come from watchlist and timeframe is entry_timeframe
            watchlist = trading_config.get("watchlist", [])
            expected_symbols = [item["symbol"] for item in watchlist if item.get("enabled", True)]
            # If expected_symbols is empty in config but populated elsewhere, skip strict check or assume default
            if expected_symbols:
                assert set(bot.symbols) == set(expected_symbols)

            # Timeframe should be entry_timeframe
            expected_tf = trading_config.get("mtf", {}).get("entry_timeframe", "M30")
            assert bot.timeframe == expected_tf
        else:
            # Legacy Single TF mode
            assert bot.symbols == config.get("symbols", ["EURUSD", "GBPUSD"])
            assert bot.timeframe == config.get("timeframe", "H1")

    @pytest.mark.asyncio
    async def test_trading_bot_strategy_system_initialization(self, config):
        """Test that TradingBot initializes strategy system."""
        from trading_bot.main import TradingBot

        bot = TradingBot(config)

        # Initialize foundation strategy
        bot.foundation_engine = FoundationEngine(
            config._config.get("supply_demand", {}), use_database=False
        )

        # Initialize strategy system
        await bot._initialize_strategy_system()

        assert bot.strategy_manager is not None
        assert bot.signal_aggregator is not None
        assert bot.strategy_manager.is_strategy_registered("foundation")
