"""Skema v2: run_key memisahkan run backtest di sdbot_tester.sqlite (spec 04 task 7, keputusan PC-08).

Di tester, position ID dan deal ticket mulai dari angka kecil yang sama di setiap run, dengan login
yang sama. Kunci unik (login, position_id) membuat baris run berikutnya dibuang ON CONFLICT DO NOTHING.
"""

import sqlite3
from pathlib import Path

import schema

TRADE_SQL = (
    "INSERT INTO trades (session_id, login, run_key, position_id, magic, symbol, direction, source,"
    " volume_initial, price_open, sl_initial, tp_initial, ea_version, opened_at)"
    " VALUES (?,?,?,?,2026091900,'EURUSDc','BUY','EA',0.01,1.1,1.09,1.12,'1.03',1)"
    " ON CONFLICT (login, run_key, position_id) DO NOTHING"
)


def _latest(real_schema_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    schema.apply_migrations(conn, schema.load_migrations(real_schema_dir / "migrations" / "data"))
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> dict[str, tuple]:
    return {r[1]: r for r in conn.execute(f"PRAGMA table_info({table})")}


def test_ts20_run_key_column_defaults_to_zero(real_schema_dir: Path):
    conn = _latest(real_schema_dir)
    for table in ("sessions", "trades", "deals", "closures", "balance_ops", "position_events"):
        col = _columns(conn, table).get("run_key")
        assert col is not None, f"{table}.run_key tidak ada"
        assert col[3] == 1 and col[4] == "0", f"{table}.run_key harus NOT NULL DEFAULT 0"


def test_ts21_same_position_in_two_runs_keeps_both_rows(real_schema_dir: Path):
    conn = _latest(real_schema_dir)
    conn.execute(TRADE_SQL, (1, 12345, 1, 2))
    conn.execute(TRADE_SQL, (2, 12345, 2, 2))
    assert conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == 2


def test_ts22_same_run_stays_idempotent(real_schema_dir: Path):
    conn = _latest(real_schema_dir)
    conn.execute(TRADE_SQL, (1, 12345, 0, 7))
    conn.execute(TRADE_SQL, (5, 12345, 0, 7))  # live: sesi baru setelah restart, posisi sama
    assert conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == 1


def test_ts23_deals_and_balance_ops_are_unique_per_run(real_schema_dir: Path):
    conn = _latest(real_schema_dir)
    deal = (
        "INSERT INTO deals (session_id, login, run_key, deal_ticket, position_id, magic, symbol, time, entry,"
        " deal_type, volume, price, reason, profit, commission, swap, fee)"
        " VALUES (1,12345,?,3,2,2026091900,'EURUSDc',1,'IN','BUY',0.01,1.1,'EXPERT',0,0,0,0)"
        " ON CONFLICT (login, run_key, deal_ticket) DO NOTHING"
    )
    bal = (
        "INSERT INTO balance_ops (login, run_key, deal_ticket, time, op_type, amount)"
        " VALUES (12345,?,1,1,'BALANCE',10000) ON CONFLICT (login, run_key, deal_ticket) DO NOTHING"
    )
    for key in (1, 2, 2):
        conn.execute(deal, (key,))
        conn.execute(bal, (key,))
    assert conn.execute("SELECT COUNT(*) FROM deals").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM balance_ops").fetchone()[0] == 2


def test_ts24_view_joins_closure_of_the_same_run(real_schema_dir: Path):
    conn = _latest(real_schema_dir)
    conn.execute(TRADE_SQL, (1, 12345, 1, 2))
    conn.execute(TRADE_SQL, (2, 12345, 2, 2))
    conn.execute(
        "INSERT INTO closures (session_id, login, run_key, position_id, magic, symbol, closed_at, reason,"
        " price_close, volume_total, profit, commission, swap, fee, net_profit, holding_sec,"
        " be_activated, partial_done, trail_activated)"
        " VALUES (2,12345,2,2,2026091900,'EURUSDc',5,'TP',1.12,0.01,20,0,0,0,20,4,0,0,0)"
    )
    rows = conn.execute("SELECT run_key, reason FROM v_trade_results ORDER BY run_key").fetchall()
    assert rows == [(1, None), (2, "TP")]
