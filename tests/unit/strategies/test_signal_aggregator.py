"""Tests for SignalAggregator."""

import pytest

from trading_bot.strategies.models import SignalDirection, StrategyResult
from trading_bot.strategies.signal_aggregator import SignalAggregator


@pytest.fixture
def signal_aggregator():
    """Create a SignalAggregator instance."""
    config = {
        "confluence_weights": {"foundation": 1.0},
        "signal_generation": {
            "quality_thresholds": {
                "min_confluence_score": 65.0,
                "max_signals_per_symbol": 1,
            },
            "risk_reward": {"min_risk_reward_ratio": 2.0},
        },
        "signal_aggregator": {"conflict_resolution": "highest_score"},
    }
    return SignalAggregator(config)


@pytest.fixture
def buy_result():
    """Create a BUY strategy result."""
    return StrategyResult(
        strategy_name="foundation",
        symbol="EURUSD",
        score=75.0,
        direction=SignalDirection.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        timeframe="H1",
    )


@pytest.fixture
def sell_result():
    """Create a SELL strategy result."""
    return StrategyResult(
        strategy_name="foundation",
        symbol="EURUSD",
        score=70.0,
        direction=SignalDirection.SELL,
        entry_price=1.1000,
        stop_loss=1.1050,
        take_profit=1.0850,
        timeframe="H1",
    )


class TestSignalAggregatorInitialization:
    """Test signal aggregator initialization."""

    def test_initialization_default_config(self):
        """Test initialization with default config."""
        aggregator = SignalAggregator()

        assert aggregator.min_confluence_score == 65.0
        assert aggregator.max_signals_per_symbol == 1
        assert aggregator.min_risk_reward_ratio == 2.0
        assert aggregator.conflict_resolution == "highest_score"

    def test_initialization_custom_config(self):
        """Test initialization with custom config."""
        config = {
            "signal_generation": {
                "quality_thresholds": {
                    "min_confluence_score": 70.0,
                    "max_signals_per_symbol": 2,
                },
                "risk_reward": {"min_risk_reward_ratio": 3.0},
            },
            "signal_aggregator": {"conflict_resolution": "first_signal"},
        }
        aggregator = SignalAggregator(config)

        assert aggregator.min_confluence_score == 70.0
        assert aggregator.max_signals_per_symbol == 2
        assert aggregator.min_risk_reward_ratio == 3.0
        assert aggregator.conflict_resolution == "first_signal"

    def test_confluence_weights_normalization(self):
        """Test that confluence weights are normalized to sum to 1.0."""
        config = {
            "confluence_weights": {
                "foundation": 0.5,
                "trendline": 0.3,
                "price_action": 0.2,
            }
        }
        aggregator = SignalAggregator(config)

        total_weight = sum(aggregator.confluence_weights.values())
        assert total_weight == pytest.approx(1.0, abs=0.01)


class TestSignalAggregation:
    """Test signal aggregation."""

    @pytest.mark.asyncio
    async def test_aggregate_empty_results(self, signal_aggregator):
        """Test aggregating empty results."""
        signals = await signal_aggregator.aggregate_signals([])
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_aggregate_single_buy_signal(self, signal_aggregator, buy_result):
        """Test aggregating a single BUY signal."""
        signals = await signal_aggregator.aggregate_signals([buy_result])

        assert len(signals) == 1
        signal = signals[0]
        assert signal.direction == SignalDirection.BUY
        assert signal.symbol == "EURUSD"
        assert signal.entry_price == 1.1000
        assert signal.stop_loss == 1.0950
        assert signal.take_profit == 1.1150
        assert signal.confluence_score == 75.0

    @pytest.mark.asyncio
    async def test_aggregate_single_sell_signal(self, signal_aggregator, sell_result):
        """Test aggregating a single SELL signal."""
        signals = await signal_aggregator.aggregate_signals([sell_result])

        assert len(signals) == 1
        signal = signals[0]
        assert signal.direction == SignalDirection.SELL
        assert signal.symbol == "EURUSD"
        assert signal.entry_price == 1.1000
        assert signal.stop_loss == 1.1050
        assert signal.take_profit == 1.0850

    @pytest.mark.asyncio
    async def test_aggregate_multiple_strategies_same_direction(self, signal_aggregator):
        """Test aggregating multiple strategies with same direction."""
        result1 = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
        )
        result2 = StrategyResult(
            strategy_name="trendline",
            symbol="EURUSD",
            score=80.0,
            direction=SignalDirection.BUY,
            entry_price=1.1005,
            stop_loss=1.0955,
            take_profit=1.1160,
        )

        signals = await signal_aggregator.aggregate_signals([result1, result2])

        assert len(signals) == 1
        signal = signals[0]
        assert signal.direction == SignalDirection.BUY
        # Entry should be weighted average
        assert 1.1000 <= signal.entry_price <= 1.1005

    @pytest.mark.asyncio
    async def test_aggregate_conflicting_signals(self, signal_aggregator):
        """Test aggregating conflicting BUY and SELL signals."""
        buy = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
        )
        sell = StrategyResult(
            strategy_name="trendline",
            symbol="EURUSD",
            score=80.0,
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0850,
        )

        signals = await signal_aggregator.aggregate_signals([buy, sell])

        # Should resolve conflict and keep only one signal (highest score)
        assert len(signals) == 1
        assert signals[0].direction == SignalDirection.SELL  # Higher score

    @pytest.mark.asyncio
    async def test_aggregate_multiple_symbols(self, signal_aggregator):
        """Test aggregating signals for multiple symbols."""
        eurusd = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
        )
        gbpusd = StrategyResult(
            strategy_name="foundation",
            symbol="GBPUSD",
            score=70.0,
            direction=SignalDirection.SELL,
            entry_price=1.2500,
            stop_loss=1.2550,
            take_profit=1.2350,
        )

        signals = await signal_aggregator.aggregate_signals([eurusd, gbpusd])

        assert len(signals) == 2
        symbols = {s.symbol for s in signals}
        assert "EURUSD" in symbols
        assert "GBPUSD" in symbols

    @pytest.mark.asyncio
    async def test_aggregate_no_signal_results(self, signal_aggregator):
        """Test aggregating results without signals."""
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=50.0,
            # No direction, entry, stop_loss - no signal
        )

        signals = await signal_aggregator.aggregate_signals([result])
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_aggregate_missing_critical_prices(self, signal_aggregator):
        """Test aggregating with missing critical prices (line 218-223)."""
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=None,  # Missing
            stop_loss=1.0950,
            take_profit=1.1150,
        )

        signals = await signal_aggregator.aggregate_signals([result])
        # Should handle missing prices gracefully
        assert len(signals) == 0  # Or might return None/empty

    @pytest.mark.asyncio
    async def test_aggregate_invalid_risk(self, signal_aggregator):
        """Test aggregating with invalid risk (risk <= 0) (line 234-235)."""
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.1050,  # Stop loss above entry (invalid for BUY)
            take_profit=1.1150,
        )

        signals = await signal_aggregator.aggregate_signals([result])
        # Should return None or empty list due to invalid risk
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_aggregate_value_error_handling(self, signal_aggregator):
        """Test ValueError exception handling (line 274-276)."""
        # Create a result that might cause ValueError in TradingSignal creation
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
        )

        # Mock TradingSignal to raise ValueError
        from unittest.mock import patch

        with patch("trading_bot.strategies.signal_aggregator.TradingSignal") as mock_signal:
            mock_signal.side_effect = ValueError("Invalid signal data")

            signals = await signal_aggregator.aggregate_signals([result])
            # Should handle ValueError gracefully
            assert len(signals) == 0

    def test_calculate_default_tp_buy(self, signal_aggregator):
        """Test default TP calculation for BUY (line 382-383)."""
        entry = 1.1000
        stop_loss = 1.0950
        tp = signal_aggregator._calculate_default_tp(SignalDirection.BUY, entry, stop_loss)

        risk = abs(entry - stop_loss)  # 0.0050
        expected_reward = risk * signal_aggregator.min_risk_reward_ratio  # 0.0050 * 2.0 = 0.0100
        expected_tp = entry + expected_reward  # 1.1000 + 0.0100 = 1.1100

        assert tp == pytest.approx(expected_tp, abs=0.0001)

    def test_calculate_default_tp_sell(self, signal_aggregator):
        """Test default TP calculation for SELL (line 384-385)."""
        entry = 1.1000
        stop_loss = 1.1050
        tp = signal_aggregator._calculate_default_tp(SignalDirection.SELL, entry, stop_loss)

        risk = abs(entry - stop_loss)  # 0.0050
        expected_reward = risk * signal_aggregator.min_risk_reward_ratio  # 0.0050 * 2.0 = 0.0100
        expected_tp = entry - expected_reward  # 1.1000 - 0.0100 = 1.0900

        assert tp == pytest.approx(expected_tp, abs=0.0001)


class TestConfluenceScoring:
    """Test confluence score calculation."""

    def test_calculate_confluence_single_strategy(self, signal_aggregator):
        """Test confluence score with single strategy."""
        result = StrategyResult(strategy_name="foundation", symbol="EURUSD", score=75.0)

        score = signal_aggregator.calculate_confluence_score([result])
        assert score == 75.0

    def test_calculate_confluence_multiple_strategies(self):
        """Test confluence score with multiple strategies."""
        config = {
            "confluence_weights": {
                "foundation": 0.6,
                "trendline": 0.4,
            }
        }
        aggregator = SignalAggregator(config)

        results = [
            StrategyResult(strategy_name="foundation", symbol="EURUSD", score=80.0),
            StrategyResult(strategy_name="trendline", symbol="EURUSD", score=70.0),
        ]

        score = aggregator.calculate_confluence_score(results)
        # 0.6 * 80 + 0.4 * 70 = 48 + 28 = 76
        assert score == pytest.approx(76.0, abs=0.1)

    def test_calculate_confluence_empty_results(self, signal_aggregator):
        """Test confluence score with empty results."""
        score = signal_aggregator.calculate_confluence_score([])
        assert score == 0.0

    def test_calculate_confluence_unknown_strategy(self, signal_aggregator):
        """Test confluence score with unknown strategy (no weight)."""
        result = StrategyResult(strategy_name="unknown_strategy", symbol="EURUSD", score=75.0)

        # Should fallback to simple average
        score = signal_aggregator.calculate_confluence_score([result])
        assert score == 75.0


class TestQualityFiltering:
    """Test signal quality filtering."""

    def test_filter_by_quality_all_pass(self, signal_aggregator):
        """Test filtering when all signals pass."""
        from trading_bot.strategies.models import TradingSignal

        signals = [
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                confluence_score=75.0,
                risk_reward_ratio=3.0,
            )
        ]

        filtered = signal_aggregator.filter_by_quality(signals)
        assert len(filtered) == 1

    def test_filter_by_quality_low_confluence(self, signal_aggregator):
        """Test filtering signals with low confluence score."""
        from trading_bot.strategies.models import TradingSignal

        signals = [
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                confluence_score=60.0,  # Below 65% threshold
                risk_reward_ratio=3.0,
            )
        ]

        filtered = signal_aggregator.filter_by_quality(signals)
        assert len(filtered) == 0

    def test_filter_by_quality_low_risk_reward(self, signal_aggregator):
        """Test filtering signals with low risk/reward ratio."""
        from trading_bot.strategies.models import TradingSignal

        signals = [
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1075,
                confluence_score=75.0,
                risk_reward_ratio=1.5,  # Below 2.0 threshold
            )
        ]

        filtered = signal_aggregator.filter_by_quality(signals)
        assert len(filtered) == 0

    def test_filter_by_quality_mixed(self, signal_aggregator):
        """Test filtering with mixed quality signals."""
        from trading_bot.strategies.models import TradingSignal

        signals = [
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                confluence_score=75.0,  # Pass
                risk_reward_ratio=3.0,  # Pass
            ),
            TradingSignal(
                signal_id="sig_002",
                symbol="GBPUSD",
                direction=SignalDirection.SELL,
                entry_price=1.2500,
                stop_loss=1.2550,
                take_profit=1.2350,
                confluence_score=60.0,  # Fail
                risk_reward_ratio=3.0,
            ),
        ]

        filtered = signal_aggregator.filter_by_quality(signals)
        assert len(filtered) == 1
        assert filtered[0].symbol == "EURUSD"


class TestConflictResolution:
    """Test signal conflict resolution."""

    def test_resolve_conflicts_no_conflict(self, signal_aggregator):
        """Test when there are no conflicts."""
        from trading_bot.strategies.models import TradingSignal

        signals = [
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                confluence_score=75.0,
                risk_reward_ratio=3.0,
            )
        ]

        resolved = signal_aggregator.resolve_conflicts(signals)
        assert len(resolved) == 1

    def test_resolve_conflicts_highest_score(self, signal_aggregator):
        """Test conflict resolution by highest score."""
        from trading_bot.strategies.models import TradingSignal

        signals = [
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                confluence_score=75.0,
                risk_reward_ratio=3.0,
            ),
            TradingSignal(
                signal_id="sig_002",
                symbol="EURUSD",
                direction=SignalDirection.SELL,
                entry_price=1.1000,
                stop_loss=1.1050,
                take_profit=1.0850,
                confluence_score=80.0,  # Higher score
                risk_reward_ratio=3.0,
            ),
        ]

        resolved = signal_aggregator.resolve_conflicts(signals)
        assert len(resolved) == 1
        assert resolved[0].direction == SignalDirection.SELL

    def test_resolve_conflicts_first_signal(self):
        """Test conflict resolution by first signal."""
        from trading_bot.strategies.models import TradingSignal

        config = {"signal_aggregator": {"conflict_resolution": "first_signal"}}
        aggregator = SignalAggregator(config)

        signals = [
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                confluence_score=75.0,
                risk_reward_ratio=3.0,
            ),
            TradingSignal(
                signal_id="sig_002",
                symbol="EURUSD",
                direction=SignalDirection.SELL,
                entry_price=1.1000,
                stop_loss=1.1050,
                take_profit=1.0850,
                confluence_score=80.0,
                risk_reward_ratio=3.0,
            ),
        ]

        resolved = aggregator.resolve_conflicts(signals)
        assert len(resolved) == 1
        assert resolved[0].direction == SignalDirection.BUY  # First signal

    def test_resolve_conflicts_multiple_symbols(self, signal_aggregator):
        """Test conflict resolution with multiple symbols."""
        from trading_bot.strategies.models import TradingSignal

        signals = [
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                confluence_score=75.0,
                risk_reward_ratio=3.0,
            ),
            TradingSignal(
                signal_id="sig_002",
                symbol="GBPUSD",
                direction=SignalDirection.SELL,
                entry_price=1.2500,
                stop_loss=1.2550,
                take_profit=1.2350,
                confluence_score=70.0,
                risk_reward_ratio=3.0,
            ),
        ]

        resolved = signal_aggregator.resolve_conflicts(signals)
        assert len(resolved) == 2  # Different symbols, no conflict


class TestUtilityMethods:
    """Test utility methods."""

    def test_string_representation(self, signal_aggregator):
        """Test string representation."""
        str_repr = str(signal_aggregator)
        assert "65.0%" in str_repr
        assert "2.0" in str_repr

    def test_generate_signal_id(self, signal_aggregator):
        """Test signal ID generation."""
        id1 = signal_aggregator._generate_signal_id()
        id2 = signal_aggregator._generate_signal_id()

        assert id1.startswith("sig_")
        assert id2.startswith("sig_")
        assert id1 != id2  # Should be unique

    def test_weighted_average(self, signal_aggregator):
        """Test weighted average calculation."""
        values = [1.0, 2.0, 3.0]
        avg = signal_aggregator._weighted_average(values)
        assert avg == 2.0

    def test_weighted_average_with_none(self, signal_aggregator):
        """Test weighted average with None values."""
        values = [1.0, None, 3.0]
        avg = signal_aggregator._weighted_average(values)
        assert avg == 2.0

    def test_weighted_average_all_none(self, signal_aggregator):
        """Test weighted average with all None values."""
        values = [None, None, None]
        avg = signal_aggregator._weighted_average(values)
        assert avg is None
