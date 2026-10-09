"""Laporan alasan tutup per rentang sesi tester (spec 24 Req 1.2, 2.2).

Per run: trade, R per trade, PF, jumlah dan R rata-rata per alasan tutup, SL yang sempat MFE >= 0,5R,
dan jumlah MODIFY_FAILED. Cara hitung trade dan R sama dengan baseline_report.py.

Contoh:
    python exit_report.py --db <tester.sqlite> --runs acuan=1396-1407 --runs be050=1432-1443
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

REASONS = ("SL", "BE_STOP", "TRAIL_STOP", "TP")
MFE_HALF = 0.5

Ranges = list[tuple[int, int]]

# Trade strategi yang sudah tutup dengan R: definisi sama untuk exit_report dan trade_diff (spec 27).
CLOSED_EA_FROM = "closures c JOIN trades t ON t.login = c.login AND t.run_key = c.run_key AND t.position_id = c.position_id"
CLOSED_EA_WHERE = "t.source = 'EA' AND c.r_result IS NOT NULL"


@dataclass
class ExitSummary:
    trades: int = 0
    total_r: float = 0.0
    gross_win: float = 0.0
    gross_loss: float = 0.0
    reasons: dict[str, tuple[int, float]] = field(default_factory=dict)
    sl_mfe_half: int = 0
    modify_failed: int | None = 0
    trail_mfe_avg: float | None = None  # spec 26: MFE rata-rata TRAIL_STOP
    trail_giveback_avg: float | None = None  # spec 26: MFE - R hasil rata-rata TRAIL_STOP

    @property
    def r_per_trade(self) -> float | None:
        return self.total_r / self.trades if self.trades else None

    @property
    def pf(self) -> float | None:
        if not self.trades or self.gross_loss <= 0:
            return None
        return self.gross_win / self.gross_loss


def parse_runs(items: list[str]) -> list[tuple[str, Ranges]]:
    """`NAMA=A-B[,C-D]` -> [(nama, [(A, B), ...])]; format salah -> ValueError."""
    runs: list[tuple[str, Ranges]] = []
    for item in items:
        name, sep, spec = item.partition("=")
        if not sep or not name or not spec:
            raise ValueError(f"--runs harus NAMA=A-B[,C-D]: {item!r}")
        ranges: Ranges = []
        for part in spec.split(","):
            lo, dash, hi = part.partition("-")
            if not dash or not lo.isdigit() or not hi.isdigit() or int(lo) > int(hi):
                raise ValueError(f"rentang sesi salah: {part!r}")
            ranges.append((int(lo), int(hi)))
        runs.append((name, ranges))
    return runs


def _where(column: str, ranges: Ranges) -> tuple[str, list[int]]:
    parts = [f"{column} BETWEEN ? AND ?" for _ in ranges]
    params = [v for r in ranges for v in r]
    return "(" + " OR ".join(parts) + ")", params


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        is not None
    )


def exit_summary(conn: sqlite3.Connection, ranges: Ranges) -> ExitSummary:
    s = ExitSummary()
    cond, params = _where("t.session_id", ranges)
    rows = conn.execute(
        f"SELECT c.reason, c.r_result, c.net_profit, c.mfe_r FROM {CLOSED_EA_FROM} "
        f"WHERE {CLOSED_EA_WHERE} AND {cond}",
        params,
    ).fetchall()
    sums: dict[str, list[float]] = {}
    trail_mfe: list[float] = []
    trail_give: list[float] = []
    for reason, r, net, mfe in rows:
        s.trades += 1
        s.total_r += float(r)
        if net > 0:
            s.gross_win += float(net)
        elif net < 0:
            s.gross_loss -= float(net)
        key = reason if reason in REASONS else "LAIN"
        acc = sums.setdefault(key, [0, 0.0])
        acc[0] += 1
        acc[1] += float(r)
        if reason == "SL" and mfe is not None and mfe >= MFE_HALF:
            s.sl_mfe_half += 1
        if reason == "TRAIL_STOP" and mfe is not None:
            trail_mfe.append(float(mfe))
            trail_give.append(float(mfe) - float(r))
    s.reasons = {k: (int(n), total / n) for k, (n, total) in sums.items()}
    if trail_mfe:
        s.trail_mfe_avg = sum(trail_mfe) / len(trail_mfe)
        s.trail_giveback_avg = sum(trail_give) / len(trail_give)
    if _has_table(conn, "position_events"):
        cond_e, params_e = _where("session_id", ranges)
        s.modify_failed = conn.execute(
            f"SELECT COUNT(*) FROM position_events WHERE type = 'MODIFY_FAILED' AND {cond_e}",
            params_e,
        ).fetchone()[0]
    else:
        s.modify_failed = None
    return s


def _num(v: float | None, fmt: str) -> str:
    return "-" if v is None else format(v, fmt)


def render(summaries: list[tuple[str, ExitSummary]]) -> str:
    keys = [*REASONS, "LAIN"]
    head = f"{'run':<10} {'trade':>6} {'R/trade':>8} {'PF':>5}"
    for k in keys:
        head += f" {k + ' n':>13} {'R':>6}"
    head += f" {'SL MFE>=0.5':>12} {'MOD_FAIL':>9} {'TRAIL MFE':>10} {'GIVEBACK':>9}"
    lines = [head, "-" * len(head)]
    for name, s in summaries:
        line = f"{name:<10} {s.trades:>6} {_num(s.r_per_trade, '+.3f'):>8} {_num(s.pf, '.2f'):>5}"
        for k in keys:
            n, avg = s.reasons.get(k, (0, None))
            line += f" {n:>13} {_num(avg, '+.2f'):>6}"
        line += f" {s.sl_mfe_half:>12} {_num(s.modify_failed, 'd'):>9}"
        line += f" {_num(s.trail_mfe_avg, '+.2f'):>10} {_num(s.trail_giveback_avg, '+.2f'):>9}"
        lines.append(line)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument(
        "--runs", action="append", required=True, help="NAMA=A-B[,C-D] (rentang id sesi inklusif)"
    )
    args = ap.parse_args(argv)
    try:
        runs = parse_runs(args.runs)
    except ValueError as exc:
        print(f"[exit_report] {exc}")
        return 2
    if not args.db.is_file():
        print(f"[exit_report] DB tidak ditemukan: {args.db}")
        return 1
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        print(render([(name, exit_summary(conn, ranges)) for name, ranges in runs]))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
