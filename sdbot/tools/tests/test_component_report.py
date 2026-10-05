"""Laporan per nilai komponen skor (spec 17 Req 3): TS-67..69."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import component_report as cr

SCHEMA = Path(__file__).resolve().parents[2] / "shared" / "schema" / "data_db.sql"
PERIODS = "[IS]\nFromDate=2025.10.01\nToDate=2026.07.01\nModel=4\n[OOS]\nFromDate=2026.07.01\nToDate=2026.10.01\nModel=4\n"


def _g(score: float, n: int, wins: int, total_r: float) -> cr.Group:
    return cr.Group("FIB", False, score, n, wins, total_r)


def test_ts67_verdict() -> None:
    better_is = [_g(0, 30, 12, -3.0), _g(8, 25, 12, 0.0), _g(15, 22, 13, 4.4)]
    better_oos = [_g(0, 21, 9, -2.1), _g(15, 20, 11, 2.0)]
    assert cr.verdict(better_is, better_oos) == "TERBUKTI"
    worse_oos = [_g(0, 21, 11, 2.1), _g(15, 20, 9, -2.0)]
    assert cr.verdict(better_is, worse_oos) == "TIDAK"
    small = [_g(0, 12, 6, 0.0), _g(15, 30, 16, 3.0)]
    assert cr.verdict(better_is, small) == "SAMPEL KURANG"
    no_zero = [_g(8, 40, 20, 1.0), _g(15, 40, 22, 3.0)]  # EC-07: komponen selalu bernilai
    assert cr.verdict(no_zero, no_zero) == "SAMPEL KURANG"
    assert cr.verdict(better_is, []) == "SAMPEL KURANG"


def _epoch(y: int, m: int, d: int) -> int:
    return int(datetime(y, m, d, tzinfo=UTC).timestamp())


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "t.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    runs = [
        (1, _epoch(2025, 10, 1), _epoch(2026, 6, 30) + 86399),
        (2, _epoch(2026, 7, 1), _epoch(2026, 9, 30) + 86399),
    ]
    sig = 0
    for sid, t0, t1 in runs:
        conn.execute(
            "INSERT INTO sessions (id, login, magic, symbol, mode, ea_version, input_hash, inputs_json, started_at, "
            "tester_from, tester_to, run_key) VALUES (?, 1, 2026091901, 'EURUSDc', 'TESTER', '1.19', 'h', '{}', 0, ?, ?, ?)",
            (sid, t0, t1, sid),
        )
        # ACCEPTED dengan trade: ZONE 30 menang, ZONE 15 kalah; FIB bayangan 15 menang / 0 kalah
        for pos, (zone, fib, r) in enumerate(
            [(30, 15, 2.0), (15, 0, -1.0), (30, 15, 1.0)], start=1
        ):
            sig += 1
            conn.execute(
                "INSERT INTO signals (id, session_id, login, magic, symbol, time, direction, style, score_total, "
                "spread_points, status) VALUES (?, ?, 1, 2026091901, 'EURUSDc', ?, 'BUY', 'DAY', 40, 5, 'ACCEPTED')",
                (sig, sid, t0 + pos * 3600),
            )
            for comp, score, mx, act in (
                ("ZONE", zone, 30, 1),
                ("TREND", 7, 15, 1),
                ("PA", 7, 10, 1),
                ("FIB", fib, 15, 0),
            ):
                conn.execute(
                    "INSERT INTO signal_scores (signal_id, component, score, max_score, active) VALUES (?, ?, ?, ?, ?)",
                    (sig, comp, score, mx, act),
                )
            conn.execute(
                "INSERT INTO trades (session_id, login, run_key, position_id, magic, symbol, direction, source, "
                "volume_initial, price_open, sl_initial, tp_initial, signal_id, ea_version, opened_at) "
                "VALUES (?, 1, ?, ?, 2026091901, 'EURUSDc', 'BUY', 'EA', 1, 1, 0.9, 1.2, ?, '1.19', ?)",
                (sid, sid, pos, sig, t0 + pos * 3600),
            )
            conn.execute(
                "INSERT INTO closures (session_id, login, run_key, position_id, magic, symbol, closed_at, reason, "
                "price_close, volume_total, profit, commission, swap, fee, net_profit, r_result, holding_sec, "
                "be_activated, partial_done, trail_activated) VALUES (?, 1, ?, ?, 2026091901, 'EURUSDc', ?, 'SL', 1, 1, 0, 0, 0, 0, ?, ?, 60, 0, 0, 0)",
                (sid, sid, pos, t0 + pos * 3600 + 600, r * 10, r),
            )
        # kandidat ditolak tanpa trade
        sig += 1
        conn.execute(
            "INSERT INTO signals (id, session_id, login, magic, symbol, time, direction, style, score_total, "
            "spread_points, status, reject_stage) VALUES (?, ?, 1, 2026091901, 'EURUSDc', ?, 'BUY', 'DAY', 20, 5, 'REJECTED', 'NO_PA_TRIGGER')",
            (sig, sid, t0 + 99 * 3600),
        )
        for comp, score, act in (("ZONE", 15, 1), ("FIB", 8, 0)):
            conn.execute(
                "INSERT INTO signal_scores (signal_id, component, score, max_score, active) VALUES (?, ?, ?, 15, ?)",
                (sig, comp, score, act),
            )
    conn.commit()
    conn.close()
    return path


def test_ts68_shadow_component_grouped_per_period(tmp_path: Path) -> None:
    db = _db(tmp_path)
    ini = tmp_path / "p.ini"
    ini.write_text(PERIODS, encoding="utf-8")
    conn = sqlite3.connect(db)
    groups = cr.group_trades(conn, 0, 10, cr.load_periods(ini)[0])
    conn.close()
    fib_is = {g.score: g for g in groups[("FIB", "IS")]}
    assert (
        set(fib_is) == {0.0, 15.0}
        and fib_is[15.0].n == 2
        and fib_is[15.0].total_r == 3.0
        and not fib_is[15.0].active
    )
    assert {g.score: g.n for g in groups[("ZONE", "OOS")]} == {15.0: 1, 30.0: 2}
    assert all(g.active for g in groups[("ZONE", "IS")])
    text = cr.render(groups, min_n=20)
    assert "FIB (bayangan)" in text and "ZONE (aktif)" in text
    assert "sampel kecil" in text and "SAMPEL KURANG" in text


def test_ts69_candidates_distribution(tmp_path: Path) -> None:
    db = _db(tmp_path)
    conn = sqlite3.connect(db)
    dist = cr.candidate_distribution(conn, 0, 10)
    conn.close()
    assert dist[("FIB", "ACCEPTED")] == {15.0: 4, 0.0: 2}
    assert dist[("FIB", "NO_PA_TRIGGER")] == {8.0: 2}
    text = cr.render_candidates(dist)
    assert "NO_PA_TRIGGER" in text and "FIB" in text
