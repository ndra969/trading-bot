"""Query analisis dasar terhadap fixture data_latest_sample.sqlite (spec 07 Req 3): TQ-01..08."""

import sqlite3
from pathlib import Path

import pytest

SDBOT = Path(__file__).resolve().parents[2]
QUERIES = SDBOT / "tools" / "queries"
FIXTURE = SDBOT / "shared" / "schema" / "fixtures" / "data_latest_sample.sqlite"

EXPECTED_COLUMNS = {
    "summary_by_symbol_version.sql": [
        "symbol",
        "ea_version",
        "trades",
        "win_rate",
        "profit_factor",
        "expectancy_r",
    ],
    "close_reasons.sql": ["reason", "closures", "avg_r"],
    "be_leak.sql": ["run_key", "position_id", "symbol", "r_result", "mfe_r", "leaked_r"],
    "losers_never_green.sql": ["run_key", "position_id", "symbol", "r_result", "mfe_r", "mae_r"],
    "by_session_inputs.sql": ["input_hash", "sessions", "trades", "net_profit", "expectancy_r"],
    "by_run.sql": ["run_key", "mode", "ea_version", "trades", "net_profit", "expectancy_r"],
    "balance_ops.sql": ["month", "run_key", "op_type", "operations", "amount"],
    "alerts_by_severity.sql": ["severity", "status", "alerts"],
}


def _run(name: str) -> tuple[list[str], list[tuple]]:
    conn = sqlite3.connect(f"file:{FIXTURE.as_posix()}?mode=ro", uri=True)
    try:
        cur = conn.execute((QUERIES / name).read_text(encoding="utf-8"))
        return [d[0] for d in cur.description], cur.fetchall()
    finally:
        conn.close()


@pytest.mark.parametrize("name", sorted(EXPECTED_COLUMNS))
def test_tq01_08_query_runs_with_expected_columns_and_rows(name: str):
    columns, rows = _run(name)
    assert columns == EXPECTED_COLUMNS[name]
    assert rows, f"{name} tidak menghasilkan baris dari fixture"


def test_tq_by_run_keeps_tester_runs_apart():
    columns, rows = _run("by_run.sql")
    by_key = {r[columns.index("run_key")]: r for r in rows}
    # Dua run backtest memakai position_id kecil yang sama; masing-masing tetap terhitung sendiri.
    assert {0, 3, 4} <= set(by_key)
    assert by_key[3][columns.index("trades")] == 2
    assert by_key[4][columns.index("trades")] == 1
    assert by_key[3][columns.index("mode")] == "TESTER"


def test_tq_be_leak_joins_on_run_key():
    columns, rows = _run("be_leak.sql")
    keys = {(r[columns.index("run_key")], r[columns.index("position_id")]) for r in rows}
    assert (0, 5000000002) in keys and (3, 2) in keys
    assert (4, 2) not in keys  # run 4 posisi 2 kena TP, bukan BE_STOP


def test_tq_queries_join_positions_on_run_key():
    for path in QUERIES.glob("*.sql"):
        sql = path.read_text(encoding="utf-8").lower()
        if "join closures" in sql or "join trades" in sql:
            assert "run_key" in sql, f"{path.name} menggabungkan posisi tanpa run_key"
