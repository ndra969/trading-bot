"""Metrik PF/DD dan laporan per periode (spec 17 Req 2): TS-62..66."""

import math
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import baseline_report as br

SCHEMA = Path(__file__).resolve().parents[2] / "shared" / "schema" / "data_db.sql"
PERIODS = """[IS]
FromDate=2025.10.01
ToDate=2026.07.01
Model=4
[OOS]
FromDate=2026.07.01
ToDate=2026.10.01
Model=4
[ShortHistory]
Symbols=XAUUSDc
"""


def _epoch(y: int, m: int, d: int) -> int:
    return int(datetime(y, m, d, tzinfo=UTC).timestamp())


def test_ts62_profit_factor() -> None:
    assert br.profit_factor(300.0, 200.0, 5) == 1.5
    assert math.isinf(br.profit_factor(300.0, 0.0, 3))
    assert br.profit_factor(0.0, 0.0, 0) is None
    assert br.fmt_pf(None) == "-" and br.fmt_pf(math.inf) == "∞" and br.fmt_pf(1.234) == "1.23"


def test_ts63_max_drawdown_pct() -> None:
    assert round(br.max_drawdown_pct(10000.0, [100.0, -300.0, 50.0, -100.0]), 2) == 3.47
    assert br.max_drawdown_pct(10000.0, []) is None
    assert br.max_drawdown_pct(10000.0, [10.0, 20.0]) == 0.0


def test_ts64_max_drawdown_r() -> None:
    assert br.max_drawdown_r([1.0, -1.0, -1.0, 2.0, -1.0]) == 2.0
    assert br.max_drawdown_r([]) is None


def _db(tmp_path: Path) -> Path:
    """Dua run IS (EURUSDc, XAUUSDc), satu run OOS (EURUSDc), dan satu run acuan IS EURUSDc."""
    path = tmp_path / "t.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    runs = [
        # (session/run, symbol, from, to, [(net, r)])
        (
            1,
            "EURUSDc",
            _epoch(2025, 10, 1),
            _epoch(2026, 6, 30) + 86399,
            [(150.0, 1.5), (-50.0, -1.0)],
        ),  # acuan IS: PF 3.00
        (
            10,
            "EURUSDc",
            _epoch(2025, 10, 1),
            _epoch(2026, 6, 30) + 86399,
            [(200.0, 2.0), (-50.0, -1.0), (-50.0, -1.0)],
        ),
        (
            11,
            "XAUUSDc",
            _epoch(2025, 10, 1),
            _epoch(2026, 6, 27) + 43200,
            [(80.0, 1.0)],
        ),  # tick terakhir 4 hari sebelum ToDate
        (
            12,
            "EURUSDc",
            _epoch(2026, 7, 1),
            _epoch(2026, 9, 30) + 86399,
            [(-60.0, -1.0), (30.0, 0.5)],
        ),
    ]
    sig = 0
    for sid, sym, t0, t1, trades in runs:
        conn.execute(
            "INSERT INTO sessions (id, login, magic, symbol, mode, ea_version, input_hash, inputs_json, started_at, "
            "tester_from, tester_to, run_key) VALUES (?, 1, 2026091901, ?, 'TESTER', '1.19', 'h', '{}', 0, ?, ?, ?)",
            (sid, sym, t0, t1, sid),
        )
        for pos, (net, r) in enumerate(trades, start=1):
            sig += 1
            conn.execute(
                "INSERT INTO signals (id, session_id, login, magic, symbol, time, direction, style, score_total, "
                "spread_points, status) VALUES (?, ?, 1, 2026091901, ?, ?, 'BUY', 'DAY', 40, 5, 'ACCEPTED')",
                (sig, sid, sym, t0 + pos * 3600),
            )
            for c in ("ZONE", "TREND", "PA"):
                conn.execute(
                    "INSERT INTO signal_scores (signal_id, component, score, max_score) VALUES (?, ?, 1, 10)",
                    (sig, c),
                )
            conn.execute(
                "INSERT INTO signal_scores (signal_id, component, score, max_score, active) VALUES (?, 'FIB', 0, 15, 0)",
                (sig,),
            )
            conn.execute(
                "INSERT INTO trades (session_id, login, run_key, position_id, magic, symbol, direction, source, "
                "volume_initial, price_open, sl_initial, tp_initial, signal_id, ea_version, opened_at) "
                "VALUES (?, 1, ?, ?, 2026091901, ?, 'BUY', 'EA', 1, 1, 0.9, 1.2, ?, '1.19', ?)",
                (sid, sid, pos, sym, sig, t0 + pos * 3600),
            )
            conn.execute(
                "INSERT INTO closures (session_id, login, run_key, position_id, magic, symbol, closed_at, reason, "
                "price_close, volume_total, profit, commission, swap, fee, net_profit, r_result, holding_sec, "
                "be_activated, partial_done, trail_activated) VALUES (?, 1, ?, ?, 2026091901, ?, ?, 'SL', 1, 1, ?, 0, 0, 0, ?, ?, 60, 0, 0, 0)",
                (sid, sid, pos, sym, t0 + pos * 3600 + 600, net, net, r),
            )
    conn.commit()
    conn.close()
    return path


def test_ts65_report_per_period_with_compare(tmp_path: Path) -> None:
    db = _db(tmp_path)
    ini = tmp_path / "periods.ini"
    ini.write_text(PERIODS, encoding="utf-8")
    periods, short = br.load_period_file(ini)
    conn = sqlite3.connect(db)
    rep = br.evaluate(
        conn, after_session=9, error_lines=[], min_total=0, min_symbol=0, periods=periods
    )
    ref = br.evaluate(
        conn,
        after_session=0,
        upto_session=1,
        error_lines=[],
        min_total=0,
        min_symbol=0,
        periods=periods,
    )
    conn.close()
    by = {(r.period, r.symbol): r for r in rep.rows}
    assert set(by) == {("IS", "EURUSDc"), ("IS", "XAUUSDc"), ("OOS", "EURUSDc")}
    eu = by[("IS", "EURUSDc")]
    assert eu.profit_factor == 2.0 and round(eu.max_dd_pct, 3) == round(100 * 100 / 10200, 3)
    assert rep.ok  # skor bayangan FIB tidak membuat "skor tidak lengkap"
    text = br.render(rep, ref, ticks={"EURUSDc": ["EURUSDc: generated ticks"]}, short=short)
    assert "== IS ==" in text and "== OOS ==" in text
    assert "PF" in text and "DD%" in text
    assert "XAUUSDc*" in text and "EURUSDc*" in text  # ShortHistory dan tick bermasalah ditandai
    is_block = text.split("== OOS ==")[0]
    assert "2.00" in is_block  # PF IS EURUSDc
    assert "ref PF" in is_block and "3.00" in is_block  # PF acuan IS EURUSDc per (periode, simbol)


def test_ts66_prd_status() -> None:
    lines = br.prd_status(br.Summary(pf=1.4, dd_pct=8.0), br.Summary(pf=0.9, dd_pct=12.0))
    assert "PF IS 1.40 >= 1.3" in lines[0]
    assert any("PF OOS vs IS -36% (batas -30%)" in x for x in lines)
    assert any("DD OOS 12.0% <= 15%" in x for x in lines)
    only_is = br.prd_status(br.Summary(pf=1.1, dd_pct=20.0), None)
    assert any("PF IS 1.10 < 1.3" in x for x in only_is) and any(
        "DD IS 20.0% > 15%" in x for x in only_is
    )


def test_ts65b_trade_count_criteria_only_for_is(tmp_path: Path) -> None:
    db = _db(tmp_path)
    ini = tmp_path / "periods.ini"
    ini.write_text(PERIODS, encoding="utf-8")
    periods, _ = br.load_period_file(ini)
    conn = sqlite3.connect(db)
    # OOS saja (run 12, 2 trade): periode pendek, kriteria jumlah trade tidak berlaku
    oos = br.evaluate(
        conn, after_session=11, error_lines=[], min_total=200, min_symbol=10, periods=periods
    )
    # IS + OOS: kriteria hanya dihitung dari run IS (3 + 1 trade)
    both = br.evaluate(
        conn, after_session=9, error_lines=[], min_total=200, min_symbol=10, periods=periods
    )
    conn.close()
    assert oos.ok
    assert "total trade 4 < 200" in both.problems
    assert not any("run 12" in p for p in both.problems)
    assert any("XAUUSDc (run 11): 1 trade < 10" in p for p in both.problems)
