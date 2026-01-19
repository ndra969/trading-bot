"""
Performance Analyzer - Week 15.5.1

Analyzes trading performance to identify root causes of losses and generate
actionable recommendations for system improvements.

Key features:
- Win rate and risk:reward ratio analysis
- Trailing stop effectiveness evaluation
- Entry/exit quality assessment
- Symbol-specific performance analysis
- Comprehensive performance reporting
"""

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PerformanceMetrics:
    """Overall performance metrics."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    avg_win_pips: float = 0.0
    avg_loss_pips: float = 0.0
    risk_reward_ratio: float = 0.0

    total_pnl_usd: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0

    expectancy: float = 0.0
    sharpe_ratio: float = 0.0

    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0


@dataclass
class TradePerformance:
    """Individual trade performance data."""

    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    profit_pips: float
    profit_usd: float
    status: str  # WIN or LOSS
    close_reason: str
    open_time: datetime
    close_time: datetime
    holding_time_seconds: int | None = None


@dataclass
class TrailingStopAnalysis:
    """Trailing stop effectiveness analysis."""

    total_trailing_closes: int = 0
    trailing_wins: int = 0
    trailing_losses: int = 0
    effectiveness_score: float = 0.0

    premature_exits: list[TradePerformance] = field(default_factory=list)
    recommended_distance_pips: float = 15.0
    recommended_activation_pips: float = 20.0

    avg_win_on_trailing: float = 0.0
    avg_loss_on_trailing: float = 0.0

    patterns: list[str] = field(default_factory=list)


@dataclass
class SymbolAnalysis:
    """Per-symbol performance analysis."""

    symbol: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    loss_rate: float = 0.0

    avg_win_pips: float = 0.0
    avg_loss_pips: float = 0.0
    total_pnl_usd: float = 0.0

    trailing_stop_losses: int = 0
    sl_hit_losses: int = 0


@dataclass
class EntryQualityAnalysis:
    """Entry point quality analysis."""

    quality_score: float = 0.0
    immediate_drawdown_count: int = 0
    total_trades: int = 0

    poor_entries: list[TradePerformance] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class DrawdownAnalysis:
    """Drawdown analysis."""

    max_drawdown_usd: float = 0.0
    current_drawdown_usd: float = 0.0
    drawdown_periods: list[dict] = field(default_factory=list)


@dataclass
class PerformanceComparison:
    """Comparison of actual vs expected performance."""

    expected_win_rate: float = 60.0
    actual_win_rate: float = 0.0
    win_rate_gap: float = 0.0

    expected_rr_ratio: float = 2.0
    actual_rr_ratio: float = 0.0
    rr_ratio_gap: float = 0.0


@dataclass
class Recommendations:
    """Actionable recommendations for improvement."""

    priority_1: str = ""
    priority_2: str = ""
    priority_3: str = ""

    actions: list[str] = field(default_factory=list)
    min_profit_threshold_pips: float = 15.0


class PerformanceAnalyzer:
    """
    Analyzes trading performance and generates improvement recommendations.

    Usage:
        analyzer = PerformanceAnalyzer()
        metrics = analyzer.calculate_metrics(trades)
        report = analyzer.generate_report(trades)
    """

    def __init__(self):
        """Initialize performance analyzer."""
        self.expected_win_rate = 60.0
        self.expected_rr_ratio = 2.0
        self.min_acceptable_quality = 60.0

    def calculate_metrics(self, trades: list[dict]) -> PerformanceMetrics:
        """
        Calculate overall performance metrics.

        Args:
            trades: List of trade dictionaries

        Returns:
            PerformanceMetrics with calculated values
        """
        if not trades:
            return PerformanceMetrics()

        # Basic counts
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t["status"] == "WIN")
        losing_trades = sum(1 for t in trades if t["status"] == "LOSS")

        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        # Average win/loss
        wins = [t["profit_pips"] for t in trades if t["status"] == "WIN"]
        losses = [t["profit_pips"] for t in trades if t["status"] == "LOSS"]

        avg_win_pips = statistics.mean(wins) if wins else 0.0
        avg_loss_pips = statistics.mean(losses) if losses else 0.0

        # Risk:Reward ratio
        risk_reward_ratio = (avg_win_pips / abs(avg_loss_pips)) if avg_loss_pips != 0 else 0.0

        # P&L
        total_pnl_usd = sum(t["profit_usd"] for t in trades)
        gross_profit = sum(t["profit_usd"] for t in trades if t["status"] == "WIN")
        gross_loss = abs(sum(t["profit_usd"] for t in trades if t["status"] == "LOSS"))

        # Profit factor
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

        # Expectancy
        loss_rate = 1.0 - (win_rate / 100)
        expectancy = (win_rate / 100 * avg_win_pips) - (loss_rate * abs(avg_loss_pips))

        # Sharpe ratio (simplified)
        returns = [t["profit_usd"] for t in trades]
        avg_return = statistics.mean(returns) if returns else 0.0
        std_return = statistics.stdev(returns) if len(returns) > 1 else 1.0
        sharpe_ratio = (avg_return / std_return) if std_return > 0 else 0.0

        # Consecutive wins/losses
        max_consecutive_wins = self._calculate_max_consecutive(trades, "WIN")
        max_consecutive_losses = self._calculate_max_consecutive(trades, "LOSS")

        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 2),
            avg_win_pips=round(avg_win_pips, 2),
            avg_loss_pips=round(avg_loss_pips, 2),
            risk_reward_ratio=round(risk_reward_ratio, 2),
            total_pnl_usd=round(total_pnl_usd, 2),
            gross_profit=round(gross_profit, 2),
            gross_loss=round(gross_loss, 2),
            profit_factor=round(profit_factor, 2),
            expectancy=round(expectancy, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
        )

    def analyze_trailing_stops(self, trades: list[dict]) -> TrailingStopAnalysis:
        """
        Analyze trailing stop effectiveness.

        Args:
            trades: List of trade dictionaries

        Returns:
            TrailingStopAnalysis with recommendations
        """
        trailing_trades = [t for t in trades if t["close_reason"] == "TRAILING_STOP"]

        if not trailing_trades:
            return TrailingStopAnalysis()

        trailing_wins = [t for t in trailing_trades if t["status"] == "WIN"]
        trailing_losses = [t for t in trailing_trades if t["status"] == "LOSS"]

        # Effectiveness score (win rate for trailing stops)
        effectiveness_score = (
            (len(trailing_wins) / len(trailing_trades) * 100) if trailing_trades else 0.0
        )

        # Identify premature exits (wins < 3 pips)
        premature_exits = [
            TradePerformance(**t) for t in trailing_wins if abs(t["profit_pips"]) < 3.0
        ]

        # Calculate averages
        avg_win_on_trailing = (
            statistics.mean([t["profit_pips"] for t in trailing_wins]) if trailing_wins else 0.0
        )
        avg_loss_on_trailing = (
            statistics.mean([t["profit_pips"] for t in trailing_losses]) if trailing_losses else 0.0
        )

        # Identify patterns
        patterns = []
        if len(premature_exits) >= 3:
            patterns.append("premature_activation")
        if len(trailing_losses) > len(trailing_wins):
            patterns.append("tight_trailing_distance")
        if effectiveness_score < 40:
            patterns.append("market_volatility_mismatch")

        # Recommendations (based on analysis)
        # Current: 10 pips activation/distance is too tight
        # Recommended: 20 pips activation, 15 pips distance minimum
        recommended_distance_pips = 15.0
        recommended_activation_pips = 20.0

        return TrailingStopAnalysis(
            total_trailing_closes=len(trailing_trades),
            trailing_wins=len(trailing_wins),
            trailing_losses=len(trailing_losses),
            effectiveness_score=round(effectiveness_score, 2),
            premature_exits=premature_exits,
            recommended_distance_pips=recommended_distance_pips,
            recommended_activation_pips=recommended_activation_pips,
            avg_win_on_trailing=round(avg_win_on_trailing, 2),
            avg_loss_on_trailing=round(avg_loss_on_trailing, 2),
            patterns=patterns,
        )

    def analyze_by_symbol(self, trades: list[dict]) -> dict[str, SymbolAnalysis]:
        """
        Analyze performance per symbol.

        Args:
            trades: List of trade dictionaries

        Returns:
            Dictionary mapping symbol to SymbolAnalysis
        """
        symbol_trades = defaultdict(list)
        for trade in trades:
            symbol_trades[trade["symbol"]].append(trade)

        results = {}
        for symbol, symbol_trade_list in symbol_trades.items():
            total_trades = len(symbol_trade_list)
            winning_trades = sum(1 for t in symbol_trade_list if t["status"] == "WIN")
            losing_trades = sum(1 for t in symbol_trade_list if t["status"] == "LOSS")

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
            loss_rate = (losing_trades / total_trades * 100) if total_trades > 0 else 0.0

            wins = [t["profit_pips"] for t in symbol_trade_list if t["status"] == "WIN"]
            losses = [t["profit_pips"] for t in symbol_trade_list if t["status"] == "LOSS"]

            avg_win_pips = statistics.mean(wins) if wins else 0.0
            avg_loss_pips = statistics.mean(losses) if losses else 0.0

            total_pnl_usd = sum(t["profit_usd"] for t in symbol_trade_list)

            trailing_stop_losses = sum(
                1
                for t in symbol_trade_list
                if t["status"] == "LOSS" and t["close_reason"] == "TRAILING_STOP"
            )
            sl_hit_losses = sum(
                1
                for t in symbol_trade_list
                if t["status"] == "LOSS" and t["close_reason"] == "SL_HIT"
            )

            results[symbol] = SymbolAnalysis(
                symbol=symbol,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=round(win_rate, 2),
                loss_rate=round(loss_rate, 2),
                avg_win_pips=round(avg_win_pips, 2),
                avg_loss_pips=round(avg_loss_pips, 2),
                total_pnl_usd=round(total_pnl_usd, 2),
                trailing_stop_losses=trailing_stop_losses,
                sl_hit_losses=sl_hit_losses,
            )

        return results

    def analyze_entry_quality(self, trades: list[dict]) -> EntryQualityAnalysis:
        """
        Analyze entry point quality.

        Args:
            trades: List of trade dictionaries

        Returns:
            EntryQualityAnalysis with quality score and recommendations
        """
        if not trades:
            return EntryQualityAnalysis()

        # Identify poor entries (trades that went against position immediately)
        # Simplified: use loss trades with very quick closes as proxy
        poor_entries = []
        immediate_drawdown_count = 0

        for trade in trades:
            if trade["status"] == "LOSS":
                # Check if holding time was short (< 2 hours)
                if "close_time" in trade and "open_time" in trade:
                    holding_time = (trade["close_time"] - trade["open_time"]).total_seconds()
                    if holding_time < 7200:  # 2 hours
                        poor_entries.append(TradePerformance(**trade))
                        immediate_drawdown_count += 1

        # Quality score based on win rate and immediate drawdowns
        win_rate = sum(1 for t in trades if t["status"] == "WIN") / len(trades) * 100
        quality_score = win_rate - (immediate_drawdown_count / len(trades) * 20)
        quality_score = max(0, min(100, quality_score))

        # Recommendations
        recommendations = []
        if quality_score < 60:
            recommendations.append("raise_minimum_confluence_to_75")
            recommendations.append("add_trend_alignment_filter")
            recommendations.append("add_volatility_filter")
        if immediate_drawdown_count > len(trades) * 0.3:
            recommendations.append("improve_entry_timing")
            recommendations.append("wait_for_confirmation")

        return EntryQualityAnalysis(
            quality_score=round(quality_score, 2),
            immediate_drawdown_count=immediate_drawdown_count,
            total_trades=len(trades),
            poor_entries=poor_entries,
            recommendations=recommendations,
        )

    def identify_loss_patterns(self, trades: list[dict]) -> dict[str, any]:
        """
        Identify common patterns in losing trades.

        Args:
            trades: List of trade dictionaries

        Returns:
            Dictionary with identified patterns
        """
        losses = [t for t in trades if t["status"] == "LOSS"]

        patterns = {
            "total_losses": len(losses),
            "premature_activation": False,
            "tight_trailing_distance": False,
            "market_volatility_mismatch": False,
            "low_confluence_entries": False,
            "counter_trend_entries": False,
        }

        # Trailing stop analysis
        trailing_losses = [t for t in losses if t["close_reason"] == "TRAILING_STOP"]
        if len(trailing_losses) > len(losses) * 0.6:
            patterns["premature_activation"] = True
            patterns["tight_trailing_distance"] = True

        # Volatility mismatch (simplified: check if losses are small and frequent)
        small_losses = [t for t in losses if abs(t["profit_pips"]) < 3.0]
        if len(small_losses) > len(losses) * 0.5:
            patterns["market_volatility_mismatch"] = True

        # Low confluence (would need actual signal data, using proxy)
        # Assume if win rate < 40%, likely low confluence entries
        win_rate = sum(1 for t in trades if t["status"] == "WIN") / len(trades) * 100
        if win_rate < 40:
            patterns["low_confluence_entries"] = True
            patterns["counter_trend_entries"] = True

        return patterns

    def compare_vs_expected(self, trades: list[dict]) -> PerformanceComparison:
        """
        Compare actual vs expected performance.

        Args:
            trades: List of trade dictionaries

        Returns:
            PerformanceComparison with gaps identified
        """
        metrics = self.calculate_metrics(trades)

        win_rate_gap = self.expected_win_rate - metrics.win_rate
        rr_ratio_gap = self.expected_rr_ratio - metrics.risk_reward_ratio

        return PerformanceComparison(
            expected_win_rate=self.expected_win_rate,
            actual_win_rate=metrics.win_rate,
            win_rate_gap=round(win_rate_gap, 2),
            expected_rr_ratio=self.expected_rr_ratio,
            actual_rr_ratio=metrics.risk_reward_ratio,
            rr_ratio_gap=round(rr_ratio_gap, 2),
        )

    def rank_symbols(self, trades: list[dict]) -> list[SymbolAnalysis]:
        """
        Rank symbols by performance.

        Args:
            trades: List of trade dictionaries

        Returns:
            List of SymbolAnalysis sorted by total P&L (best to worst)
        """
        symbol_analysis = self.analyze_by_symbol(trades)

        # Sort by total_pnl_usd descending
        ranked = sorted(symbol_analysis.values(), key=lambda x: x.total_pnl_usd, reverse=True)

        return ranked

    def analyze_drawdowns(self, trades: list[dict]) -> DrawdownAnalysis:
        """
        Analyze drawdown periods.

        Args:
            trades: List of trade dictionaries

        Returns:
            DrawdownAnalysis with drawdown metrics
        """
        if not trades:
            return DrawdownAnalysis()

        # Sort trades by close time
        sorted_trades = sorted(trades, key=lambda x: x["close_time"])

        # Calculate cumulative P&L and track drawdowns
        cumulative_pnl = 0.0
        peak_pnl = 0.0
        max_drawdown = 0.0
        current_drawdown = 0.0
        drawdown_periods = []
        in_drawdown = False
        drawdown_start = None

        for trade in sorted_trades:
            cumulative_pnl += trade["profit_usd"]

            if cumulative_pnl > peak_pnl:
                peak_pnl = cumulative_pnl
                if in_drawdown:
                    # Drawdown recovered
                    drawdown_periods.append(
                        {
                            "start_time": drawdown_start,
                            "end_time": trade["close_time"],
                            "max_drawdown": current_drawdown,
                        }
                    )
                    in_drawdown = False
                    current_drawdown = 0.0
            else:
                # In drawdown
                current_drawdown = peak_pnl - cumulative_pnl
                if current_drawdown > max_drawdown:
                    max_drawdown = current_drawdown

                if not in_drawdown:
                    in_drawdown = True
                    drawdown_start = trade["close_time"]

        # Current drawdown (if still in one)
        final_current_drawdown = peak_pnl - cumulative_pnl if peak_pnl > cumulative_pnl else 0.0

        return DrawdownAnalysis(
            max_drawdown_usd=round(max_drawdown, 2),
            current_drawdown_usd=round(final_current_drawdown, 2),
            drawdown_periods=drawdown_periods,
        )

    def identify_improvements(self, trades: list[dict]) -> dict[str, bool]:
        """
        Identify areas needing improvement.

        Args:
            trades: List of trade dictionaries

        Returns:
            Dictionary of improvement areas
        """
        metrics = self.calculate_metrics(trades)
        trailing_analysis = self.analyze_trailing_stops(trades)
        entry_analysis = self.analyze_entry_quality(trades)

        improvements = {}

        # Trailing stop issues
        if trailing_analysis.effectiveness_score < 50:
            improvements["trailing_stop_optimization"] = True

        # Entry quality issues
        if entry_analysis.quality_score < 60:
            improvements["entry_quality_filter"] = True

        # Risk management issues
        if metrics.risk_reward_ratio < 2.0:
            improvements["risk_management_adjustment"] = True

        # Win rate issues
        if metrics.win_rate < 50:
            improvements["confluence_threshold_increase"] = True
            improvements["trend_alignment_filter"] = True

        return improvements

    def generate_recommendations(self, trades: list[dict]) -> Recommendations:
        """
        Generate actionable recommendations.

        Args:
            trades: List of trade dictionaries

        Returns:
            Recommendations with prioritized actions
        """
        metrics = self.calculate_metrics(trades)
        trailing_analysis = self.analyze_trailing_stops(trades)
        entry_analysis = self.analyze_entry_quality(trades)

        # Priority recommendations
        priority_1 = "fix_trailing_stop"
        priority_2 = "raise_confluence" if metrics.win_rate < 50 else "add_trend_filter"
        priority_3 = "reduce_risk_per_trade"

        # Specific actions
        actions = []

        # Trailing stop actions
        actions.append("atr_based_trailing")
        actions.append(
            f"increase_activation_distance to {trailing_analysis.recommended_activation_pips} pips"
        )
        actions.append(
            f"widen_trailing_distance to {trailing_analysis.recommended_distance_pips} pips"
        )

        # Entry quality actions
        if entry_analysis.quality_score < 60:
            actions.append("raise_min_confluence_to_75_percent")
            actions.append("add_trend_alignment_filter")
            actions.append("add_volatility_filter")

        # Risk management actions
        if metrics.risk_reward_ratio < 2.0:
            actions.append("reduce_risk_per_trade_to_0.5_percent")
            actions.append("max_3_simultaneous_positions")

        return Recommendations(
            priority_1=priority_1,
            priority_2=priority_2,
            priority_3=priority_3,
            actions=actions,
            min_profit_threshold_pips=trailing_analysis.recommended_activation_pips,
        )

    def generate_report(self, trades: list[dict]) -> dict[str, any]:
        """
        Generate comprehensive performance report.

        Args:
            trades: List of trade dictionaries

        Returns:
            Dictionary with complete analysis and recommendations
        """
        overall_metrics = self.calculate_metrics(trades)
        trailing_stop_analysis = self.analyze_trailing_stops(trades)
        symbol_analysis = self.analyze_by_symbol(trades)
        entry_analysis = self.analyze_entry_quality(trades)
        drawdown_analysis = self.analyze_drawdowns(trades)
        comparison = self.compare_vs_expected(trades)
        recommendations = self.generate_recommendations(trades)

        return {
            "overall_metrics": overall_metrics,
            "trailing_stop_analysis": trailing_stop_analysis,
            "symbol_analysis": symbol_analysis,
            "entry_analysis": entry_analysis,
            "drawdown_analysis": drawdown_analysis,
            "comparison": comparison,
            "recommendations": recommendations,
            "loss_patterns": self.identify_loss_patterns(trades),
            "improvements_needed": self.identify_improvements(trades),
        }

    def _calculate_max_consecutive(self, trades: list[dict], status: str) -> int:
        """
        Calculate maximum consecutive wins or losses.

        Args:
            trades: List of trade dictionaries
            status: "WIN" or "LOSS"

        Returns:
            Maximum consecutive count
        """
        if not trades:
            return 0

        # Sort by close time
        sorted_trades = sorted(trades, key=lambda x: x["close_time"])

        max_consecutive = 0
        current_consecutive = 0

        for trade in sorted_trades:
            if trade["status"] == status:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive
