"""
Compare Backtest Results - Before vs After Week 15.5 Fixes

Generates comprehensive comparison report showing improvement metrics.

Usage:
    uv run python scripts/compare_backtest_results.py \
        --before backtest_before_fixes.json \
        --after backtest_after_fixes.json \
        --output backtest_comparison_report.txt
"""

import argparse
import json
from pathlib import Path
from typing import Dict


def load_results(filepath: str) -> Dict:
    """Load backtest results from JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def calculate_improvement(before: float, after: float, is_lower_better: bool = False) -> float:
    """Calculate improvement percentage."""
    if before == 0:
        return 0.0

    if is_lower_better:
        # For metrics where lower is better (losses, drawdown)
        improvement = ((before - after) / abs(before)) * 100
    else:
        # For metrics where higher is better (win rate, profit)
        improvement = ((after - before) / abs(before)) * 100

    return improvement


def generate_comparison_report(before_results: Dict, after_results: Dict, output_file: str) -> None:
    """
    Generate comprehensive comparison report.

    Args:
        before_results: Baseline results dictionary
        after_results: Improved results dictionary
        output_file: Output report filename
    """
    print("=" * 80)
    print("[COMPARISON] BACKTEST COMPARISON REPORT - Week 15.5 Fixes Validation")
    print("=" * 80)
    print()

    # Build report content
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("[COMPARISON] BACKTEST COMPARISON REPORT")
    report_lines.append("Week 15.5 Performance Fixes - Before vs After")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Period info
    report_lines.append(f"Period: {before_results.get('period', 'N/A')}")
    report_lines.append(f"Symbols: {', '.join(before_results.get('symbols', []))}")
    report_lines.append("")

    # Win Rate Comparison
    before_wr = before_results.get("win_rate", 0)
    after_wr = after_results.get("win_rate", 0)
    wr_improvement = calculate_improvement(before_wr, after_wr)

    report_lines.append("[WIN RATE]")
    report_lines.append(f"  Before: {before_wr:.2f}%")
    report_lines.append(f"  After:  {after_wr:.2f}%")
    report_lines.append(
        f"  Change: +{wr_improvement:.2f}% ({after_wr - before_wr:+.2f} percentage points)"
    )
    report_lines.append(
        f"  Target: 50%+ -> {'[OK] ACHIEVED' if after_wr >= 50 else '[NO] NOT YET'}"
    )
    report_lines.append("")

    # Risk:Reward Comparison
    before_rr = before_results.get("risk_reward_ratio", 0)
    after_rr = after_results.get("risk_reward_ratio", 0)
    rr_improvement = calculate_improvement(before_rr, after_rr)

    report_lines.append("[RISK:REWARD RATIO]")
    report_lines.append(f"  Before: {before_rr:.2f}:1")
    report_lines.append(f"  After:  {after_rr:.2f}:1")
    report_lines.append(f"  Change: +{rr_improvement:.2f}% ({after_rr - before_rr:+.2f})")
    report_lines.append(
        f"  Target: 2:1+ -> {'[OK] ACHIEVED' if after_rr >= 2.0 else '[NO] NOT YET'}"
    )
    report_lines.append("")

    # Profit Factor Comparison
    before_pf = before_results.get("profit_factor", 0)
    after_pf = after_results.get("profit_factor", 0)
    pf_improvement = calculate_improvement(before_pf, after_pf)

    report_lines.append("[PROFIT FACTOR]")
    report_lines.append(f"  Before: {before_pf:.2f}")
    report_lines.append(f"  After:  {after_pf:.2f}")
    report_lines.append(f"  Change: +{pf_improvement:.2f}%")
    report_lines.append(
        f"  Target: 1.5+ -> {'[OK] ACHIEVED' if after_pf >= 1.5 else '[NO] NOT YET'}"
    )
    report_lines.append("")

    # P&L Comparison
    before_pnl = before_results.get("total_pnl", 0)
    after_pnl = after_results.get("total_pnl", 0)
    pnl_change = after_pnl - before_pnl

    report_lines.append("[TOTAL P&L]")
    report_lines.append(f"  Before: ${before_pnl:.2f}")
    report_lines.append(f"  After:  ${after_pnl:.2f}")
    report_lines.append(f"  Change: ${pnl_change:+.2f}")
    report_lines.append(f"  Status: {'[OK] POSITIVE' if after_pnl > 0 else '[WARN] NEGATIVE'}")
    report_lines.append("")

    # Average Win/Loss Comparison
    before_avg_win = before_results.get("avg_win_pips", 0)
    after_avg_win = after_results.get("avg_win_pips", 0)
    before_avg_loss = before_results.get("avg_loss_pips", 0)
    after_avg_loss = after_results.get("avg_loss_pips", 0)

    report_lines.append("[AVERAGE WIN/LOSS]")
    report_lines.append(f"  Average Win:")
    report_lines.append(f"    Before: +{before_avg_win:.2f} pips")
    report_lines.append(f"    After:  +{after_avg_win:.2f} pips")
    report_lines.append(f"    Change: {after_avg_win - before_avg_win:+.2f} pips")
    report_lines.append(f"  Average Loss:")
    report_lines.append(f"    Before: {before_avg_loss:.2f} pips")
    report_lines.append(f"    After:  {after_avg_loss:.2f} pips")
    report_lines.append(f"    Change: {after_avg_loss - before_avg_loss:+.2f} pips")
    report_lines.append("")

    # Trade Count Comparison
    before_trades = before_results.get("total_trades", 0)
    after_trades = after_results.get("total_trades", 0)

    report_lines.append("[TRADE COUNT]")
    report_lines.append(f"  Before: {before_trades} trades")
    report_lines.append(f"  After:  {after_trades} trades")
    report_lines.append(f"  Change: {after_trades - before_trades:+d} trades")
    report_lines.append(f"  Note: Fewer trades expected due to stricter filters (higher quality)")
    report_lines.append("")

    # Risk Exposure Comparison
    if "max_risk_old" in after_results:
        max_risk_old = after_results.get("max_risk_old", 0)
        max_risk_new = after_results.get("max_risk_new", 0)
        risk_reduction = after_results.get("risk_reduction_percent", 0)

        report_lines.append("[RISK EXPOSURE]")
        report_lines.append(f"  Old System: ${max_risk_old:.0f} max exposure (1% × 5 positions)")
        report_lines.append(f"  New System: ${max_risk_new:.0f} max exposure (0.5% × 3 positions)")
        report_lines.append(f"  Reduction: {risk_reduction:.0f}% safer")
        report_lines.append("")

    # Drawdown Comparison
    before_dd = before_results.get("max_drawdown_usd", 0)
    after_dd = after_results.get("max_drawdown_usd", 0)
    dd_improvement = calculate_improvement(before_dd, after_dd, is_lower_better=True)

    report_lines.append("[MAX DRAWDOWN]")
    report_lines.append(f"  Before: ${before_dd:.2f}")
    report_lines.append(f"  After:  ${after_dd:.2f}")
    report_lines.append(f"  Improvement: {dd_improvement:.2f}% (lower is better)")
    report_lines.append("")

    # Summary
    report_lines.append("=" * 80)
    report_lines.append("[SUMMARY] Week 15.5 Fixes Effectiveness")
    report_lines.append("=" * 80)

    targets_met = 0
    total_targets = 3

    if after_wr >= 50:
        report_lines.append("[OK] Win Rate Target (50%+): ACHIEVED")
        targets_met += 1
    else:
        report_lines.append(f"[NO] Win Rate Target (50%+): NOT YET ({after_wr:.2f}%)")

    if after_rr >= 2.0:
        report_lines.append("[OK] Risk:Reward Target (2:1+): ACHIEVED")
        targets_met += 1
    else:
        report_lines.append(f"[NO] Risk:Reward Target (2:1+): NOT YET ({after_rr:.2f}:1)")

    if after_pf >= 1.5:
        report_lines.append("[OK] Profit Factor Target (1.5+): ACHIEVED")
        targets_met += 1
    else:
        report_lines.append(f"[NO] Profit Factor Target (1.5+): NOT YET ({after_pf:.2f})")

    report_lines.append("")
    report_lines.append(f"Overall: {targets_met}/{total_targets} targets achieved")
    report_lines.append("")

    if targets_met == total_targets:
        report_lines.append("[SUCCESS] ALL TARGETS ACHIEVED - Week 15.5 fixes are EFFECTIVE!")
        report_lines.append("[OK] System is ready for live trading validation")
    elif targets_met >= 2:
        report_lines.append("[WARN] MOST TARGETS ACHIEVED - Significant improvement!")
        report_lines.append("[WAIT] Minor adjustments may be needed")
    else:
        report_lines.append("[FAIL] TARGETS NOT MET - Further optimization required")
        report_lines.append("[FIX] Review and adjust parameters")

    report_lines.append("")
    report_lines.append("=" * 80)

    # Print to console
    for line in report_lines:
        print(line)

    # Save to file
    output_path = Path(output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print()
    print(f"[SAVED] Comparison report saved: {output_path}")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compare backtest results")
    parser.add_argument(
        "--before", default="backtest_before_fixes.json", help="Before fixes results"
    )
    parser.add_argument("--after", default="backtest_after_fixes.json", help="After fixes results")
    parser.add_argument(
        "--output", default="backtest_comparison_report.txt", help="Output report file"
    )

    args = parser.parse_args()

    # Load results
    before_path = Path(args.before)
    after_path = Path(args.after)

    if not before_path.exists():
        print(f"[ERROR] Before results not found: {before_path}")
        print("Run: uv run python scripts/backtest_current_system.py")
        return 1

    if not after_path.exists():
        print(f"[ERROR] After results not found: {after_path}")
        print("Run: uv run python scripts/backtest_with_fixes.py")
        return 1

    before_results = load_results(args.before)
    after_results = load_results(args.after)

    # Generate comparison
    generate_comparison_report(before_results, after_results, args.output)

    return 0


if __name__ == "__main__":
    exit(main())
