"""Perbandingan trade varian vs acuan (spec 27 Req 3.2): TS-92, TS-93."""

import sqlite3
from pathlib import Path

import pytest
import trade_diff as td

SCHEMA = Path(__file__).resolve().parents[2] / "shared" / "schema" / "data_db.sql"


def _session(conn: sqlite3.Connection, sid: int) -> None:
    conn.execute(
        "INSERT INTO sessions (id, login, magic, symbol, mode, ea_version, input_hash, inputs_json, started_at, "
        "run_key) VALUES (?, 1, 2026091901, 'EURUSDc', 'TESTER', '1.27', 'h', '{}', 0, ?)",
        (sid, sid),
    )


def _trade(
    conn: sqlite3.Connection,
    sid: int,
    pos: int,
    bar: int | None,
    r: float,
    source: str = "EA",
    direction: str = "BUY",
) -> None:
    signal_id = None
    if bar is not None:
        # signal_id beda antar run (memuat run_key), jadi pencocokan wajib lewat simbol + waktu bar + arah.
        signal_id = sid * 1000 + pos
        conn.execute(
            "INSERT INTO signals (id, session_id, login, magic, symbol, time, direction, style, spread_points, "
            "status) VALUES (?, ?, 1, 2026091901, 'EURUSDc', ?, ?, 'DAY', 5, 'ACCEPTED')",
            (signal_id, sid, bar, direction),
        )
    conn.execute(
        "INSERT INTO trades (session_id, login, run_key, position_id, magic, symbol, direction, source, "
        "volume_initial, price_open, sl_initial, tp_initial, signal_id, ea_version, opened_at) "
        "VALUES (?, 1, ?, ?, 2026091901, 'EURUSDc', ?, ?, 1, 1, 0.9, 1.2, ?, '1.27', 0)",
        (sid, sid, pos, direction, source, signal_id),
    )
    conn.execute(
        "INSERT INTO closures (session_id, login, run_key, position_id, magic, symbol, closed_at, reason, "
        "price_close, volume_total, profit, commission, swap, fee, net_profit, r_result, mfe_r, holding_sec, "
        "be_activated, partial_done, trail_activated) "
        "VALUES (?, 1, ?, ?, 2026091901, 'EURUSDc', 0, 'SL', 1, 1, 0, 0, 0, 0, ?, ?, 0, 60, 0, 0, 0)",
        (sid, sid, pos, r * 10, r),
    )


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "t.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    for sid in (1, 2, 3):
        _session(conn, sid)
    # acuan (sesi 1): bar 100 +1, bar 200 -1, bar 300 +2
    _trade(conn, 1, 1, 100, 1.0)
    _trade(conn, 1, 2, 200, -1.0)
    _trade(conn, 1, 3, 300, 2.0)
    # varian (sesi 2): bar 100 +0,5 (sama), bar 200 -1 (sama), bar 400 +1 (baru), bar 300 hilang,
    # bar 200 arah SELL (beda arah = baru), RECONCILED tanpa sinyal (diabaikan)
    _trade(conn, 2, 1, 100, 0.5)
    _trade(conn, 2, 2, 200, -1.0)
    _trade(conn, 2, 3, 400, 1.0)
    _trade(conn, 2, 4, 200, -1.0, direction="SELL")
    _trade(conn, 2, 5, None, 0.3, source="RECONCILED")
    conn.commit()
    conn.close()
    return path


def test_ts92_diff_trades(db: Path) -> None:
    """TS-92: sama 2, baru 2, hilang 1, satu trade tanpa sinyal diabaikan dan dihitung."""
    conn = sqlite3.connect(db)
    d = td.diff_trades(conn, [(1, 1)], [(2, 2)])
    conn.close()
    assert d.same.n == 2
    assert d.same.r_avg == pytest.approx(-0.25)
    assert d.same.base_r_avg == pytest.approx(0.0)
    assert d.new.n == 2
    assert d.new.r_avg == pytest.approx(0.0)
    assert d.lost.n == 1
    assert d.lost.r_avg == pytest.approx(2.0)
    assert d.skipped == 1


def test_ts93_cli_empty_and_missing_table(
    db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """TS-93: rentang tanpa trade -> "-" di laporan; DB tanpa tabel signals -> kode 2."""
    assert td.main(["--db", str(db), "--base", "1-1", "--variant", "kosong=3-3"]) == 0
    out = capsys.readouterr().out
    line = next(ln for ln in out.splitlines() if ln.startswith("kosong"))
    assert "-" in line
    assert line.split()[1] == "0"

    bare = tmp_path / "bare.sqlite"
    sqlite3.connect(bare).close()
    assert td.main(["--db", str(bare), "--base", "1-1", "--variant", "v=2-2"]) == 2
