"""Laporan backtest dasar Fase 3 (spec 13 Req 8.2, design §3.4).

Membaca sdbot_tester.sqlite untuk sesi TESTER sesudah penanda (id sesi terbesar sebelum backtest dimulai),
mengelompokkan per run (run_key), lalu memeriksa kriteria PC-19:
- total trade >= --min-total dan setiap simbol >= --min-symbol;
- setiap trade EA punya signal_id ke baris signals ACCEPTED;
- setiap kandidat punya 3 komponen skor (ZONE, TREND, PA);
- tidak ada baris log [SDB][ERROR] / [SDB][CRITICAL] (dikumpulkan runner dari jurnal tester).
Profit dicetak tetapi bukan syarat (PC-15).

Pemakaian:
    python baseline_report.py --db <sdbot_tester.sqlite> --after-session N [--errors file] [--min-total 300] [--min-symbol 15]
    python baseline_report.py --db <sdbot_tester.sqlite> --max-session      (cetak penanda untuk runner)
Kode keluar: 0 lolos, 1 gagal, 2 DB tidak terbaca.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ERROR_LINE = re.compile(r"\[SDB\]\[(ERROR|CRITICAL)\]")
COMPONENTS = ("ZONE", "TREND", "PA")


@dataclass
class RunRow:
    run_key: int
    symbol: str
    candidates: int = 0
    stages: Counter = field(default_factory=Counter)
    trades: int = 0
    closed: int = 0
    wins: int = 0
    total_r: float = 0.0
    no_signal: int = 0
    bad_scores: int = 0

    @property
    def expectancy(self) -> float:
        return self.total_r / self.closed if self.closed else 0.0


@dataclass
class Report:
    rows: list[RunRow]
    errors: list[str]
    problems: list[str]

    @property
    def ok(self) -> bool:
        return not self.problems


def max_session(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COALESCE(MAX(id), 0) FROM sessions").fetchone()[0]


def _run_rows(conn: sqlite3.Connection, after_session: int) -> list[RunRow]:
    runs = conn.execute(
        "SELECT run_key, MIN(symbol) FROM sessions WHERE mode = 'TESTER' AND id > ? GROUP BY run_key ORDER BY run_key",
        (after_session,),
    ).fetchall()
    rows = []
    for run_key, symbol in runs:
        row = RunRow(run_key, symbol)
        ses = "SELECT id FROM sessions WHERE run_key = ? AND mode = 'TESTER'"
        for stage, n in conn.execute(
            f"SELECT COALESCE(reject_stage, 'ACCEPTED'), COUNT(*) FROM signals WHERE session_id IN ({ses}) GROUP BY 1",
            (run_key,),
        ):
            row.stages[stage] = n
            row.candidates += n
        row.trades = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE run_key = ? AND source = 'EA'", (run_key,)
        ).fetchone()[0]
        row.no_signal = conn.execute(
            "SELECT COUNT(*) FROM trades t WHERE t.run_key = ? AND t.source = 'EA' AND NOT EXISTS "
            "(SELECT 1 FROM signals s WHERE s.id = t.signal_id AND s.status = 'ACCEPTED')",
            (run_key,),
        ).fetchone()[0]
        row.bad_scores = conn.execute(
            f"SELECT COUNT(*) FROM signals s WHERE s.session_id IN ({ses}) AND "
            "(SELECT COUNT(*) FROM signal_scores c WHERE c.signal_id = s.id AND c.component IN ('ZONE','TREND','PA')) <> 3",
            (run_key,),
        ).fetchone()[0]
        closed, wins, total = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(CASE WHEN c.r_result > 0 THEN 1 ELSE 0 END), 0), COALESCE(SUM(c.r_result), 0) "
            "FROM closures c JOIN trades t ON t.login = c.login AND t.run_key = c.run_key AND t.position_id = c.position_id "
            "WHERE t.run_key = ? AND t.source = 'EA' AND c.r_result IS NOT NULL",
            (run_key,),
        ).fetchone()
        row.closed, row.wins, row.total_r = closed, wins, float(total)
        rows.append(row)
    return rows


def evaluate(
    conn: sqlite3.Connection,
    *,
    after_session: int,
    error_lines: list[str],
    min_total: int,
    min_symbol: int,
) -> Report:
    rows = _run_rows(conn, after_session)
    errors = [line.strip() for line in error_lines if ERROR_LINE.search(line)]
    problems: list[str] = []
    if not rows:
        problems.append("tidak ada run TESTER sesudah penanda")
    total = sum(r.trades for r in rows)
    if total < min_total:
        problems.append(f"total trade {total} < {min_total}")
    for r in rows:
        if r.trades < min_symbol:
            problems.append(f"{r.symbol} (run {r.run_key}): {r.trades} trade < {min_symbol}")
        if r.no_signal:
            problems.append(
                f"{r.symbol} (run {r.run_key}): {r.no_signal} trade tanpa signal_id ACCEPTED"
            )
        if r.bad_scores:
            problems.append(
                f"{r.symbol} (run {r.run_key}): {r.bad_scores} kandidat dengan skor tidak lengkap"
            )
    if errors:
        problems.append(f"{len(errors)} baris log ERROR/CRITICAL, pertama: {errors[0]}")
    return Report(rows, errors, problems)


def render(rep: Report) -> str:
    head = f"{'simbol':<9} {'run':>5} {'kandidat':>8} {'trade':>5} {'win%':>5} {'R total':>8} {'R/trade':>7}  tahap tolak teratas"
    lines = [head, "-" * len(head)]
    for r in rep.rows:
        win = 100.0 * r.wins / r.closed if r.closed else 0.0
        top = ", ".join(f"{s} {n}" for s, n in r.stages.most_common(4) if s != "ACCEPTED")
        lines.append(
            f"{r.symbol:<9} {r.run_key:>5} {r.candidates:>8} {r.trades:>5} {win:>5.1f} {r.total_r:>8.2f} {r.expectancy:>7.3f}  {top}"
        )
    closed = sum(r.closed for r in rep.rows)
    total_r = sum(r.total_r for r in rep.rows)
    lines.append(
        f"{'TOTAL':<9} {'':>5} {sum(r.candidates for r in rep.rows):>8} {sum(r.trades for r in rep.rows):>5} "
        f"{'':>5} {total_r:>8.2f} {(total_r / closed if closed else 0.0):>7.3f}"
    )
    lines.append("")
    lines.append("LOLOS" if rep.ok else "GAGAL:\n  - " + "\n  - ".join(rep.problems))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--after-session", type=int, default=0)
    ap.add_argument("--max-session", action="store_true")
    ap.add_argument("--errors", type=Path, help="file baris log ERROR/CRITICAL dari jurnal tester")
    ap.add_argument("--min-total", type=int, default=300)
    ap.add_argument("--min-symbol", type=int, default=15)
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # konsol Windows cp1252
    try:
        conn = sqlite3.connect(f"file:{args.db.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        print(f"[baseline] DB tidak terbaca: {exc}")
        return 2
    try:
        if args.max_session:
            print(max_session(conn))
            return 0
        # PowerShell menulis UTF-8 dengan BOM; utf-8-sig membuangnya.
        lines = (
            args.errors.read_text(encoding="utf-8-sig").splitlines()
            if args.errors and args.errors.exists()
            else []
        )
        rep = evaluate(
            conn,
            after_session=args.after_session,
            error_lines=lines,
            min_total=args.min_total,
            min_symbol=args.min_symbol,
        )
    finally:
        conn.close()
    print(render(rep))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
