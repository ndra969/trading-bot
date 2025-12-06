"""Tests for StrategyManager."""

import pandas as pd
import pytest

from trading_bot.strategies.models import SignalDirection, StrategyResult
from trading_bot.strategies.strategy_manager import StrategyManager


class MockStrategy:
    """Mock strategy for testing."""

    def __init__(self, name: str, returns_signal: bool = True, should_fail: bool = False):
        self.name = name
        self.returns_signal = returns_signal
        self.should_fail = should_fail
        self.call_count = 0

    async def generate_signals(
        self, symbol: str, data: pd.DataFrame, timeframe: str
    ) -> list[StrategyResult]:
        """Generate mock signals."""
        self.call_count += 1

        if self.should_fail:
            raise Exception(f"Strategy {self.name} failed")

        if not self.returns_signal:
            return []

        result = StrategyResult(
            strategy_name=self.name,
            symbol=symbol,
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            timeframe=timeframe,
        )
        return [result]


@pytest.fixture
def strategy_manager():
    """Create a StrategyManager instance."""
    config = {
        "strategy_manager": {
            "max_concurrent_strategies": 8,
            "conflict_prevention": True,
            "health_check_interval": 300,
        }
    }
    return StrategyManager(config)


@pytest.fixture
def sample_data():
    """Create sample OHLCV data."""
    return pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=100, freq="1h"),
            "open": [1.1000] * 100,
            "high": [1.1050] * 100,
            "low": [1.0950] * 100,
            "close": [1.1000] * 100,
            "volume": [1000] * 100,
        }
    )


class TestStrategyManagerInitialization:
    """Test strategy manager initialization."""

    def test_initialization_default_config(self):
        """Test initialization with default config."""
        manager = StrategyManager()

        assert manager.max_concurrent_strategies == 8
        assert manager.conflict_prevention is True
        assert manager.health_check_interval == 300
        assert len(manager.strategies) == 0

    def test_initialization_custom_config(self):
        """Test initialization with custom config."""
        config = {
            "strategy_manager": {
                "max_concurrent_strategies": 5,
                "conflict_prevention": False,
                "health_check_interval": 600,
            }
        }
        manager = StrategyManager(config)

        assert manager.max_concurrent_strategies == 5
        assert manager.conflict_prevention is False
        assert manager.health_check_interval == 600


class TestStrategyRegistration:
    """Test strategy registration."""

    def test_register_strategy(self, strategy_manager):
        """Test registering a strategy."""
        strategy = MockStrategy("foundation")
        strategy_manager.register_strategy("foundation", strategy)

        assert strategy_manager.is_strategy_registered("foundation")
        assert strategy_manager.get_strategy_count() == 1
        assert "foundation" in strategy_manager.get_active_strategies()

    def test_register_multiple_strategies(self, strategy_manager):
        """Test registering multiple strategies."""
        foundation = MockStrategy("foundation")
        trendline = MockStrategy("trendline")

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("trendline", trendline)

        assert strategy_manager.get_strategy_count() == 2
        assert strategy_manager.is_strategy_registered("foundation")
        assert strategy_manager.is_strategy_registered("trendline")

    def test_register_duplicate_strategy(self, strategy_manager):
        """Test that duplicate registration raises error."""
        strategy = MockStrategy("foundation")
        strategy_manager.register_strategy("foundation", strategy)

        with pytest.raises(ValueError, match="already registered"):
            strategy_manager.register_strategy("foundation", strategy)

    def test_register_exceeds_max_strategies(self):
        """Test that exceeding max strategies raises error."""
        config = {"strategy_manager": {"max_concurrent_strategies": 2}}
        manager = StrategyManager(config)

        manager.register_strategy("strategy1", MockStrategy("strategy1"))
        manager.register_strategy("strategy2", MockStrategy("strategy2"))

        with pytest.raises(ValueError, match="Maximum number of strategies"):
            manager.register_strategy("strategy3", MockStrategy("strategy3"))

    def test_unregister_strategy(self, strategy_manager):
        """Test unregistering a strategy."""
        strategy = MockStrategy("foundation")
        strategy_manager.register_strategy("foundation", strategy)

        assert strategy_manager.is_strategy_registered("foundation")

        strategy_manager.unregister_strategy("foundation")

        assert not strategy_manager.is_strategy_registered("foundation")
        assert strategy_manager.get_strategy_count() == 0

    def test_unregister_nonexistent_strategy(self, strategy_manager):
        """Test that unregistering nonexistent strategy raises error."""
        with pytest.raises(ValueError, match="not found"):
            strategy_manager.unregister_strategy("nonexistent")


class TestSymbolAnalysis:
    """Test symbol analysis with strategies."""

    @pytest.mark.asyncio
    async def test_analyze_symbol_with_one_strategy(self, strategy_manager, sample_data):
        """Test analyzing symbol with one strategy."""
        strategy = MockStrategy("foundation")
        strategy_manager.register_strategy("foundation", strategy)

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        assert len(results) == 1
        assert results[0].strategy_name == "foundation"
        assert results[0].symbol == "EURUSD"
        assert results[0].score == 75.0
        assert strategy.call_count == 1

    @pytest.mark.asyncio
    async def test_analyze_symbol_with_multiple_strategies(self, strategy_manager, sample_data):
        """Test analyzing symbol with multiple strategies."""
        foundation = MockStrategy("foundation")
        trendline = MockStrategy("trendline")

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("trendline", trendline)

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        assert len(results) == 2
        assert foundation.call_count == 1
        assert trendline.call_count == 1

        strategy_names = [r.strategy_name for r in results]
        assert "foundation" in strategy_names
        assert "trendline" in strategy_names

    @pytest.mark.asyncio
    async def test_analyze_symbol_no_strategies(self, strategy_manager, sample_data):
        """Test analyzing symbol with no registered strategies."""
        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_analyze_symbol_strategy_returns_no_signal(self, strategy_manager, sample_data):
        """Test analyzing when strategy returns no signal."""
        strategy = MockStrategy("foundation", returns_signal=False)
        strategy_manager.register_strategy("foundation", strategy)

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        assert len(results) == 0
        assert strategy.call_count == 1

    @pytest.mark.asyncio
    async def test_analyze_symbol_strategy_fails(self, strategy_manager, sample_data):
        """Test analyzing when strategy fails."""
        failing_strategy = MockStrategy("foundation", should_fail=True)
        strategy_manager.register_strategy("foundation", failing_strategy)

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        assert len(results) == 0
        assert strategy_manager.strategy_health["foundation"] is False

    @pytest.mark.asyncio
    async def test_analyze_symbol_concurrent_execution(self, strategy_manager, sample_data):
        """Test that multiple strategies execute concurrently."""
        # Register multiple strategies
        for i in range(5):
            strategy = MockStrategy(f"strategy_{i}")
            strategy_manager.register_strategy(f"strategy_{i}", strategy)

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        assert len(results) == 5
        # All strategies should have been called once
        for name in strategy_manager.strategies:
            assert strategy_manager.strategies[name].call_count == 1


class TestStrategyHealth:
    """Test strategy health monitoring."""

    def test_initial_health_status(self, strategy_manager):
        """Test that newly registered strategies are healthy."""
        strategy = MockStrategy("foundation")
        strategy_manager.register_strategy("foundation", strategy)

        assert strategy_manager.strategy_health["foundation"] is True
        assert "foundation" in strategy_manager.get_active_strategies()

    @pytest.mark.asyncio
    async def test_health_status_after_failure(self, strategy_manager, sample_data):
        """Test that failed strategy is marked unhealthy."""
        failing_strategy = MockStrategy("foundation", should_fail=True)
        strategy_manager.register_strategy("foundation", failing_strategy)

        await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        assert strategy_manager.strategy_health["foundation"] is False
        assert "foundation" not in strategy_manager.get_active_strategies()

    @pytest.mark.asyncio
    async def test_health_check(self, strategy_manager):
        """Test health check method."""
        foundation = MockStrategy("foundation")
        trendline = MockStrategy("trendline", should_fail=True)

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("trendline", trendline)

        # Manually set trendline as unhealthy
        strategy_manager.strategy_health["trendline"] = False

        health_status = await strategy_manager.health_check()

        assert health_status["foundation"] is True
        assert health_status["trendline"] is False

    def test_reset_strategy_health(self, strategy_manager):
        """Test resetting strategy health."""
        strategy = MockStrategy("foundation")
        strategy_manager.register_strategy("foundation", strategy)

        # Mark as unhealthy
        strategy_manager.strategy_health["foundation"] = False
        assert "foundation" not in strategy_manager.get_active_strategies()

        # Reset health
        strategy_manager.reset_strategy_health("foundation")
        assert strategy_manager.strategy_health["foundation"] is True
        assert "foundation" in strategy_manager.get_active_strategies()

    def test_reset_nonexistent_strategy_health(self, strategy_manager):
        """Test that resetting nonexistent strategy raises error."""
        with pytest.raises(ValueError, match="not found"):
            strategy_manager.reset_strategy_health("nonexistent")

    @pytest.mark.asyncio
    async def test_unhealthy_strategy_skipped(self, strategy_manager, sample_data):
        """Test that unhealthy strategies are skipped during analysis."""
        foundation = MockStrategy("foundation")
        trendline = MockStrategy("trendline")

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("trendline", trendline)

        # Mark trendline as unhealthy
        strategy_manager.strategy_health["trendline"] = False

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        assert len(results) == 1
        assert results[0].strategy_name == "foundation"
        assert foundation.call_count == 1
        assert trendline.call_count == 0  # Should not be called


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_active_strategies(self, strategy_manager):
        """Test getting active strategies."""
        foundation = MockStrategy("foundation")
        trendline = MockStrategy("trendline")

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("trendline", trendline)

        active = strategy_manager.get_active_strategies()
        assert len(active) == 2
        assert "foundation" in active
        assert "trendline" in active

    def test_get_active_strategies_with_unhealthy(self, strategy_manager):
        """Test getting active strategies excludes unhealthy ones."""
        foundation = MockStrategy("foundation")
        trendline = MockStrategy("trendline")

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("trendline", trendline)

        # Mark trendline as unhealthy
        strategy_manager.strategy_health["trendline"] = False

        active = strategy_manager.get_active_strategies()
        assert len(active) == 1
        assert "foundation" in active
        assert "trendline" not in active

    def test_get_strategy_count(self, strategy_manager):
        """Test getting strategy count."""
        assert strategy_manager.get_strategy_count() == 0

        strategy_manager.register_strategy("foundation", MockStrategy("foundation"))
        assert strategy_manager.get_strategy_count() == 1

        strategy_manager.register_strategy("trendline", MockStrategy("trendline"))
        assert strategy_manager.get_strategy_count() == 2

    def test_is_strategy_registered(self, strategy_manager):
        """Test checking if strategy is registered."""
        assert not strategy_manager.is_strategy_registered("foundation")

        strategy_manager.register_strategy("foundation", MockStrategy("foundation"))
        assert strategy_manager.is_strategy_registered("foundation")

    def test_string_representation(self, strategy_manager):
        """Test string representation."""
        strategy_manager.register_strategy("foundation", MockStrategy("foundation"))
        strategy_manager.register_strategy("trendline", MockStrategy("trendline"))

        str_repr = str(strategy_manager)
        assert "2/2" in str_repr

        # Mark one as unhealthy
        strategy_manager.strategy_health["trendline"] = False
        str_repr = str(strategy_manager)
        assert "1/2" in str_repr
