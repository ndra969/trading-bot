"""Laporan alasan tutup per rentang sesi (spec 24 Req 1.2, 2.2): TS-84..87."""

import sqlite3
from pathlib import Path

import exit_report as er
import pytest

SCHEMA = Path(__file__).resolve().parents[2] / "shared" / "schema" / "data_db.sql"


def _session(conn: sqlite3.Connection, sid: int) -> None:
    conn.execute(
        "INSERT INTO sessions (id, login, magic, symbol, mode, ea_version, input_hash, inputs_json, started_at, "
        "run_key) VALUES (?, 1, 2026091901, 'EURUSDc', 'TESTER', '1.25', 'h', '{}', 0, ?)",
        (sid, sid),
    )


def _trade(conn: sqlite3.Connection, sid: int, pos: int, reason: str, r: float, mfe: float) -> None:
    conn.execute(
        "INSERT INTO trades (session_id, login, run_key, position_id, magic, symbol, direction, source, "
        "volume_initial, price_open, sl_initial, tp_initial, ea_version, opened_at) "
        "VALUES (?, 1, ?, ?, 2026091901, 'EURUSDc', 'BUY', 'EA', 1, 1, 0.9, 1.2, '1.25', 0)",
        (sid, sid, pos),
    )
    conn.execute(
        "INSERT INTO closures (session_id, login, run_key, position_id, magic, symbol, closed_at, reason, "
        "price_close, volume_total, profit, commission, swap, fee, net_profit, r_result, mfe_r, holding_sec, "
        "be_activated, partial_done, trail_activated) "
        "VALUES (?, 1, ?, ?, 2026091901, 'EURUSDc', ?, ?, 1, 1, 0, 0, 0, 0, ?, ?, ?, 60, 0, 0, 0)",
        (sid, sid, pos, pos * 60, reason, r * 10, r, mfe),
    )


def _event(conn: sqlite3.Connection, sid: int, pos: int, kind: str) -> None:
    conn.execute(
        "INSERT INTO position_events (session_id, login, position_id, time, type, volume, price, spread_points, "
        "run_key) VALUES (?, 1, ?, 0, ?, 1, 1, 5, ?)",
        (sid, pos, kind, sid),
    )


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "t.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    for sid in (1, 2, 3):
        _session(conn, sid)
    # sesi 1: 2 SL (satu MFE 0,6), 1 BE_STOP, 1 TRAIL_STOP, 1 TP
    for pos, (reason, r, mfe) in enumerate(
        [
            ("SL", -1.0, 0.6),
            ("SL", -1.0, 0.2),
            ("BE_STOP", 0.2, 1.1),
            ("TRAIL_STOP", 1.0, 2.0),
            ("TP", 2.0, 2.0),
        ],
        start=1,
    ):
        _trade(conn, 1, pos, reason, r, mfe)
    _trade(conn, 2, 1, "TP", 2.0, 2.0)
    _trade(conn, 3, 1, "SL", -1.0, 0.0)
    _event(conn, 1, 1, "MODIFY_FAILED")
    _event(conn, 2, 1, "MODIFY_FAILED")
    _event(conn, 3, 1, "MODIFY_FAILED")
    _event(conn, 1, 3, "BE")
    conn.commit()
    conn.close()
    return path


def test_ts84_reasons_and_mfe(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        s = er.exit_summary(conn, [(1, 1)])
    assert s.trades == 5
    assert s.total_r == pytest.approx(1.2)
    assert s.r_per_trade == pytest.approx(0.24)
    assert s.reasons["SL"] == (2, pytest.approx(-1.0))
    assert s.reasons["BE_STOP"] == (1, pytest.approx(0.2))
    assert s.reasons["TRAIL_STOP"] == (1, pytest.approx(1.0))
    assert s.reasons["TP"] == (1, pytest.approx(2.0))
    assert s.sl_mfe_half == 1
    assert s.pf == pytest.approx(32.0 / 20.0)


def test_ts85_multiple_ranges(db: Path) -> None:
    assert er.parse_runs(["a=1-1,2-2", "b=3-3"]) == [("a", [(1, 1), (2, 2)]), ("b", [(3, 3)])]
    with sqlite3.connect(db) as conn:
        s = er.exit_summary(conn, [(1, 1), (2, 2)])
    assert s.trades == 6
    assert s.reasons["TP"] == (2, pytest.approx(2.0))


def test_ts86_modify_failed(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        assert er.exit_summary(conn, [(1, 2)]).modify_failed == 2
        assert er.exit_summary(conn, [(3, 3)]).modify_failed == 1


def test_ts87_bad_format_and_empty(db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for bad in (["tanpa_sama"], ["a=1"], ["a=x-2"], ["a=5-1"]):
        with pytest.raises(ValueError):
            er.parse_runs(bad)
    assert er.main(["--db", str(db), "--runs", "rusak"]) == 2
    with sqlite3.connect(db) as conn:
        empty = er.exit_summary(conn, [(50, 60)])
    assert empty.trades == 0 and empty.r_per_trade is None and empty.pf is None
    assert er.main(["--db", str(db), "--runs", "a=1-1", "--runs", "kosong=50-60"]) == 0
    out = capsys.readouterr().out
    assert "kosong" in out and "a" in out
    assert er.main(["--db", str(db.parent / "tidak_ada.sqlite"), "--runs", "a=1-1"]) == 1
