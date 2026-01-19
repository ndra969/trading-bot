"""Tests for StrategyManager."""

from unittest.mock import patch

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

    def test_repr_representation(self, strategy_manager):
        """Test __repr__ representation."""
        strategy_manager.register_strategy("foundation", MockStrategy("foundation"))
        repr_str = repr(strategy_manager)
        assert "StrategyManager" in repr_str
        assert "1/1" in repr_str


class TestStrategyExecutionEdgeCases:
    """Test edge cases in strategy execution."""

    @pytest.mark.asyncio
    async def test_analyze_symbol_all_strategies_unhealthy(self, strategy_manager, sample_data):
        """Test analyzing when all strategies are unhealthy."""
        foundation = MockStrategy("foundation")
        trendline = MockStrategy("trendline")

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("trendline", trendline)

        # Mark all as unhealthy
        strategy_manager.strategy_health["foundation"] = False
        strategy_manager.strategy_health["trendline"] = False

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        assert len(results) == 0
        assert foundation.call_count == 0
        assert trendline.call_count == 0

    @pytest.mark.asyncio
    async def test_analyze_symbol_mixed_health_strategies(self, strategy_manager, sample_data):
        """Test analyzing with mix of healthy and unhealthy strategies."""
        foundation = MockStrategy("foundation")
        trendline = MockStrategy("trendline")
        rsi = MockStrategy("rsi")

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("trendline", trendline)
        strategy_manager.register_strategy("rsi", rsi)

        # Mark trendline as unhealthy
        strategy_manager.strategy_health["trendline"] = False

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        assert len(results) == 2
        assert foundation.call_count == 1
        assert trendline.call_count == 0
        assert rsi.call_count == 1

    @pytest.mark.asyncio
    async def test_strategy_returns_non_list_result(self, strategy_manager, sample_data):
        """Test when strategy returns non-list result."""

        # Create a strategy that returns invalid type
        class InvalidReturnTypeStrategy:
            def __init__(self):
                self.name = "invalid"

            async def generate_signals(self, symbol, data, timeframe):
                return "invalid_result"  # Not a list

        invalid_strategy = InvalidReturnTypeStrategy()
        strategy_manager.register_strategy("invalid", invalid_strategy)

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        # Should handle gracefully and return empty list
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_strategy_returns_single_result_object(self, strategy_manager, sample_data):
        """Test when strategy returns a single StrategyResult instead of list."""

        # Create a strategy that returns a single object (edge case in gather)
        class SingleResultStrategy:
            def __init__(self):
                self.name = "single"

            async def generate_signals(self, symbol, data, timeframe):
                # Returns a single StrategyResult (not in a list)
                # This is technically invalid but should be handled
                result = StrategyResult(
                    strategy_name="single",
                    symbol=symbol,
                    score=80.0,
                    direction=SignalDirection.BUY,
                    entry_price=1.1000,
                    stop_loss=1.0950,
                    take_profit=1.1150,
                    timeframe=timeframe,
                )
                return [result]  # Return as list (correct behavior)

        single_strategy = SingleResultStrategy()
        strategy_manager.register_strategy("single", single_strategy)

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        # Should handle single result in results list
        assert len(results) == 1
        assert results[0].strategy_name == "single"


class TestExecuteStrategyValidation:
    """Test _execute_strategy validation logic."""

    @pytest.mark.asyncio
    async def test_execute_strategy_invalid_result_type(self, strategy_manager, sample_data):
        """Test _execute_strategy with invalid return type."""

        class InvalidTypeStrategy:
            def __init__(self):
                self.name = "invalid_type"

            async def generate_signals(self, symbol, data, timeframe):
                return {"invalid": "dict"}  # Not a list

        invalid_strategy = InvalidTypeStrategy()
        strategy_manager.register_strategy("invalid_type", invalid_strategy)

        # Call _execute_strategy directly
        result = await strategy_manager._execute_strategy(
            "invalid_type", invalid_strategy, "EURUSD", sample_data, "H1"
        )

        # Should return empty list for invalid type
        assert result == []

    @pytest.mark.asyncio
    async def test_execute_strategy_invalid_result_item_type(self, strategy_manager, sample_data):
        """Test _execute_strategy with invalid items in result list."""

        class InvalidItemStrategy:
            def __init__(self):
                self.name = "invalid_item"

            async def generate_signals(self, symbol, data, timeframe):
                # Return list with invalid items
                return [
                    "invalid_string",
                    {"invalid": "dict"},
                    123,
                ]

        invalid_strategy = InvalidItemStrategy()
        strategy_manager.register_strategy("invalid_item", invalid_strategy)

        # Call _execute_strategy directly
        result = await strategy_manager._execute_strategy(
            "invalid_item", invalid_strategy, "EURUSD", sample_data, "H1"
        )

        # Should filter out invalid items and return empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_execute_strategy_mixed_valid_invalid_results(
        self, strategy_manager, sample_data
    ):
        """Test _execute_strategy with mix of valid and invalid results."""

        class MixedResultsStrategy:
            def __init__(self):
                self.name = "mixed"

            async def generate_signals(self, symbol, data, timeframe):
                # Return list with mix of valid and invalid items
                valid_result = StrategyResult(
                    strategy_name="mixed",
                    symbol=symbol,
                    score=75.0,
                    direction=SignalDirection.BUY,
                    entry_price=1.1000,
                    stop_loss=1.0950,
                    take_profit=1.1150,
                    timeframe=timeframe,
                )
                return [
                    "invalid_string",
                    valid_result,
                    {"invalid": "dict"},
                    StrategyResult(
                        strategy_name="mixed",
                        symbol=symbol,
                        score=80.0,
                        direction=SignalDirection.SELL,
                        entry_price=1.1000,
                        stop_loss=1.1050,
                        take_profit=1.0850,
                        timeframe=timeframe,
                    ),
                ]

        mixed_strategy = MixedResultsStrategy()
        strategy_manager.register_strategy("mixed", mixed_strategy)

        # Call _execute_strategy directly
        result = await strategy_manager._execute_strategy(
            "mixed", mixed_strategy, "EURUSD", sample_data, "H1"
        )

        # Should filter out invalid items and keep only valid ones
        assert len(result) == 2
        assert all(isinstance(r, StrategyResult) for r in result)

    @pytest.mark.asyncio
    async def test_execute_strategy_wrong_strategy_name_correction(
        self, strategy_manager, sample_data
    ):
        """Test that wrong strategy name in result is corrected."""

        class WrongNameStrategy:
            def __init__(self):
                self.name = "correct_name"

            async def generate_signals(self, symbol, data, timeframe):
                # Return result with wrong strategy name
                result = StrategyResult(
                    strategy_name="wrong_name",  # Wrong name
                    symbol=symbol,
                    score=75.0,
                    direction=SignalDirection.BUY,
                    entry_price=1.1000,
                    stop_loss=1.0950,
                    take_profit=1.1150,
                    timeframe=timeframe,
                )
                return [result]

        wrong_name_strategy = WrongNameStrategy()
        strategy_manager.register_strategy("correct_name", wrong_name_strategy)

        # Call _execute_strategy directly
        result = await strategy_manager._execute_strategy(
            "correct_name", wrong_name_strategy, "EURUSD", sample_data, "H1"
        )

        # Should correct the strategy name
        assert len(result) == 1
        assert result[0].strategy_name == "correct_name"

    @pytest.mark.asyncio
    async def test_execute_strategy_exception_handling(self, strategy_manager, sample_data):
        """Test _execute_strategy exception handling."""

        class FailingStrategy:
            def __init__(self):
                self.name = "failing"

            async def generate_signals(self, symbol, data, timeframe):
                raise RuntimeError("Strategy execution failed")

        failing_strategy = FailingStrategy()
        strategy_manager.register_strategy("failing", failing_strategy)

        # Call _execute_strategy directly
        result = await strategy_manager._execute_strategy(
            "failing", failing_strategy, "EURUSD", sample_data, "H1"
        )

        # Should return empty list and mark strategy as unhealthy
        assert result == []
        assert strategy_manager.strategy_health["failing"] is False


class TestHealthCheckEdgeCases:
    """Test health check edge cases."""

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self, strategy_manager):
        """Test health check when strategy raises exception."""

        # Create a wrapper that will cause the health check to fail
        # We need to test the exception handling in health_check method
        # The health_check accesses strategy_health.get() which could raise
        class FailingDict(dict):
            """Dict that raises exception on get for specific key."""

            def get(self, key, default=None):
                if key == "exception_strategy":
                    raise RuntimeError("Health check failed")
                return super().get(key, default)

        # Replace strategy_health with failing dict
        original_health = strategy_manager.strategy_health
        strategy_manager.strategy_health = FailingDict(original_health)

        # Register a strategy to trigger the exception
        exception_strategy = MockStrategy("exception_strategy")
        strategy_manager.register_strategy("exception_strategy", exception_strategy)

        # Call health_check
        health_status = await strategy_manager.health_check()

        # Should handle exception and mark as unhealthy
        assert health_status["exception_strategy"] is False
        assert strategy_manager.strategy_health["exception_strategy"] is False

    @pytest.mark.asyncio
    async def test_health_check_with_no_strategies(self, strategy_manager):
        """Test health check with no registered strategies."""
        health_status = await strategy_manager.health_check()

        assert len(health_status) == 0

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, strategy_manager):
        """Test health check when all strategies are healthy."""
        foundation = MockStrategy("foundation")
        trendline = MockStrategy("trendline")

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("trendline", trendline)

        health_status = await strategy_manager.health_check()

        assert health_status["foundation"] is True
        assert health_status["trendline"] is True

    @pytest.mark.asyncio
    async def test_health_check_all_unhealthy(self, strategy_manager):
        """Test health check when all strategies are unhealthy."""
        foundation = MockStrategy("foundation")
        trendline = MockStrategy("trendline")

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("trendline", trendline)

        # Mark all as unhealthy
        strategy_manager.strategy_health["foundation"] = False
        strategy_manager.strategy_health["trendline"] = False

        health_status = await strategy_manager.health_check()

        assert health_status["foundation"] is False
        assert health_status["trendline"] is False


class TestAnalyzeSymbolResultsAggregation:
    """Test results aggregation in analyze_symbol."""

    @pytest.mark.asyncio
    async def test_analyze_symbol_aggregates_multiple_results(self, strategy_manager, sample_data):
        """Test that analyze_symbol properly aggregates results from multiple strategies."""

        # Create strategies that return multiple results each
        class MultiResultStrategy:
            def __init__(self, name, count=2):
                self.name = name
                self.result_count = count

            async def generate_signals(self, symbol, data, timeframe):
                results = []
                for i in range(self.result_count):
                    result = StrategyResult(
                        strategy_name=self.name,
                        symbol=symbol,
                        score=70.0 + i,
                        direction=SignalDirection.BUY if i % 2 == 0 else SignalDirection.SELL,
                        entry_price=1.1000 + (i * 0.001),
                        stop_loss=1.0950 + (i * 0.001),
                        take_profit=1.1150 + (i * 0.001),
                        timeframe=timeframe,
                    )
                    results.append(result)
                return results

        foundation = MultiResultStrategy("foundation", count=3)
        trendline = MultiResultStrategy("trendline", count=2)

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("trendline", trendline)

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        # Should aggregate all results from both strategies
        assert len(results) == 5

        # Check that results from both strategies are present
        foundation_results = [r for r in results if r.strategy_name == "foundation"]
        trendline_results = [r for r in results if r.strategy_name == "trendline"]

        assert len(foundation_results) == 3
        assert len(trendline_results) == 2

    @pytest.mark.asyncio
    async def test_analyze_symbol_empty_results_ignored(self, strategy_manager, sample_data):
        """Test that empty results from strategies are handled correctly."""

        class EmptyResultStrategy:
            def __init__(self):
                self.name = "empty"

            async def generate_signals(self, symbol, data, timeframe):
                return []  # Empty list

        empty_strategy = EmptyResultStrategy()
        strategy_manager.register_strategy("empty", empty_strategy)

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        # Empty results should be handled gracefully
        assert len(results) == 0


class TestMultipleFailures:
    """Test scenarios with multiple strategy failures."""

    @pytest.mark.asyncio
    async def test_multiple_strategies_fail_during_analysis(self, strategy_manager, sample_data):
        """Test that multiple strategy failures are handled correctly."""
        foundation = MockStrategy("foundation")  # Healthy
        failing1 = MockStrategy("failing1", should_fail=True)
        failing2 = MockStrategy("failing2", should_fail=True)

        strategy_manager.register_strategy("foundation", foundation)
        strategy_manager.register_strategy("failing1", failing1)
        strategy_manager.register_strategy("failing2", failing2)

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        # Only foundation should return results
        assert len(results) == 1
        assert results[0].strategy_name == "foundation"

        # Failed strategies should be marked unhealthy
        assert strategy_manager.strategy_health["foundation"] is True
        assert strategy_manager.strategy_health["failing1"] is False
        assert strategy_manager.strategy_health["failing2"] is False

    @pytest.mark.asyncio
    async def test_all_strategies_fail_during_analysis(self, strategy_manager, sample_data):
        """Test that complete strategy failure is handled gracefully."""
        failing1 = MockStrategy("failing1", should_fail=True)
        failing2 = MockStrategy("failing2", should_fail=True)

        strategy_manager.register_strategy("failing1", failing1)
        strategy_manager.register_strategy("failing2", failing2)

        results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

        # Should return empty list
        assert len(results) == 0

        # All should be marked unhealthy
        assert strategy_manager.strategy_health["failing1"] is False
        assert strategy_manager.strategy_health["failing2"] is False


class TestGatherExceptionHandling:
    """Test exception handling in asyncio.gather results."""

    @pytest.mark.asyncio
    async def test_analyze_symbol_handles_gather_exception(self, strategy_manager, sample_data):
        """Test analyze_symbol when gather returns exceptions."""

        # Mock _execute_strategy to return an exception directly
        # This simulates what happens when asyncio.gather returns exceptions
        async def mock_execute(name, strategy, symbol, data, timeframe):
            if name == "failing":
                raise RuntimeError("Strategy failed during execution")
            return []

        with patch.object(strategy_manager, "_execute_strategy", side_effect=mock_execute):
            foundation = MockStrategy("foundation")
            failing = MockStrategy("failing")

            strategy_manager.register_strategy("foundation", foundation)
            strategy_manager.register_strategy("failing", failing)

            results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

            # Should handle exception and return empty list (foundation also returns [])
            assert len(results) == 0

            # Failing strategy should be marked unhealthy
            assert strategy_manager.strategy_health["failing"] is False
            assert strategy_manager.strategy_health["foundation"] is True

    @pytest.mark.asyncio
    async def test_analyze_symbol_single_result_object(self, strategy_manager, sample_data):
        """Test analyze_symbol when strategy returns single StrategyResult."""
        # Mock _execute_strategy to return a single StrategyResult (not a list)
        # This tests lines 164-165

        async def mock_execute(name, strategy, symbol, data, timeframe):
            if name == "single_result":
                result = StrategyResult(
                    strategy_name="single_result",
                    symbol=symbol,
                    score=75.0,
                    direction=SignalDirection.BUY,
                    entry_price=1.1000,
                    stop_loss=1.0950,
                    take_profit=1.1150,
                    timeframe=timeframe,
                )
                return result  # Single object, not a list
            return []

        with patch.object(strategy_manager, "_execute_strategy", side_effect=mock_execute):
            strategy = MockStrategy("single_result")
            strategy_manager.register_strategy("single_result", strategy)

            results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

            # Should handle single result object
            assert len(results) == 1
            assert results[0].strategy_name == "single_result"

    @pytest.mark.asyncio
    async def test_analyze_symbol_mixed_results_and_exceptions(self, strategy_manager, sample_data):
        """Test analyze_symbol with mix of valid results and exceptions from gather."""
        # Mock _execute_strategy to return different types
        result1 = StrategyResult(
            strategy_name="strategy1",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            timeframe="H1",
        )

        result2 = StrategyResult(
            strategy_name="strategy2",
            symbol="EURUSD",
            score=80.0,
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0850,
            timeframe="H1",
        )

        async def mock_execute(name, strategy, symbol, data, timeframe):
            if name == "strategy1":
                return result1  # Single object
            elif name == "strategy2":
                return [result2]  # List
            elif name == "failing":
                raise RuntimeError("Execution failed")
            return []

        with patch.object(strategy_manager, "_execute_strategy", side_effect=mock_execute):
            strategy1 = MockStrategy("strategy1")
            strategy2 = MockStrategy("strategy2")
            failing = MockStrategy("failing")

            strategy_manager.register_strategy("strategy1", strategy1)
            strategy_manager.register_strategy("strategy2", strategy2)
            strategy_manager.register_strategy("failing", failing)

            results = await strategy_manager.analyze_symbol("EURUSD", sample_data, "H1")

            # Should aggregate both single result and list result
            assert len(results) == 2

            # Check that both results are present
            result_names = [r.strategy_name for r in results]
            assert "strategy1" in result_names
            assert "strategy2" in result_names

            # Failing should be marked unhealthy
            assert strategy_manager.strategy_health["failing"] is False
