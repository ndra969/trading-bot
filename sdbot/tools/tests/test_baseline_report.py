"""Laporan backtest dasar (spec 13 Req 8.2): TS-52. DB uji dibuat dari snapshot skema."""

import sqlite3
from pathlib import Path

import baseline_report

SCHEMA = Path(__file__).resolve().parents[2] / "shared" / "schema" / "data_db.sql"


def _db(
    tmp_path: Path,
    trades_per_symbol: dict[str, int],
    *,
    null_signal: bool = False,
    missing_score: bool = False,
) -> Path:
    path = tmp_path / "tester.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    sid = 0
    sig = 1000
    for run, (symbol, n) in enumerate(trades_per_symbol.items(), start=10):
        sid += 1
        conn.execute(
            "INSERT INTO sessions (id, login, magic, symbol, mode, ea_version, input_hash, inputs_json, started_at, run_key) "
            "VALUES (?, 1, 2026091901, ?, 'TESTER', '1.12', 'h', '{}', 0, ?)",
            (sid, symbol, run),
        )
        for pos in range(1, n + 1):
            sig += 1
            for k, status in ((0, "ACCEPTED"), (1, "REJECTED")):
                conn.execute(
                    "INSERT INTO signals (id, session_id, login, magic, symbol, time, direction, style, score_total, "
                    "spread_points, status, reject_stage) VALUES (?, ?, 1, 2026091901, ?, ?, 'BUY', 'DAY', 40, 5, ?, ?)",
                    (
                        sig * 10 + k,
                        sid,
                        symbol,
                        pos * 900 + k,
                        status,
                        None if k == 0 else "NO_PA_TRIGGER",
                    ),
                )
                comps = (
                    ("ZONE", "TREND")
                    if (missing_score and pos == 1 and k == 0)
                    else ("ZONE", "TREND", "PA")
                )
                for c in comps:
                    conn.execute(
                        "INSERT INTO signal_scores VALUES (?, ?, 1, 10)", (sig * 10 + k, c)
                    )
            signal_id = None if (null_signal and pos == 1) else sig * 10
            conn.execute(
                "INSERT INTO trades (session_id, login, run_key, position_id, magic, symbol, direction, source, volume_initial, "
                "price_open, sl_initial, tp_initial, signal_id, ea_version, opened_at) "
                "VALUES (?, 1, ?, ?, 2026091901, ?, 'BUY', 'EA', 0.1, 1.1, 1.09, 1.12, ?, '1.12', 0)",
                (sid, run, pos, symbol, signal_id),
            )
            conn.execute(
                "INSERT INTO closures (session_id, login, run_key, position_id, magic, symbol, closed_at, reason, price_close, "
                "volume_total, profit, commission, swap, fee, net_profit, r_result, holding_sec, be_activated, partial_done, "
                "trail_activated) VALUES (?, 1, ?, ?, 2026091901, ?, 0, 'SL', 1.09, 0.1, -1, 0, 0, 0, -1, ?, 60, 0, 0, 0)",
                (sid, run, pos, symbol, 2.0 if pos % 3 == 0 else -1.0),
            )
    conn.commit()
    conn.close()
    return path


def _eval(path: Path, errors: list[str] | None = None, **kw):
    conn = sqlite3.connect(path)
    try:
        return baseline_report.evaluate(conn, after_session=0, error_lines=errors or [], **kw)
    finally:
        conn.close()


def test_ts52_passes_when_totals_and_telemetry_complete(tmp_path):
    rep = _eval(_db(tmp_path, {"EURUSDc": 6, "XAUUSDc": 5}), min_total=10, min_symbol=5)
    assert rep.ok, rep.problems
    by = {r.symbol: r for r in rep.rows}
    assert by["EURUSDc"].trades == 6 and by["EURUSDc"].candidates == 12
    assert by["EURUSDc"].stages["NO_PA_TRIGGER"] == 6
    assert round(by["EURUSDc"].total_r, 2) == 0.0  # posisi 3 dan 6: 2R; empat lainnya: -1R


def test_ts52_fails_on_symbol_below_minimum_and_total(tmp_path):
    rep = _eval(_db(tmp_path, {"EURUSDc": 6, "XAUUSDc": 2}), min_total=10, min_symbol=5)
    assert not rep.ok
    assert any("XAUUSDc" in p for p in rep.problems)
    assert any("total" in p for p in rep.problems)


def test_ts52_fails_on_missing_signal_id_or_scores(tmp_path):
    rep = _eval(_db(tmp_path, {"EURUSDc": 6}, null_signal=True), min_total=1, min_symbol=1)
    assert not rep.ok and any("signal_id" in p for p in rep.problems)
    other = tmp_path / "b"
    other.mkdir()
    rep = _eval(_db(other, {"EURUSDc": 6}, missing_score=True), min_total=1, min_symbol=1)
    assert not rep.ok and any("skor" in p for p in rep.problems)


def test_ts52_fails_on_error_log_lines(tmp_path):
    path = _db(tmp_path, {"EURUSDc": 6})
    rep = _eval(path, ["[SDB][CRITICAL][Risk][EURUSDc] emergency"], min_total=1, min_symbol=1)
    assert not rep.ok and any("log" in p for p in rep.problems)
    assert _eval(path, ["[SDB][WARN][Signals] histori kurang"], min_total=1, min_symbol=1).ok


def test_ts52_only_sessions_after_marker(tmp_path):
    conn = sqlite3.connect(_db(tmp_path, {"EURUSDc": 6, "XAUUSDc": 5}))
    try:
        rep = baseline_report.evaluate(
            conn, after_session=1, error_lines=[], min_total=1, min_symbol=1
        )
    finally:
        conn.close()
    assert [r.symbol for r in rep.rows] == ["XAUUSDc"]


def test_ts55_defaults_and_compare(tmp_path):
    """Spec 14 Req 5.3: default kriteria Fase 4 200/10; pembanding per simbol dari sesi backtest lain."""
    assert baseline_report.DEFAULT_MIN_TOTAL == 200 and baseline_report.DEFAULT_MIN_SYMBOL == 10
    path = _db(tmp_path, {"EURUSDc": 6, "XAUUSDc": 5})  # sesi 1 = EURUSD, sesi 2 = XAUUSD
    conn = sqlite3.connect(path)
    try:
        ref = baseline_report.evaluate(
            conn, after_session=0, upto_session=1, error_lines=[], min_total=1, min_symbol=1
        )
        cur = baseline_report.evaluate(
            conn, after_session=1, error_lines=[], min_total=1, min_symbol=1
        )
    finally:
        conn.close()
    assert [r.symbol for r in ref.rows] == ["EURUSDc"]
    text = baseline_report.render(cur, ref)
    assert "ref trade" in text and "XAUUSDc" in text
    eur_ref = baseline_report.render(ref, ref)
    assert "6" in eur_ref.splitlines()[2]
