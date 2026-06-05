"""Unit tests for the pure analytics aggregation helpers."""

from trading_api import aggregations as agg


def _t(pnl, conf, **extra):
    return {"pnl": pnl, "confluence": conf, **extra}


def test_group_stats_winrate_and_sort():
    trades = [
        _t(10, 60, asset_class="forex_major"),
        _t(-5, 40, asset_class="forex_major"),
        _t(-20, 50, asset_class="commodities"),
    ]
    rows = agg.group_stats(trades, lambda t: t.get("asset_class"))
    # sorted worst total_pnl first
    assert rows[0]["key"] == "commodities"
    assert rows[0]["total_pnl"] == -20.0
    fx = next(r for r in rows if r["key"] == "forex_major")
    assert fx["count"] == 2 and fx["wins"] == 1 and fx["win_rate"] == 50.0
    assert fx["avg_confluence"] == 50.0


def test_group_stats_none_key_is_unknown():
    rows = agg.group_stats([_t(1, 50)], lambda t: t.get("market_session"))
    assert rows[0]["key"] == "unknown"


def test_confluence_buckets_span_full_range():
    buckets = agg.confluence_buckets([_t(5, 66), _t(-5, 61)])
    assert len(buckets) == 10  # 0-10 .. 90-100
    b60 = next(b for b in buckets if b["bucket"] == "60-70")
    assert b60["count"] == 2 and b60["wins"] == 1 and b60["win_rate"] == 50.0


def test_percentiles():
    assert agg.percentiles([]) == (None, None, None)
    lo, p50, hi = agg.percentiles([10.0, 30.0, 20.0])
    assert (lo, hi) == (10.0, 30.0)


def test_equity_curve_is_cumulative_in_time_order():
    from datetime import datetime

    trades = [
        _t(10, 50, close_time=datetime(2026, 6, 2)),
        _t(-4, 50, close_time=datetime(2026, 6, 1)),
    ]
    curve = agg.equity_curve(trades)
    assert [round(p["cumulative_pnl"], 1) for p in curve] == [-4.0, 6.0]


def test_layer_contribution_and_coverage():
    trades = [
        _t(1, 50, breakdown={"raw_confidences": {"ma": 50.0, "price_action": 70.0}}),
        _t(1, 50, breakdown={"raw_confidences": {"ma": 30.0}}),
        _t(1, 50),  # no breakdown
    ]
    rows, coverage, sample = agg.layer_contribution(trades)
    assert sample == 2
    assert coverage == round(2 / 3, 3)
    ma = next(r for r in rows if r["layer"] == "ma")
    assert ma["participation_rate"] == 1.0  # fired in both sampled
    assert ma["avg_contribution"] == 40.0
    pa = next(r for r in rows if r["layer"] == "price_action")
    assert pa["participation_rate"] == 0.5
