"""Skema v3: kunci notifikasi dan alasan status di alerts (spec 08 task 1, keputusan PC-13).

Notifier melaporkan hasil kirim sebelum baris alert pasti sudah di-flush, jadi Logger memperbarui
baris lewat notify_key, bukan ID baris. status_reason menyimpan alasan SKIPPED/FAILED.
"""

import sqlite3
from pathlib import Path

import schema

FIXTURE = Path(__file__).resolve().parents[2] / "shared" / "schema" / "fixtures"


def _migrations(real_schema_dir: Path) -> list:
    return schema.load_migrations(real_schema_dir / "migrations" / "data")


def _latest(real_schema_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    schema.apply_migrations(conn, _migrations(real_schema_dir))
    return conn


def test_ts30_alerts_has_notify_key_status_reason_and_index(real_schema_dir: Path):
    conn = _latest(real_schema_dir)
    cols = {r[1]: r for r in conn.execute("PRAGMA table_info(alerts)")}
    assert "notify_key" in cols and cols["notify_key"][2] == "TEXT"
    assert "status_reason" in cols and cols["status_reason"][2] == "TEXT"
    idx = {r[1] for r in conn.execute("PRAGMA index_list(alerts)")}
    assert "ix_alerts_login_key" in idx
    key_cols = [r[2] for r in conn.execute("PRAGMA index_info(ix_alerts_login_key)")]
    assert key_cols == ["login", "notify_key"]


def test_ts30_status_update_by_notify_key(real_schema_dir: Path):
    conn = _latest(real_schema_dir)
    conn.execute(
        "INSERT INTO alerts (session_id, login, magic, symbol, time, type, severity, message, status,"
        " attempts, notify_key) VALUES (1, 12345, 2026091901, 'EURUSDc', 1, 'CONN_DOWN', 'MEDIUM',"
        " 'x', 'PENDING', 0, '2026091901-1-2-7')"
    )
    conn.execute(
        "UPDATE alerts SET status = 'SKIPPED', status_reason = 'COOLDOWN'"
        " WHERE login = 12345 AND notify_key = '2026091901-1-2-7'"
    )
    assert conn.execute("SELECT status, status_reason FROM alerts").fetchone() == (
        "SKIPPED",
        "COOLDOWN",
    )


def test_ts31_existing_rows_get_row_key_on_upgrade(real_schema_dir: Path):
    migs = _migrations(real_schema_dir)
    v3 = [m for m in migs if m.version == 3]
    assert v3, "migrasi 0003 tidak ada"
    seed = schema.load_seed(real_schema_dir / "migrations" / "data" / "seed_sample.sql")
    conn = sqlite3.connect(":memory:")
    schema.apply_migrations(conn, [m for m in migs if m.version <= 2])
    conn.executescript(seed[1])
    conn.executescript(seed[2])
    schema.apply_migrations(conn, v3)
    rows = conn.execute("SELECT id, notify_key FROM alerts ORDER BY id").fetchall()
    assert rows and all(key == f"row-{rid}" for rid, key in rows)


def test_ts31_seed_v3_has_trade_and_skipped_rows():
    conn = sqlite3.connect(
        f"file:{(FIXTURE / 'data_latest_sample.sqlite').as_posix()}?mode=ro", uri=True
    )
    try:
        types = {r[0] for r in conn.execute("SELECT type FROM alerts WHERE notify_key IS NOT NULL")}
        reasons = {r[0] for r in conn.execute("SELECT status_reason FROM alerts")}
    finally:
        conn.close()
    assert {"TRADE_OPENED", "TRADE_CLOSED"} <= types
    assert {"QUOTA", "COOLDOWN"} <= reasons


def test_ts30_enums_list_trade_types_and_status_reasons(real_schema_dir: Path):
    enums = {e.name: e for e in schema.load_enums(real_schema_dir / "enums.md")}
    assert {"TRADE_OPENED", "TRADE_CLOSED"} <= set(enums["alert_type"].values)
    reason = enums["alert_status_reason"]
    assert not reason.has_check
    assert reason.values == [
        "COOLDOWN",
        "QUOTA",
        "STALE",
        "OVERFLOW",
        "RESTART",
        "TRANSPORT_TEMP",
        "TRANSPORT_PERMANENT",
    ]
    assert reason.columns == ["alerts.status_reason"]
