"""
Signal Aggregator - Aggregates and filters trading signals.

Combines signals from multiple strategies with confluence scoring.
"""

import uuid
from typing import Any

from trading_bot.strategies.models import (
    SignalDirection,
    SignalStatus,
    StrategyResult,
    TradingSignal,
)
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class SignalAggregator:
    """
    Aggregates signals from multiple strategies.

    Responsibilities:
    - Aggregate signals from multiple strategies
    - Calculate weighted confluence scores
    - Filter signals by quality threshold
    - Resolve conflicting signals
    - Apply validation rules
    """

    def __init__(self, config: dict[str, Any] = None):
        """
        Initialize signal aggregator.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Load confluence weights from config
        self.confluence_weights = self.config.get("confluence_weights", {})
        if not self.confluence_weights:
            # Default weights (Phase 5: Enhanced Architecture)
            self.confluence_weights = {
                "foundation": 0.30,      # Foundation (S&D Zones)
                "trendline": 0.20,       # Trendline Confluence
                "price_action": 0.15,    # Price Action
                "fibonacci": 0.12,       # Fibonacci
                "breakout_retest": 0.12, # Breakout/Retest
                "rsi": 0.10,             # RSI Analysis
                "structure": 0.08,       # Market Structure
                "ma": 0.08,              # Moving Average
                "market_structure": 0.08, # Alias for structure
                "volume_profile": 0.05,
                "multi_timeframe": 0.05,
            }

        # Normalize weights to sum to 1.0
        total_weight = sum(self.confluence_weights.values())
        if total_weight > 0:
            self.confluence_weights = {
                k: v / total_weight for k, v in self.confluence_weights.items()
            }

        # Signal quality thresholds
        self.min_confluence_score = (
            self.config.get("signal_generation", {})
            .get("quality_thresholds", {})
            .get("min_confluence_score", 65.0)
        )
        self.max_signals_per_symbol = (
            self.config.get("signal_generation", {})
            .get("quality_thresholds", {})
            .get("max_signals_per_symbol", 1)
        )

        # Risk/reward requirements
        self.min_risk_reward_ratio = (
            self.config.get("signal_generation", {})
            .get("risk_reward", {})
            .get("min_risk_reward_ratio", 2.0)
        )

        # Conflict resolution strategy
        self.conflict_resolution = self.config.get("signal_aggregator", {}).get(
            "conflict_resolution", "highest_score"
        )

        logger.info(
            f"SignalAggregator initialized (min confluence: {self.min_confluence_score:.1f}%, "
            f"min R:R: {self.min_risk_reward_ratio:.1f})"
        )

    async def aggregate_signals(
        self, strategy_results: list[StrategyResult]
    ) -> list[TradingSignal]:
        """
        Aggregate signals from multiple strategies.

        Args:
            strategy_results: Results from all strategies

        Returns:
            List of aggregated TradingSignal objects
        """
        if not strategy_results:
            logger.debug("No strategy results to aggregate")
            return []

        logger.debug(f"Aggregating {len(strategy_results)} strategy results")

        # Group results by symbol
        results_by_symbol = self._group_by_symbol(strategy_results)

        # Aggregate signals for each symbol
        all_signals = []
        for symbol, results in results_by_symbol.items():
            signals = await self._aggregate_symbol_signals(symbol, results)
            all_signals.extend(signals)

        logger.info(f"Aggregated {len(strategy_results)} results into {len(all_signals)} signals")

        return all_signals

    def _group_by_symbol(self, results: list[StrategyResult]) -> dict[str, list[StrategyResult]]:
        """Group strategy results by symbol."""
        grouped: dict[str, list[StrategyResult]] = {}
        for result in results:
            if result.symbol not in grouped:
                grouped[result.symbol] = []
            grouped[result.symbol].append(result)
        return grouped

    async def _aggregate_symbol_signals(
        self, symbol: str, results: list[StrategyResult]
    ) -> list[TradingSignal]:
        """
        Aggregate signals for a single symbol.

        Args:
            symbol: Trading symbol
            results: Strategy results for this symbol

        Returns:
            List of TradingSignal for this symbol
        """
        # Filter results that have signals
        signal_results = [r for r in results if r.has_signal]

        if not signal_results:
            logger.debug(f"{symbol}: No signals from strategies")
            return []

        logger.debug(
            f"{symbol}: Processing {len(signal_results)} signals from {len(results)} results"
        )

        # Group by direction (BUY/SELL)
        buy_results = [r for r in signal_results if r.direction == SignalDirection.BUY]
        sell_results = [r for r in signal_results if r.direction == SignalDirection.SELL]

        signals = []

        # Create signal for BUY direction if any
        if buy_results:
            buy_signal = await self._create_signal_from_results(
                symbol, SignalDirection.BUY, buy_results
            )
            if buy_signal:
                signals.append(buy_signal)

        # Create signal for SELL direction if any
        if sell_results:
            sell_signal = await self._create_signal_from_results(
                symbol, SignalDirection.SELL, sell_results
            )
            if sell_signal:
                signals.append(sell_signal)

        # Filter by quality
        signals = self.filter_by_quality(signals)

        # Apply conflict resolution
        signals = self.resolve_conflicts(signals)

        # Limit signals per symbol
        signals = signals[: self.max_signals_per_symbol]

        logger.debug(f"{symbol}: Generated {len(signals)} final signals")
        return signals

    async def _create_signal_from_results(
        self, symbol: str, direction: SignalDirection, results: list[StrategyResult]
    ) -> TradingSignal | None:
        """
        Create a TradingSignal from strategy results.

        Args:
            symbol: Trading symbol
            direction: Signal direction
            results: Strategy results for this direction

        Returns:
            TradingSignal or None if validation fails
        """
        # Calculate confluence score
        confluence_score = self.calculate_confluence_score(results)

        # Calculate weighted average for prices
        entry_price = self._weighted_average([r.entry_price for r in results if r.entry_price])
        stop_loss = self._weighted_average([r.stop_loss for r in results if r.stop_loss])
        take_profit = self._weighted_average([r.take_profit for r in results if r.take_profit])

        # If any critical price is missing, use the first result's prices
        if entry_price is None or stop_loss is None:
            logger.warning(f"{symbol}: Missing critical prices, using first result")
            entry_price = results[0].entry_price
            stop_loss = results[0].stop_loss
            take_profit = results[0].take_profit or self._calculate_default_tp(
                direction, entry_price, stop_loss
            )

        # Calculate risk/reward ratio
        if direction == SignalDirection.BUY:
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # SELL
            risk = stop_loss - entry_price
            reward = entry_price - take_profit

        if risk <= 0:
            logger.warning(f"{symbol}: Invalid risk ({risk:.5f}), skipping signal")
            return None

        risk_reward_ratio = reward / risk

        # Validate risk/reward ratio
        if risk_reward_ratio < self.min_risk_reward_ratio:
            logger.debug(
                f"{symbol}: Risk/reward too low ({risk_reward_ratio:.2f} < "
                f"{self.min_risk_reward_ratio:.2f}), skipping"
            )
            return None

        # Collect strategy scores
        strategy_scores = {r.strategy_name: r.score for r in results}

        # Create signal
        try:
            signal = TradingSignal(
                signal_id=self._generate_signal_id(),
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confluence_score=confluence_score,
                risk_reward_ratio=risk_reward_ratio,
                strategy_scores=strategy_scores,
                timeframe=results[0].timeframe,
                status=SignalStatus.PENDING,
                metadata={"num_strategies": len(results)},
            )

            logger.debug(
                f"Created signal: {signal.direction.value} {signal.symbol} "
                f"(confluence: {signal.confluence_score:.1f}%, R:R: {signal.risk_reward_ratio:.2f})"
            )

            return signal

        except ValueError as e:
            logger.error(f"Failed to create signal for {symbol}: {e}")
            return None

    def calculate_confluence_score(self, results: list[StrategyResult]) -> float:
        """
        Calculate weighted confluence score.

        Args:
            results: Strategy results

        Returns:
            Weighted confluence score (0-100)
        """
        if not results:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        for result in results:
            weight = self.confluence_weights.get(result.strategy_name, 0.0)
            total_score += result.score * weight
            total_weight += weight

        if total_weight == 0:
            # If no configured weights, use simple average
            return sum(r.score for r in results) / len(results)

        return total_score / total_weight if total_weight > 0 else 0.0

    def filter_by_quality(self, signals: list[TradingSignal]) -> list[TradingSignal]:
        """
        Filter signals by quality threshold.

        Args:
            signals: List of trading signals

        Returns:
            Filtered signals that meet quality requirements
        """
        filtered = [
            signal
            for signal in signals
            if signal.confluence_score >= self.min_confluence_score
            and signal.risk_reward_ratio >= self.min_risk_reward_ratio
        ]

        if len(filtered) < len(signals):
            logger.debug(f"Filtered {len(signals) - len(filtered)} signals below quality threshold")

        return filtered

    def resolve_conflicts(self, signals: list[TradingSignal]) -> list[TradingSignal]:
        """
        Resolve conflicting signals (e.g., both BUY and SELL for same symbol).

        Args:
            signals: List of trading signals

        Returns:
            Signals with conflicts resolved
        """
        if len(signals) <= 1:
            return signals

        # Group by symbol
        signals_by_symbol: dict[str, list[TradingSignal]] = {}
        for signal in signals:
            if signal.symbol not in signals_by_symbol:
                signals_by_symbol[signal.symbol] = []
            signals_by_symbol[signal.symbol].append(signal)

        resolved = []
        for symbol, symbol_signals in signals_by_symbol.items():
            # Check for conflicting directions
            directions = {s.direction for s in symbol_signals}
            if len(directions) > 1:
                logger.warning(
                    f"{symbol}: Conflicting signals detected, applying resolution strategy"
                )

                if self.conflict_resolution == "highest_score":
                    # Keep signal with highest confluence score
                    best_signal = max(symbol_signals, key=lambda s: s.confluence_score)
                    resolved.append(best_signal)
                else:  # "first_signal"
                    resolved.append(symbol_signals[0])
            else:
                # No conflict, keep all signals for this symbol
                resolved.extend(symbol_signals)

        return resolved

    def _weighted_average(self, values: list[float | None]) -> float | None:
        """Calculate weighted average of values."""
        valid_values = [v for v in values if v is not None]
        if not valid_values:
            return None
        return sum(valid_values) / len(valid_values)

    def _calculate_default_tp(
        self, direction: SignalDirection, entry: float, stop_loss: float
    ) -> float:
        """Calculate default take profit based on risk/reward ratio."""
        risk = abs(entry - stop_loss)
        reward = risk * self.min_risk_reward_ratio

        if direction == SignalDirection.BUY:
            return entry + reward
        else:  # SELL
            return entry - reward

    def _generate_signal_id(self) -> str:
        """Generate unique signal ID."""
        return f"sig_{uuid.uuid4().hex[:12]}"

    def __str__(self) -> str:
        """String representation."""
        return (
            f"SignalAggregator(min_confluence: {self.min_confluence_score:.1f}%, "
            f"min_rr: {self.min_risk_reward_ratio:.1f})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
