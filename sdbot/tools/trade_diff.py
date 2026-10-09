"""Trade varian vs acuan: sama, baru, hilang dengan R per trade (spec 27 Req 3.2).

Trade dicocokkan lewat simbol + waktu bar sinyal + arah (`trades.signal_id -> signals`), karena
`signal_id` memuat run_key dan berbeda antar run. Trade dan R didefinisikan sama dengan exit_report.py
(trade EA yang sudah tutup dengan `r_result`). Trade tanpa sinyal (RECONCILED, sinyal hilang) diabaikan
dan jumlahnya dicetak.

Contoh:
    python trade_diff.py --db <tester.sqlite> --base 1396-1407 --variant v-a=1444-1455 --variant v-c=1456-1467
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from exit_report import (
    CLOSED_EA_FROM,
    CLOSED_EA_WHERE,
    Ranges,
    _has_table,
    _num,
    _where,
    parse_runs,
)

Key = tuple[str, int, str]


@dataclass
class Group:
    rs: list[float] = field(default_factory=list)
    base_rs: list[float] = field(default_factory=list)  # hanya grup "sama": R acuan pasangannya

    @property
    def n(self) -> int:
        return len(self.rs)

    @property
    def r_avg(self) -> float | None:
        return sum(self.rs) / len(self.rs) if self.rs else None

    @property
    def base_r_avg(self) -> float | None:
        return sum(self.base_rs) / len(self.base_rs) if self.base_rs else None


@dataclass
class TradeDiff:
    same: Group = field(default_factory=Group)
    new: Group = field(default_factory=Group)
    lost: Group = field(default_factory=Group)
    skipped: int = 0


def _trades(conn: sqlite3.Connection, ranges: Ranges) -> tuple[dict[Key, list[float]], int]:
    cond, params = _where("t.session_id", ranges)
    rows = conn.execute(
        f"SELECT s.symbol, s.time, t.direction, c.r_result FROM {CLOSED_EA_FROM} "
        f"LEFT JOIN signals s ON s.id = t.signal_id WHERE {CLOSED_EA_WHERE} AND {cond}",
        params,
    ).fetchall()
    by_key: dict[Key, list[float]] = defaultdict(list)
    skipped = 0
    for symbol, bar, direction, r in rows:
        if symbol is None:
            skipped += 1
            continue
        by_key[(symbol, int(bar), direction)].append(float(r))
    cond_x, params_x = _where("t.session_id", ranges)
    skipped += conn.execute(
        f"SELECT COUNT(*) FROM {CLOSED_EA_FROM} WHERE t.source <> 'EA' AND c.r_result IS NOT NULL AND {cond_x}",
        params_x,
    ).fetchone()[0]
    return by_key, skipped


def diff_trades(conn: sqlite3.Connection, base: Ranges, variant: Ranges) -> TradeDiff:
    """Pasangkan trade varian dengan acuan per kunci; sisa varian = baru, sisa acuan = hilang."""
    base_trades, _ = _trades(conn, base)
    var_trades, skipped = _trades(conn, variant)
    d = TradeDiff(skipped=skipped)
    for key in sorted(set(base_trades) | set(var_trades)):
        b, v = base_trades.get(key, []), var_trades.get(key, [])
        k = min(len(b), len(v))
        d.same.rs.extend(v[:k])
        d.same.base_rs.extend(b[:k])
        d.new.rs.extend(v[k:])
        d.lost.rs.extend(b[k:])
    return d


def render(diffs: list[tuple[str, TradeDiff]]) -> str:
    head = (
        f"{'run':<10} {'sama n':>7} {'R':>7} {'R acuan':>8} {'baru n':>7} {'R':>7} "
        f"{'hilang n':>9} {'R acuan':>8} {'tanpa sinyal':>13}"
    )
    lines = [head, "-" * len(head)]
    for name, d in diffs:
        lines.append(
            f"{name:<10} {d.same.n:>7} {_num(d.same.r_avg, '+.3f'):>7} {_num(d.same.base_r_avg, '+.3f'):>8} "
            f"{d.new.n:>7} {_num(d.new.r_avg, '+.3f'):>7} {d.lost.n:>9} {_num(d.lost.r_avg, '+.3f'):>8} "
            f"{d.skipped:>13}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--base", required=True, help="A-B[,C-D] (rentang id sesi acuan, inklusif)")
    ap.add_argument("--variant", action="append", required=True, help="NAMA=A-B[,C-D]")
    args = ap.parse_args(argv)
    try:
        base = parse_runs([f"acuan={args.base}"])[0][1]
        variants = parse_runs(args.variant)
    except ValueError as exc:
        print(f"[trade_diff] {exc}")
        return 2
    if not args.db.is_file():
        print(f"[trade_diff] DB tidak ditemukan: {args.db}")
        return 1
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        if not all(_has_table(conn, t) for t in ("signals", "trades", "closures")):
            print("[trade_diff] DB tanpa tabel signals/trades/closures")
            return 2
        print(render([(name, diff_trades(conn, base, ranges)) for name, ranges in variants]))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
