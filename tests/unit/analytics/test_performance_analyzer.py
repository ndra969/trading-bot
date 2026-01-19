"""
Unit tests for PerformanceAnalyzer - Week 15.5.1

Tests trading performance analysis including:
- Win rate calculation
- Risk:Reward ratio analysis
- Trailing stop effectiveness
- Entry/exit quality analysis
- Root cause identification for losses
"""

from datetime import datetime

import pytest

# These imports will fail initially (RED phase) - we'll implement them next
from src.trading_bot.analytics.performance_analyzer import (
    PerformanceAnalyzer,
)


# Test fixtures
@pytest.fixture
def sample_trades() -> list[dict]:
    """Sample trades from Week 1 (Jan 5-9, 2026) with actual data."""
    return [
        # GBPUSD trades (8 trades, 25% win rate)
        {
            "symbol": "GBPUSD",
            "direction": "BUY",
            "entry_price": 1.34548,
            "exit_price": 1.34397,
            "profit_pips": 1.51,
            "profit_usd": 1.51,
            "status": "WIN",
            "close_reason": "TP_HIT",
            "open_time": datetime(2026, 1, 5, 10, 0),
            "close_time": datetime(2026, 1, 5, 14, 30),
        },
        {
            "symbol": "GBPUSD",
            "direction": "BUY",
            "entry_price": 1.34608,
            "exit_price": 1.35388,
            "profit_pips": 7.80,
            "profit_usd": 7.80,
            "status": "WIN",
            "close_reason": "TP_HIT",
            "open_time": datetime(2026, 1, 6, 8, 0),
            "close_time": datetime(2026, 1, 6, 16, 45),
        },
        {
            "symbol": "GBPUSD",
            "direction": "BUY",
            "entry_price": 1.34903,
            "exit_price": 1.34702,
            "profit_pips": -2.01,
            "profit_usd": -2.01,
            "status": "LOSS",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 7, 9, 0),
            "close_time": datetime(2026, 1, 7, 11, 20),
        },
        {
            "symbol": "GBPUSD",
            "direction": "BUY",
            "entry_price": 1.34433,
            "exit_price": 1.34224,
            "profit_pips": -2.09,
            "profit_usd": -2.09,
            "status": "LOSS",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 7, 13, 0),
            "close_time": datetime(2026, 1, 7, 15, 10),
        },
        {
            "symbol": "GBPUSD",
            "direction": "BUY",
            "entry_price": 1.35575,
            "exit_price": 1.35396,
            "profit_pips": -1.79,
            "profit_usd": -1.79,
            "status": "LOSS",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 8, 10, 30),
            "close_time": datetime(2026, 1, 8, 12, 45),
        },
        {
            "symbol": "GBPUSD",
            "direction": "BUY",
            "entry_price": 1.34763,
            "exit_price": 1.34539,
            "profit_pips": -2.24,
            "profit_usd": -2.24,
            "status": "LOSS",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 8, 14, 0),
            "close_time": datetime(2026, 1, 8, 16, 30),
        },
        {
            "symbol": "GBPUSD",
            "direction": "BUY",
            "entry_price": 1.35371,
            "exit_price": 1.34872,
            "profit_pips": -4.99,
            "profit_usd": -4.99,
            "status": "LOSS",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 9, 8, 0),
            "close_time": datetime(2026, 1, 9, 10, 15),
        },
        # EURUSD trades (3 wins, 3 losses = 50% win rate)
        {
            "symbol": "EURUSD",
            "direction": "SELL",
            "entry_price": 1.17183,
            "exit_price": 1.17080,
            "profit_pips": 1.03,
            "profit_usd": 1.03,
            "status": "WIN",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 5, 11, 0),
            "close_time": datetime(2026, 1, 5, 13, 20),
        },
        {
            "symbol": "EURUSD",
            "direction": "SELL",
            "entry_price": 1.17066,
            "exit_price": 1.17181,
            "profit_pips": -1.15,
            "profit_usd": -1.15,
            "status": "LOSS",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 6, 9, 30),
            "close_time": datetime(2026, 1, 6, 11, 45),
        },
        {
            "symbol": "EURUSD",
            "direction": "SELL",
            "entry_price": 1.16809,
            "exit_price": 1.16692,
            "profit_pips": 1.17,
            "profit_usd": 1.17,
            "status": "WIN",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 7, 10, 0),
            "close_time": datetime(2026, 1, 7, 12, 30),
        },
        {
            "symbol": "EURUSD",
            "direction": "SELL",
            "entry_price": 1.16699,
            "exit_price": 1.17089,
            "profit_pips": -3.90,
            "profit_usd": -3.90,
            "status": "LOSS",
            "close_reason": "SL_HIT",
            "open_time": datetime(2026, 1, 8, 9, 0),
            "close_time": datetime(2026, 1, 8, 10, 30),
        },
        {
            "symbol": "EURUSD",
            "direction": "SELL",
            "entry_price": 1.16611,
            "exit_price": 1.16408,
            "profit_pips": 2.03,
            "profit_usd": 2.03,
            "status": "WIN",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 8, 13, 0),
            "close_time": datetime(2026, 1, 8, 15, 20),
        },
        {
            "symbol": "EURUSD",
            "direction": "SELL",
            "entry_price": 1.17073,
            "exit_price": 1.16569,
            "profit_pips": -5.04,
            "profit_usd": -5.04,
            "status": "LOSS",
            "close_reason": "SL_HIT",
            "open_time": datetime(2026, 1, 9, 9, 30),
            "close_time": datetime(2026, 1, 9, 11, 0),
        },
        # USDJPY trades (2 wins, 3 losses = 40% win rate)
        {
            "symbol": "USDJPY",
            "direction": "BUY",
            "entry_price": 156.442,
            "exit_price": 157.370,
            "profit_pips": 5.90,
            "profit_usd": 5.90,
            "status": "WIN",
            "close_reason": "TP_HIT",
            "open_time": datetime(2026, 1, 5, 12, 0),
            "close_time": datetime(2026, 1, 5, 17, 30),
        },
        {
            "symbol": "USDJPY",
            "direction": "SELL",
            "entry_price": 156.732,
            "exit_price": 156.354,
            "profit_pips": 2.42,
            "profit_usd": 2.42,
            "status": "WIN",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 6, 10, 0),
            "close_time": datetime(2026, 1, 6, 13, 15),
        },
        {
            "symbol": "USDJPY",
            "direction": "BUY",
            "entry_price": 157.374,
            "exit_price": 157.583,
            "profit_pips": -1.33,
            "profit_usd": -1.33,
            "status": "LOSS",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 7, 11, 0),
            "close_time": datetime(2026, 1, 7, 13, 20),
        },
        {
            "symbol": "USDJPY",
            "direction": "BUY",
            "entry_price": 156.619,
            "exit_price": 156.375,
            "profit_pips": -1.56,
            "profit_usd": -1.56,
            "status": "LOSS",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 8, 11, 30),
            "close_time": datetime(2026, 1, 8, 14, 0),
        },
        {
            "symbol": "USDJPY",
            "direction": "BUY",
            "entry_price": 156.558,
            "exit_price": 156.750,
            "profit_pips": -1.22,
            "profit_usd": -1.22,
            "status": "LOSS",
            "close_reason": "TRAILING_STOP",
            "open_time": datetime(2026, 1, 9, 10, 0),
            "close_time": datetime(2026, 1, 9, 12, 30),
        },
    ]


@pytest.fixture
def performance_analyzer():
    """Create PerformanceAnalyzer instance."""
    return PerformanceAnalyzer()


# Test Suite 1: Overall Performance Metrics (5 tests)
class TestOverallPerformanceMetrics:
    """Test overall performance calculation."""

    def test_calculate_overall_win_rate(self, performance_analyzer, sample_trades):
        """Test win rate calculation from sample trades."""
        metrics = performance_analyzer.calculate_metrics(sample_trades)

        # Expected: 7 wins out of 18 trades = 38.89%
        assert metrics.win_rate == pytest.approx(38.89, abs=0.1)
        assert metrics.total_trades == 18
        assert metrics.winning_trades == 7
        assert metrics.losing_trades == 11

    def test_calculate_average_win_loss(self, performance_analyzer, sample_trades):
        """Test average win and loss calculation."""
        metrics = performance_analyzer.calculate_metrics(sample_trades)

        # Expected averages from actual data
        # 7 wins: 1.51, 7.80, 1.03, 1.17, 2.03, 5.90, 2.42 = avg 3.12
        # 11 losses: -2.01, -2.09, -1.79, -2.24, -4.99, -1.15, -3.90, -5.04, -1.33, -1.56, -1.22 = avg -2.48
        assert metrics.avg_win_pips == pytest.approx(3.12, abs=0.1)
        assert metrics.avg_loss_pips == pytest.approx(-2.48, abs=0.1)

    def test_calculate_risk_reward_ratio(self, performance_analyzer, sample_trades):
        """Test risk:reward ratio calculation."""
        metrics = performance_analyzer.calculate_metrics(sample_trades)

        # Expected: avg_win / abs(avg_loss) = 2.98 / 2.42 = 1.23:1
        assert metrics.risk_reward_ratio == pytest.approx(1.23, abs=0.05)

        # CRITICAL: This is too low! Need 2:1 minimum for profitability
        assert metrics.risk_reward_ratio < 2.0, "Risk:Reward is below profitable threshold"

    def test_calculate_profit_factor(self, performance_analyzer, sample_trades):
        """Test profit factor calculation."""
        metrics = performance_analyzer.calculate_metrics(sample_trades)

        # Profit factor = gross_profit / gross_loss
        # Expected to be negative or very low given the losses
        assert metrics.profit_factor < 1.5
        assert metrics.total_pnl_usd < 0, "Overall P&L should be negative"

    def test_calculate_expectancy(self, performance_analyzer, sample_trades):
        """Test expectancy calculation."""
        metrics = performance_analyzer.calculate_metrics(sample_trades)

        # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        expected_expectancy = (0.3889 * 2.98) - (0.6111 * 2.42)
        assert metrics.expectancy == pytest.approx(expected_expectancy, abs=0.1)
        assert metrics.expectancy < 0, "Expectancy should be negative given current performance"


# Test Suite 2: Trailing Stop Analysis (6 tests)
class TestTrailingStopAnalysis:
    """Test trailing stop effectiveness analysis."""

    def test_analyze_trailing_stop_effectiveness(self, performance_analyzer, sample_trades):
        """Test analysis of trailing stop performance."""
        trailing_analysis = performance_analyzer.analyze_trailing_stops(sample_trades)

        # Count trailing stop closes (13 out of 18 trades)
        trailing_closes = [t for t in sample_trades if t["close_reason"] == "TRAILING_STOP"]
        assert len(trailing_closes) == 13  # Majority are trailing stop

        # Analyze win/loss ratio for trailing stops
        trailing_wins = [t for t in trailing_closes if t["status"] == "WIN"]
        trailing_losses = [t for t in trailing_closes if t["status"] == "LOSS"]

        assert len(trailing_losses) > len(trailing_wins), "More losses than wins via trailing stop"
        assert trailing_analysis.effectiveness_score < 50, "Trailing stop effectiveness is poor"

    def test_identify_premature_trailing_exits(self, performance_analyzer, sample_trades):
        """Test identification of trades closed too early by trailing stop."""
        trailing_analysis = performance_analyzer.analyze_trailing_stops(sample_trades)

        # EURUSD trades show tiny wins (1.03, 1.17, 2.03 pips) - too small!
        premature_exits = trailing_analysis.premature_exits
        assert len(premature_exits) >= 3, "Should identify EURUSD trades as premature"

        # Check for small win sizes
        small_wins = [t for t in sample_trades if t["status"] == "WIN" and t["profit_pips"] < 3]
        assert len(small_wins) >= 3, "Many wins are too small (<3 pips)"

    def test_calculate_optimal_trailing_distance(self, performance_analyzer, sample_trades):
        """Test calculation of optimal trailing distance."""
        trailing_analysis = performance_analyzer.analyze_trailing_stops(sample_trades)

        # Current: 10 pips for GBPUSD
        # Optimal should be wider (15-25 pips based on volatility)
        assert trailing_analysis.recommended_distance_pips > 10
        assert trailing_analysis.recommended_distance_pips <= 25

    def test_trailing_stop_by_symbol(self, performance_analyzer, sample_trades):
        """Test trailing stop analysis per symbol."""
        symbol_analysis = performance_analyzer.analyze_by_symbol(sample_trades)

        # GBPUSD: 75% loss rate with trailing stops
        gbpusd_stats = symbol_analysis["GBPUSD"]
        assert gbpusd_stats.loss_rate > 0.70, "GBPUSD has very high loss rate"

        # EURUSD: Small wins, big losses
        eurusd_stats = symbol_analysis["EURUSD"]
        assert eurusd_stats.avg_win_pips < 2.0, "EURUSD wins are too small"
        assert abs(eurusd_stats.avg_loss_pips) > eurusd_stats.avg_win_pips

    def test_identify_trailing_stop_pattern(self, performance_analyzer, sample_trades):
        """Test pattern identification in trailing stop losses."""
        patterns = performance_analyzer.identify_loss_patterns(sample_trades)

        # Pattern: Trailing stop activated too early (after small profit)
        assert "premature_activation" in patterns
        assert "tight_trailing_distance" in patterns
        assert "market_volatility_mismatch" in patterns

    def test_generate_trailing_stop_recommendations(self, performance_analyzer, sample_trades):
        """Test generation of recommendations for trailing stop fixes."""
        recommendations = performance_analyzer.generate_recommendations(sample_trades)

        # Expected recommendations in actions list
        actions_str = " ".join(recommendations.actions)
        assert "atr_based_trailing" in actions_str
        assert "activation_distance" in actions_str or "increase_activation" in actions_str
        assert "trailing_distance" in actions_str or "widen_trailing" in actions_str
        assert recommendations.min_profit_threshold_pips >= 15


# Test Suite 3: Entry Quality Analysis (5 tests)
class TestEntryQualityAnalysis:
    """Test entry quality and signal analysis."""

    def test_analyze_entry_quality(self, performance_analyzer, sample_trades):
        """Test entry point quality analysis."""
        entry_analysis = performance_analyzer.analyze_entry_quality(sample_trades)

        # Check if trades go against position immediately
        # (indicates poor entry timing)
        assert entry_analysis.quality_score < 60, "Entry quality is below acceptable"

    def test_identify_losing_patterns(self, performance_analyzer, sample_trades):
        """Test identification of common patterns in losing trades."""
        patterns = performance_analyzer.identify_loss_patterns(sample_trades)

        assert "low_confluence_entries" in patterns or "counter_trend_entries" in patterns
        assert patterns["total_losses"] == 11

    def test_calculate_entry_timing_accuracy(self, performance_analyzer, sample_trades):
        """Test entry timing accuracy."""
        entry_analysis = performance_analyzer.analyze_entry_quality(sample_trades)

        # Good entries should not immediately go negative
        # Check for immediate drawdown (losses closed within 2 hours)
        # With actual data, we have 2 SL hits within 2 hours
        assert entry_analysis.immediate_drawdown_count >= 2, "Should detect quick losses"
        assert entry_analysis.total_trades == 18

    def test_analyze_best_worst_symbols(self, performance_analyzer, sample_trades):
        """Test identification of best and worst performing symbols."""
        symbol_analysis = performance_analyzer.analyze_by_symbol(sample_trades)

        # GBPUSD is worst (25% win rate)
        gbpusd = symbol_analysis["GBPUSD"]
        assert gbpusd.win_rate < 30, "GBPUSD has very low win rate"

        # EURUSD is better (50% win rate but small wins)
        eurusd = symbol_analysis["EURUSD"]
        assert 45 <= eurusd.win_rate <= 55

    def test_compare_actual_vs_expected_performance(self, performance_analyzer, sample_trades):
        """Test comparison of actual vs expected performance."""
        comparison = performance_analyzer.compare_vs_expected(sample_trades)

        # Expected: 60% win rate with 2:1 RR
        # Actual: 39% win rate with 1.23:1 RR
        assert comparison.win_rate_gap > 20, "Win rate significantly below target"
        assert comparison.rr_ratio_gap > 0.7, "Risk:reward ratio significantly below target"


# Test Suite 4: Symbol-Specific Analysis (4 tests)
class TestSymbolSpecificAnalysis:
    """Test per-symbol performance analysis."""

    def test_analyze_gbpusd_performance(self, performance_analyzer, sample_trades):
        """Test GBPUSD-specific analysis."""
        gbpusd_trades = [t for t in sample_trades if t["symbol"] == "GBPUSD"]
        metrics = performance_analyzer.calculate_metrics(gbpusd_trades)

        assert metrics.total_trades == 7  # 7 closed + 1 open
        assert metrics.win_rate == pytest.approx(25.0, abs=5)  # 2 wins / 8 trades = 25%
        assert metrics.total_pnl_usd < 0, "GBPUSD is losing money"

    def test_analyze_eurusd_performance(self, performance_analyzer, sample_trades):
        """Test EURUSD-specific analysis."""
        eurusd_trades = [t for t in sample_trades if t["symbol"] == "EURUSD"]
        metrics = performance_analyzer.calculate_metrics(eurusd_trades)

        assert metrics.total_trades == 6
        assert 45 <= metrics.win_rate <= 55, "EURUSD ~50% win rate"
        # But average wins too small!
        assert metrics.avg_win_pips < 2.5, "EURUSD wins are very small"

    def test_analyze_usdjpy_performance(self, performance_analyzer, sample_trades):
        """Test USDJPY-specific analysis."""
        usdjpy_trades = [t for t in sample_trades if t["symbol"] == "USDJPY"]
        metrics = performance_analyzer.calculate_metrics(usdjpy_trades)

        assert metrics.total_trades == 5
        assert metrics.win_rate == pytest.approx(40.0, abs=5)
        assert metrics.avg_win_pips > metrics.avg_loss_pips, "USDJPY better RR than others"

    def test_rank_symbols_by_performance(self, performance_analyzer, sample_trades):
        """Test ranking symbols by performance."""
        ranking = performance_analyzer.rank_symbols(sample_trades)

        # Best to worst by total P&L: USDJPY (+4.21), GBPUSD (-3.81), EURUSD (-5.86)
        assert ranking[0].symbol == "USDJPY", "USDJPY should be best (positive P&L)"
        assert ranking[-1].symbol == "EURUSD", "EURUSD should be worst (most negative P&L)"
        assert len(ranking) == 3


# Test Suite 5: Report Generation (5 tests)
class TestReportGeneration:
    """Test performance report generation."""

    def test_generate_performance_report(self, performance_analyzer, sample_trades):
        """Test generation of comprehensive performance report."""
        report = performance_analyzer.generate_report(sample_trades)

        assert "overall_metrics" in report
        assert "trailing_stop_analysis" in report
        assert "symbol_analysis" in report
        assert "recommendations" in report

    def test_identify_improvement_areas(self, performance_analyzer, sample_trades):
        """Test identification of areas needing improvement."""
        improvements = performance_analyzer.identify_improvements(sample_trades)

        # Critical improvements needed
        assert "trailing_stop_optimization" in improvements
        assert "entry_quality_filter" in improvements
        assert "risk_management_adjustment" in improvements

    def test_calculate_sharpe_ratio_actual(self, performance_analyzer, sample_trades):
        """Test Sharpe ratio calculation from actual trades."""
        metrics = performance_analyzer.calculate_metrics(sample_trades)

        # With negative returns, Sharpe ratio will be negative
        assert (
            metrics.sharpe_ratio < 0
        ), "Negative Sharpe ratio indicates poor risk-adjusted returns"

    def test_analyze_drawdown_periods(self, performance_analyzer, sample_trades):
        """Test drawdown period analysis."""
        drawdown_analysis = performance_analyzer.analyze_drawdowns(sample_trades)

        assert drawdown_analysis.max_drawdown_usd > 0
        assert drawdown_analysis.current_drawdown_usd > 0
        assert len(drawdown_analysis.drawdown_periods) > 0

    def test_generate_recommendations(self, performance_analyzer, sample_trades):
        """Test generation of actionable recommendations."""
        recommendations = performance_analyzer.generate_recommendations(sample_trades)

        # Priority recommendations
        assert recommendations.priority_1 == "fix_trailing_stop"
        assert recommendations.priority_2 in ["raise_confluence", "add_trend_filter"]
        assert recommendations.priority_3 == "reduce_risk_per_trade"

        # Specific actions
        assert len(recommendations.actions) >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
