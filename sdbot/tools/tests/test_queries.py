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
    # Kalibrasi sinyal (spec 13 Req 8.3, TS-53)
    "signal_rejects.sql": ["symbol", "stage", "signals", "share_pct"],
    "score_vs_r.sql": ["score_bucket", "trades", "win_rate", "expectancy_r"],
    "pattern_vs_r.sql": ["pattern", "trades", "win_rate", "expectancy_r"],
    "zone_status_vs_r.sql": ["zone_status", "trades", "win_rate", "expectancy_r"],
    "tp_source_vs_r.sql": ["tp_source", "trades", "win_rate", "expectancy_r"],
    "candidates_per_day.sql": ["symbol", "days", "candidates", "per_day", "accepted"],
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


def test_ts53_signal_queries_attribute_r_to_signal_context():
    """Spec 13 Req 8.3: R hasil trade dikelompokkan menurut konteks sinyal ACCEPTED (run 3: 101 BE_STOP 0.05R,
    102 SL -1R; run 4: 105 TP 4.995R)."""
    cols, rows = _run("pattern_vs_r.sql")
    by = {r[cols.index("pattern")]: r for r in rows}
    assert by["PIN"][cols.index("trades")] == 1 and by["ENGULF"][cols.index("expectancy_r")] == -1.0
    assert by["ENGULF_STRONG"][cols.index("expectancy_r")] == 4.995
    cols, rows = _run("zone_status_vs_r.sql")
    by = {r[cols.index("zone_status")]: r for r in rows}
    assert by["FRESH"][cols.index("trades")] == 2 and by["TESTED"][cols.index("trades")] == 1
    assert by["FRESH"][cols.index("win_rate")] == 100.0
    cols, rows = _run("tp_source_vs_r.sql")
    assert {r[cols.index("tp_source")]: r[cols.index("trades")] for r in rows} == {
        "ZONE": 2,
        "RR": 1,
    }
    cols, rows = _run("score_vs_r.sql")
    assert {r[cols.index("score_bucket")] for r in rows} == {"60-69", "70-79", "80-89"}


def test_ts53_signal_rejects_shares_sum_to_100_per_symbol():
    cols, rows = _run("signal_rejects.sql")
    eur = {r[cols.index("stage")]: r for r in rows if r[cols.index("symbol")] == "EURUSDc"}
    assert eur["ACCEPTED"][cols.index("signals")] == 4  # sesi 1 (lama) + 101, 102, 105
    assert round(sum(r[cols.index("share_pct")] for r in eur.values()), 1) == 100.0
    cols, rows = _run("candidates_per_day.sql")
    assert any(
        r[cols.index("symbol")] == "EURUSDc" and r[cols.index("candidates")] >= 5 for r in rows
    )
