"""Uji inti schema.py: pemisah pernyataan, larangan, penomoran, penerapan (spec 03 task 2)."""

import sqlite3
from pathlib import Path

import pytest
import schema


def test_ts09_split_ignores_semicolons_in_strings_and_comments():
    sql = (
        "INSERT INTO t VALUES ('a;b', 'it''s');  -- komentar; bukan pemisah\n"
        'CREATE TABLE "x;y" (a INTEGER); /* blok; komentar */\n'
        "SELECT 1;\n"
        "-- hanya komentar di akhir;\n"
    )
    stmts = schema.split_statements(sql)
    assert len(stmts) == 3
    assert stmts[0].startswith("INSERT INTO t VALUES ('a;b', 'it''s')")
    assert stmts[1].startswith('CREATE TABLE "x;y"')
    assert stmts[2] == "SELECT 1"


@pytest.mark.parametrize(
    "sql, word",
    [
        ("BEGIN; CREATE TABLE a (x INTEGER); COMMIT;", "BEGIN"),
        ("PRAGMA journal_mode=WAL;", "PRAGMA"),
        ("CREATE TRIGGER trg AFTER INSERT ON a BEGIN SELECT 1; END;", "TRIGGER"),
        ("ATTACH DATABASE 'x.db' AS x;", "ATTACH"),
        ("  -- komentar dulu\n  vacuum;", "VACUUM"),
    ],
)
def test_ts08_forbidden_statements_are_reported(sql, word):
    errors = schema.forbidden_statements(schema.split_statements(sql))
    assert errors, f"{word} harus ditolak"
    assert any(word in e.upper() for e in errors)


def test_ts08_allowed_statements_pass():
    sql = "CREATE TABLE a (x INTEGER);\nCREATE INDEX ix_a ON a (x);\nINSERT INTO a VALUES (1);"
    assert schema.forbidden_statements(schema.split_statements(sql)) == []


def _write(mig_dir: Path, name: str, sql: str = "CREATE TABLE t%s (x INTEGER);") -> None:
    mig_dir.mkdir(parents=True, exist_ok=True)
    (mig_dir / name).write_text(sql % name[:4] if "%s" in sql else sql, encoding="utf-8")


def test_ts07_numbering_gap_is_rejected(tmp_path: Path):
    mig = tmp_path / "data"
    _write(mig, "0001_a.sql")
    _write(mig, "0003_c.sql")
    with pytest.raises(schema.SchemaError, match="0002"):
        schema.load_migrations(mig)


def test_ts07_duplicate_number_is_rejected(tmp_path: Path):
    mig = tmp_path / "data"
    _write(mig, "0001_a.sql")
    _write(mig, "0002_b.sql")
    _write(mig, "0002_c.sql")
    with pytest.raises(schema.SchemaError, match="0002"):
        schema.load_migrations(mig)


def test_ts07_bad_file_name_is_rejected(tmp_path: Path):
    mig = tmp_path / "data"
    _write(mig, "0001_a.sql")
    _write(mig, "2_b.sql")
    with pytest.raises(schema.SchemaError, match="2_b.sql"):
        schema.load_migrations(mig)


def test_load_migrations_reads_versions_names_and_checksums(real_schema_dir: Path):
    migs = schema.load_migrations(real_schema_dir / "migrations" / "data")
    assert [m.version for m in migs] == list(range(1, len(migs) + 1))
    assert migs[0].name == "initial"
    assert len(migs[0].sha256) == 64
    assert migs[0].statements


def test_checksum_ignores_line_ending_style(tmp_path: Path):
    mig = tmp_path / "data"
    mig.mkdir()
    (mig / "0001_a.sql").write_bytes(b"CREATE TABLE a (x INTEGER);\n")
    lf = schema.load_migrations(mig)[0].sha256
    (mig / "0001_a.sql").write_bytes(b"CREATE TABLE a (x INTEGER);\r\n")
    crlf = schema.load_migrations(mig)[0].sha256
    assert lf == crlf


def _apply_initial(real_schema_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    schema.apply_migrations(conn, schema.load_migrations(real_schema_dir / "migrations" / "data"))
    return conn


def test_ts14_initial_schema_has_all_tables_and_view(real_schema_dir: Path):
    conn = _apply_initial(real_schema_dir)
    names = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")
    }
    expected = {
        "sessions",
        "accounts",
        "signals",
        "signal_scores",
        "trades",
        "deals",
        "position_events",
        "closures",
        "balance_ops",
        "alerts",
        "v_trade_results",
    }
    assert expected <= names
    conn.execute("SELECT * FROM v_trade_results").fetchall()


def test_ts15_duplicate_trade_insert_is_idempotent(real_schema_dir: Path):
    conn = _apply_initial(real_schema_dir)
    row = (
        1,
        12345,
        42,
        2026091901,
        "EURUSDc",
        "BUY",
        "EA",
        0.1,
        1.1,
        1.1,
        0,
        8,
        1.09,
        1.12,
        5.0,
        0.5,
        None,
        "1.02",
        1,
    )
    sql = (
        "INSERT INTO trades (session_id, login, position_id, magic, symbol, direction, source, volume_initial,"
        " price_requested, price_open, slippage_points, spread_points, sl_initial, tp_initial, risk_money, risk_pct,"
        " signal_id, ea_version, opened_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING"
    )
    conn.execute(sql, row)
    conn.execute(sql, row)
    assert conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == 1


def test_ts16_64bit_position_id_round_trip(real_schema_dir: Path):
    conn = _apply_initial(real_schema_dir)
    big = 1 << 40
    conn.execute(
        "INSERT INTO balance_ops (login, deal_ticket, time, op_type, amount) VALUES (?,?,?,?,?)",
        (12345, big, 1, "BALANCE", 10.0),
    )
    assert conn.execute("SELECT deal_ticket FROM balance_ops").fetchone()[0] == big


def test_seed_blocks_are_split_per_version(real_schema_dir: Path):
    blocks = schema.load_seed(real_schema_dir / "migrations" / "data" / "seed_sample.sql")
    assert set(blocks) == {1, 2, 3, 4}
    conn = _apply_initial(real_schema_dir)
    conn.executescript(blocks[1])
    assert conn.execute("SELECT COUNT(*) FROM closures").fetchone()[0] == 4


def test_ts49_pa_pattern_enum(real_schema_dir: Path):
    """Spec 12: kode pola price action stabil untuk telemetri sinyal (PC-18)."""
    enums = {e.name: e for e in schema.load_enums(real_schema_dir / "enums.md")}
    pa = enums["pa_pattern"]
    assert pa.values == ["STAR", "ENGULF_STRONG", "PIN", "ENGULF", "TWEEZER", "OUTSIDE", "NONE"]
    assert not pa.has_check
    assert pa.columns == ["signals.context_json"]


def test_ts50_signal_enums(real_schema_dir: Path):
    """Spec 13: tahap tolak baru, komponen skor, dan sumber TP (PC-19)."""
    enums = {e.name: e for e in schema.load_enums(real_schema_dir / "enums.md")}
    stages = enums["reject_stage"].values
    assert "POSITION_OPEN" in stages and "SL_TOO_FAR" in stages
    assert stages.index("POSITION_OPEN") < stages.index("NO_PA_TRIGGER")
    comp = enums["score_component"]
    assert comp.values == ["ZONE", "TREND", "PA", "FIB", "TRENDLINE", "BREAKOUT", "RSI"]
    assert not comp.has_check
    assert comp.columns == ["signal_scores.component"]
    tp = enums["tp_source"]
    assert tp.values == ["ZONE", "RR"]
    assert tp.columns == ["signals.context_json"]


def test_ts57_news_filter_off_alert(real_schema_dir: Path):
    """Spec 16 Req 4.2: alert proteksi berita mati (PC-24)."""
    enums = {e.name: e for e in schema.load_enums(real_schema_dir / "enums.md")}
    assert "NEWS_FILTER_OFF" in enums["alert_type"].values
