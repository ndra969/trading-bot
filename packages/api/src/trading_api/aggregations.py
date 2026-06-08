"""Pure aggregation helpers for the analytics endpoints.

Kept dependency-free (operate on plain dicts) so they're unit-testable without
a DB and reused across routers. A "trade" dict has at least: ``pnl`` (float),
``confluence`` (float), plus optional ``market_session`` and ``breakdown``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable


def _wins(trades: list[dict]) -> int:
    return sum(1 for t in trades if (t.get("pnl") or 0) > 0)


def group_stats(trades: Iterable[dict], key_fn: Callable[[dict], str | None]) -> list[dict]:
    """Group trades by ``key_fn`` → per-group count / win-rate / P&L / confluence.

    Rows are sorted by total_pnl ascending (worst first — what tuning cares about).
    Trades whose key is None are bucketed under "unknown".
    """
    groups: dict[str, list[dict]] = {}
    for t in trades:
        key = key_fn(t) or "unknown"
        groups.setdefault(key, []).append(t)

    rows = []
    for key, ts in groups.items():
        n = len(ts)
        wins = _wins(ts)
        total = sum(t.get("pnl") or 0 for t in ts)
        confs = [t["confluence"] for t in ts if t.get("confluence") is not None]
        rows.append(
            {
                "key": key,
                "count": n,
                "wins": wins,
                "win_rate": round(wins / n * 100, 1) if n else 0.0,
                "total_pnl": round(total, 2),
                "avg_pnl": round(total / n, 2) if n else 0.0,
                "avg_confluence": round(sum(confs) / len(confs), 1) if confs else 0.0,
            }
        )
    rows.sort(key=lambda r: r["total_pnl"])
    return rows


def confluence_buckets(trades: Iterable[dict], width: int = 10) -> list[dict]:
    """Histogram of confluence with win-rate + avg P&L per bucket (0..100)."""
    buckets: dict[int, list[dict]] = {}
    for t in trades:
        c = t.get("confluence")
        if c is None:
            continue
        lo = min(int(c // width) * width, 100 - width)
        lo = max(lo, 0)
        buckets.setdefault(lo, []).append(t)

    out = []
    for lo in range(0, 100, width):
        ts = buckets.get(lo, [])
        n = len(ts)
        wins = _wins(ts)
        total = sum(t.get("pnl") or 0 for t in ts)
        out.append(
            {
                "bucket": f"{lo}-{lo + width}",
                "lower": float(lo),
                "upper": float(lo + width),
                "count": n,
                "wins": wins,
                "win_rate": round(wins / n * 100, 1) if n else 0.0,
                "avg_pnl": round(total / n, 2) if n else 0.0,
            }
        )
    return out


def percentiles(values: list[float]) -> tuple[float | None, float | None, float | None]:
    """(min, p50, max) of a value list (None when empty)."""
    if not values:
        return None, None, None
    s = sorted(values)
    p50 = s[len(s) // 2]
    return round(s[0], 1), round(p50, 1), round(s[-1], 1)


def equity_curve(trades: list[dict]) -> list[dict]:
    """Cumulative realized P&L ordered by close_time."""
    ordered = sorted((t for t in trades if t.get("close_time")), key=lambda t: t["close_time"])
    cum = 0.0
    out = []
    for t in ordered:
        cum += t.get("pnl") or 0
        out.append({"close_time": t["close_time"], "cumulative_pnl": round(cum, 2)})
    return out


def layer_contribution(trades: list[dict]) -> tuple[list[dict], float, int]:
    """Per-layer participation rate + avg raw confidence, from breakdowns.

    Returns (rows, coverage, sample) where coverage = fraction of trades that
    carried a breakdown and sample = number of such trades.
    """
    with_bd = [t for t in trades if isinstance(t.get("breakdown"), dict)]
    sample = len(with_bd)
    coverage = round(sample / len(trades), 3) if trades else 0.0

    fired: dict[str, list[float]] = {}
    for t in with_bd:
        raw = t["breakdown"].get("raw_confidences", {}) or {}
        for layer, conf in raw.items():
            fired.setdefault(layer, []).append(float(conf))

    rows = [
        {
            "layer": layer,
            "participation_rate": round(len(confs) / sample, 3) if sample else 0.0,
            "avg_contribution": round(sum(confs) / len(confs), 1) if confs else 0.0,
        }
        for layer, confs in fired.items()
    ]
    rows.sort(key=lambda r: r["participation_rate"], reverse=True)
    return rows, coverage, sample
