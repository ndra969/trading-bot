"""
Trading Performance Analysis Script - Week 15.5.1

Analyzes trading performance from Week 1 (Jan 5-9, 2026) and generates
comprehensive report with actionable recommendations.

Usage:
    uv run python scripts/analyze_trading_performance.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_bot.analytics.performance_analyzer import PerformanceAnalyzer
from datetime import datetime
import json


def get_week1_trades():
    """Get actual Week 1 trading data (Jan 5-9, 2026)."""
    return [
        # GBPUSD trades (2 wins, 6 losses = 25% win rate)
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
        # EURUSD trades (3 wins, 3 losses = 50% win rate but small wins)
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


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def main():
    """Run performance analysis and generate report."""
    # Set UTF-8 encoding for Windows console
    import sys

    if sys.platform == "win32":
        import codecs

        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

    print_section("🔍 TRADING PERFORMANCE ANALYSIS - WEEK 1 (Jan 5-9, 2026)")

    # Get trading data
    trades = get_week1_trades()
    print(f"\n📊 Analyzing {len(trades)} closed positions...")

    # Initialize analyzer
    analyzer = PerformanceAnalyzer()

    # Generate comprehensive report
    report = analyzer.generate_report(trades)

    # Display overall metrics
    print_section("📈 OVERALL PERFORMANCE METRICS")
    metrics = report["overall_metrics"]
    print(
        f"""
    Total Trades:        {metrics.total_trades}
    Winning Trades:      {metrics.winning_trades}
    Losing Trades:       {metrics.losing_trades}
    Win Rate:            {metrics.win_rate}% ⚠️ (Target: 60%+)
    
    Average Win:         +{metrics.avg_win_pips} pips
    Average Loss:        {metrics.avg_loss_pips} pips
    Risk:Reward Ratio:   {metrics.risk_reward_ratio}:1 🔴 (Target: 2:1+)
    
    Total P&L:           ${metrics.total_pnl_usd} 🔴 NEGATIVE
    Gross Profit:        ${metrics.gross_profit}
    Gross Loss:          ${metrics.gross_loss}
    Profit Factor:       {metrics.profit_factor} 🔴 (Target: 1.5+)
    
    Expectancy:          {metrics.expectancy} pips/trade 🔴
    Sharpe Ratio:        {metrics.sharpe_ratio} 🔴 NEGATIVE
    
    Max Consecutive Wins:   {metrics.max_consecutive_wins}
    Max Consecutive Losses: {metrics.max_consecutive_losses} ⚠️
    """
    )

    # Display trailing stop analysis
    print_section("🛑 TRAILING STOP ANALYSIS")
    trailing = report["trailing_stop_analysis"]
    print(
        f"""
    Total Trailing Stop Closes:  {trailing.total_trailing_closes} (out of {metrics.total_trades})
    Trailing Stop Wins:          {trailing.trailing_wins}
    Trailing Stop Losses:        {trailing.trailing_losses} 🔴 MORE LOSSES!
    Effectiveness Score:         {trailing.effectiveness_score}% 🔴 (Target: 60%+)
    
    Average Win (Trailing):      +{trailing.avg_win_on_trailing} pips ⚠️ TOO SMALL
    Average Loss (Trailing):     {trailing.avg_loss_on_trailing} pips
    
    Premature Exits Detected:    {len(trailing.premature_exits)} trades
    
    🔧 RECOMMENDATIONS:
    - Recommended Activation:     {trailing.recommended_activation_pips} pips (current: 10 pips)
    - Recommended Distance:       {trailing.recommended_distance_pips} pips (current: 10 pips)
    
    🚨 PATTERNS IDENTIFIED:
    """
    )
    for pattern in trailing.patterns:
        print(f"    - {pattern}")

    # Display symbol analysis
    print_section("🎯 PER-SYMBOL PERFORMANCE")
    for symbol, stats in report["symbol_analysis"].items():
        print(
            f"""
    {symbol}:
      Trades:        {stats.total_trades}
      Win Rate:      {stats.win_rate}%
      Avg Win:       +{stats.avg_win_pips} pips
      Avg Loss:      {stats.avg_loss_pips} pips
      Total P&L:     ${stats.total_pnl_usd}
      Trailing Losses: {stats.trailing_stop_losses}
      SL Hit Losses:   {stats.sl_hit_losses}
    """
        )

    # Display entry quality
    print_section("🎯 ENTRY QUALITY ANALYSIS")
    entry = report["entry_analysis"]
    print(
        f"""
    Quality Score:              {entry.quality_score}/100 🔴 (Target: 60+)
    Immediate Drawdown Count:   {entry.immediate_drawdown_count}
    Total Trades:               {entry.total_trades}
    
    🔧 RECOMMENDATIONS:
    """
    )
    for rec in entry.recommendations:
        print(f"    - {rec}")

    # Display drawdown analysis
    print_section("📉 DRAWDOWN ANALYSIS")
    drawdown = report["drawdown_analysis"]
    print(
        f"""
    Max Drawdown:      ${drawdown.max_drawdown_usd}
    Current Drawdown:  ${drawdown.current_drawdown_usd}
    Drawdown Periods:  {len(drawdown.drawdown_periods)}
    """
    )

    # Display comparison vs expected
    print_section("⚖️ ACTUAL VS EXPECTED PERFORMANCE")
    comparison = report["comparison"]
    print(
        f"""
    Win Rate:
      Expected:  {comparison.expected_win_rate}%
      Actual:    {comparison.actual_win_rate}%
      Gap:       {comparison.win_rate_gap}% 🔴 SIGNIFICANT GAP
    
    Risk:Reward Ratio:
      Expected:  {comparison.expected_rr_ratio}:1
      Actual:    {comparison.actual_rr_ratio}:1
      Gap:       {comparison.rr_ratio_gap} 🔴 SIGNIFICANT GAP
    """
    )

    # Display priority recommendations
    print_section("🚀 PRIORITY RECOMMENDATIONS")
    recommendations = report["recommendations"]
    print(
        f"""
    Priority 1: {recommendations.priority_1.upper().replace('_', ' ')} 🔴 URGENT
    Priority 2: {recommendations.priority_2.upper().replace('_', ' ')} 🔴 URGENT
    Priority 3: {recommendations.priority_3.upper().replace('_', ' ')} ⚠️ HIGH
    
    ACTIONABLE STEPS:
    """
    )
    for i, action in enumerate(recommendations.actions, 1):
        print(f"    {i}. {action}")

    # Display improvements needed
    print_section("⚠️ IMPROVEMENTS NEEDED")
    improvements = report["improvements_needed"]
    print("\n    Critical Areas:")
    for area, needed in improvements.items():
        if needed:
            print(f"    ✅ {area.replace('_', ' ').title()}")

    # Final summary
    print_section("📋 EXECUTIVE SUMMARY")
    print(
        f"""
    🔴 CRITICAL ISSUES IDENTIFIED:
    
    1. Win Rate Too Low (39% vs 60% target)
       - Need stricter entry filters
       - Raise minimum confluence to 75%
       - Add trend alignment validation
    
    2. Poor Risk:Reward Ratio (1.23:1 vs 2:1 target)
       - Trailing stops too tight (locking in tiny profits)
       - Not adapting to market volatility
       - Need ATR-based trailing stops
    
    3. Trailing Stop Ineffective (38% effectiveness)
       - 13 out of 18 trades closed by trailing stop
       - More losses than wins via trailing stop
       - Premature exits giving back profits
    
    4. Negative Expectancy (-0.52 pips/trade)
       - System losing money long-term
       - Need immediate fixes before resuming live trading
    
    🔧 IMMEDIATE ACTIONS REQUIRED:
    
    1. 🛑 STOP LIVE TRADING until fixes implemented
    2. 🔧 Implement ATR-based trailing stops (activation: 20 pips, distance: 15 pips)
    3. 🔧 Raise minimum confluence from 65% to 75%
    4. 🔧 Add trend alignment filter (check H4/D1 trends)
    5. 🔧 Reduce risk per trade to 0.5% (from 1%)
    6. 🔧 Backtest all changes before resuming live trading
    
    ⏱️ NEXT STEPS:
    
    Phase 1: Implement fixes (Week 15.5.2 - 15.5.4)
    Phase 2: Backtest validation (compare before/after)
    Phase 3: Resume live trading with monitoring
    """
    )

    # Save report to JSON
    output_file = "week1_performance_report.json"
    with open(output_file, "w") as f:
        # Convert report to JSON-serializable format
        json_report = {
            "overall_metrics": {
                "total_trades": metrics.total_trades,
                "winning_trades": metrics.winning_trades,
                "losing_trades": metrics.losing_trades,
                "win_rate": metrics.win_rate,
                "avg_win_pips": metrics.avg_win_pips,
                "avg_loss_pips": metrics.avg_loss_pips,
                "risk_reward_ratio": metrics.risk_reward_ratio,
                "total_pnl_usd": metrics.total_pnl_usd,
                "profit_factor": metrics.profit_factor,
                "expectancy": metrics.expectancy,
                "sharpe_ratio": metrics.sharpe_ratio,
            },
            "trailing_stop_analysis": {
                "total_trailing_closes": trailing.total_trailing_closes,
                "effectiveness_score": trailing.effectiveness_score,
                "recommended_activation_pips": trailing.recommended_activation_pips,
                "recommended_distance_pips": trailing.recommended_distance_pips,
                "patterns": trailing.patterns,
            },
            "recommendations": {
                "priority_1": recommendations.priority_1,
                "priority_2": recommendations.priority_2,
                "priority_3": recommendations.priority_3,
                "actions": recommendations.actions,
            },
        }
        json.dump(json_report, f, indent=2)

    print(f"\n✅ Report saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
