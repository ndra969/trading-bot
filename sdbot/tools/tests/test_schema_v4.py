"""Skema v4: signal_scores.active (spec 17 Req 4): TS-71."""

import sqlite3
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "shared" / "schema" / "migrations" / "data"


def _seed_blocks(max_version: int) -> str:
    text = (DATA / "seed_sample.sql").read_text(encoding="utf-8")
    out, keep = [], False
    for line in text.splitlines():
        if line.startswith("-- @version "):
            keep = int(line.split()[2]) <= max_version
        if keep:
            out.append(line)
    return "\n".join(out)


def test_ts71_migration_0004_keeps_rows_active(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "v3.sqlite")
    for f in sorted(DATA.glob("000[1-3]_*.sql")):
        conn.executescript(f.read_text(encoding="utf-8"))
    conn.executescript(_seed_blocks(3))
    before = conn.execute("SELECT COUNT(*) FROM signal_scores").fetchone()[0]
    assert before > 0
    (m4,) = sorted(DATA.glob("0004_*.sql"))
    conn.executescript(m4.read_text(encoding="utf-8"))
    assert conn.execute(
        "SELECT COUNT(*), MIN(active), MAX(active) FROM signal_scores"
    ).fetchone() == (before, 1, 1)
    conn.execute(
        "INSERT INTO signal_scores (signal_id, component, score, max_score) VALUES (999, 'FIB', 8, 15)"
    )
    assert conn.execute("SELECT active FROM signal_scores WHERE signal_id = 999").fetchone() == (1,)
    conn.execute(
        "INSERT INTO signal_scores (signal_id, component, score, max_score, active) VALUES (999, 'RSI', 0, 5, 0)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO signal_scores (signal_id, component, score, max_score, active) VALUES (999, 'TRENDLINE', 0, 15, 2)"
        )
