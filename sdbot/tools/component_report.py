"""Laporan hasil trade per nilai komponen skor, IS vs OOS (spec 17 Req 3, design §3.5).

Mengelompokkan trade tertutup (closure ber-r_result dari sinyal ACCEPTED) per (komponen, nilai skor) untuk
setiap periode (IS, OOS, CUSTOM dari `periods.ini`), termasuk komponen bayangan (`signal_scores.active = 0`).
Status aktivasi PC-25: nilai tertinggi lebih baik dari nilai 0 (R per trade) di IS dan OOS, masing-masing
dengan >= min_n trade.

Pemakaian:
    python component_report.py --db <tester.sqlite> --sessions 868-879 [--periods periods.ini] [--min-n 20]
    python component_report.py --db <tester.sqlite> --sessions 868-879 --candidates
Kode keluar: 0 selesai, 2 DB tidak terbaca atau argumen salah.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from periods import CUSTOM, Period, classify, load_periods

MIN_N = 20
PERIOD_ORDER = ("IS", "OOS", "REAL", CUSTOM)
__all__ = [
    "Group",
    "load_periods",
    "group_trades",
    "verdict",
    "render",
    "candidate_distribution",
    "render_candidates",
]


@dataclass
class Group:
    component: str
    active: bool
    score: float
    n: int
    wins: int
    total_r: float

    @property
    def r_per_trade(self) -> float:
        return self.total_r / self.n if self.n else 0.0


def _active_expr(conn: sqlite3.Connection) -> str:
    has = any(r[1] == "active" for r in conn.execute("PRAGMA table_info(signal_scores)"))
    return "c.active" if has else "1"


def _run_periods(
    conn: sqlite3.Connection, first: int, last: int, periods: list[Period]
) -> dict[int, str]:
    return {
        run_key: classify(t_from, t_to, t_model, periods)
        for run_key, t_from, t_to, t_model in conn.execute(
            "SELECT run_key, MIN(tester_from), MAX(tester_to), MAX(tester_model) FROM sessions "
            "WHERE mode = 'TESTER' AND id BETWEEN ? AND ? GROUP BY run_key",
            (first, last),
        )
    }


def group_trades(
    conn: sqlite3.Connection, first: int, last: int, periods: list[Period]
) -> dict[tuple[str, str], list[Group]]:
    """(komponen, periode) -> kelompok per nilai skor, urut nilai."""
    run_period = _run_periods(conn, first, last, periods)
    acc: dict[tuple[str, str, float], Group] = {}
    rows = conn.execute(
        f"SELECT t.run_key, c.component, c.score, {_active_expr(conn)}, cl.r_result FROM trades t "
        "JOIN closures cl ON cl.login = t.login AND cl.run_key = t.run_key AND cl.position_id = t.position_id "
        "JOIN signal_scores c ON c.signal_id = t.signal_id "
        "WHERE t.source = 'EA' AND cl.r_result IS NOT NULL AND t.session_id BETWEEN ? AND ?",
        (first, last),
    )
    for run_key, comp, score, active, r in rows:
        period = run_period.get(run_key, CUSTOM)
        g = acc.setdefault(
            (comp, period, float(score)), Group(comp, bool(active), float(score), 0, 0, 0.0)
        )
        g.n += 1
        g.wins += r > 0
        g.total_r += r
    out: dict[tuple[str, str], list[Group]] = defaultdict(list)
    for (comp, period, _), g in sorted(acc.items()):
        out[(comp, period)].append(g)
    return dict(out)


def verdict(is_groups: list[Group], oos_groups: list[Group], min_n: int = MIN_N) -> str:
    """TERBUKTI / TIDAK / SAMPEL KURANG menurut aturan aktivasi PC-25."""

    def pair(groups: list[Group]) -> tuple[Group, Group] | None:
        zero = next((g for g in groups if g.score == 0), None)
        top = max(groups, key=lambda g: g.score, default=None)
        if zero is None or top is None or top.score == 0 or zero.n < min_n or top.n < min_n:
            return None
        return zero, top

    p_is, p_oos = pair(is_groups), pair(oos_groups)
    if p_is is None or p_oos is None:
        return "SAMPEL KURANG"
    better = all(top.r_per_trade > zero.r_per_trade for zero, top in (p_is, p_oos))
    return "TERBUKTI" if better else "TIDAK"


def _cell(g: Group | None, min_n: int) -> str:
    if g is None:
        return f"{'-':>24}"
    small = "*" if g.n < min_n else " "
    return (
        f"{g.n:>4}{small} {100.0 * g.wins / g.n:>5.1f}% {g.r_per_trade:>+7.3f} {g.total_r:>+6.1f}"
    )


def merge_groups(
    parts: list[dict[tuple[str, str], list[Group]]]
) -> dict[tuple[str, str], list[Group]]:
    """Gabung hasil group_trades beberapa rentang sesi (misalnya IS+OOS dan REAL yang tidak berurutan)."""
    acc: dict[tuple[str, str, float], Group] = {}
    for part in parts:
        for (comp, period), groups in part.items():
            for g in groups:
                t = acc.setdefault(
                    (comp, period, g.score), Group(comp, g.active, g.score, 0, 0, 0.0)
                )
                t.n += g.n
                t.wins += g.wins
                t.total_r += g.total_r
                t.active = t.active or g.active
    out: dict[tuple[str, str], list[Group]] = defaultdict(list)
    for (comp, period, _), g in sorted(acc.items()):
        out[(comp, period)].append(g)
    return dict(out)


MIN_IS_V2 = 50  # spec 22 Req 1.2
MIN_OOS_V2 = 10


def pos_zero(groups: list[Group]) -> tuple[Group, Group]:
    """Gabungan kelompok nilai > 0 dan kelompok nilai 0 (spec 22 aturan v2)."""
    pos = Group("", False, 1.0, 0, 0, 0.0)
    zero = Group("", False, 0.0, 0, 0, 0.0)
    for g in groups:
        t = pos if g.score > 0 else zero
        t.n += g.n
        t.wins += g.wins
        t.total_r += g.total_r
    return pos, zero


def verdict_v2(
    is_g: list[Group],
    oos_g: list[Group],
    real_g: list[Group] | None,
    min_is: int = MIN_IS_V2,
    min_oos: int = MIN_OOS_V2,
) -> str:
    """Spec 22 Req 1: nilai > 0 lebih baik dari 0 di IS dan OOS (sampel minimum), dan tidak lebih buruk di REAL."""
    ip, iz = pos_zero(is_g)
    op, oz = pos_zero(oos_g)
    if min(ip.n, iz.n) < min_is or min(op.n, oz.n) < min_oos:
        return "SAMPEL KURANG"
    if not (ip.r_per_trade > iz.r_per_trade and op.r_per_trade > oz.r_per_trade):
        return "TIDAK"
    if real_g:
        rp, rz = pos_zero(real_g)
        if rp.n and rz.n and rp.r_per_trade < rz.r_per_trade:
            return "TIDAK"
    return "TERBUKTI"


def render(groups: dict[tuple[str, str], list[Group]], min_n: int = MIN_N, rule: str = "v2") -> str:
    comps = sorted({c for c, _ in groups})
    periods = [p for p in PERIOD_ORDER if any(per == p for _, per in groups)]
    head = f"{'nilai':>6} " + " ".join(f"{p + ' n  win%  R/trade  R':>24}" for p in periods)
    lines: list[str] = []
    for comp in comps:
        active = any(g.active for p in periods for g in groups.get((comp, p), []))
        lines.append(f"== {comp} ({'aktif' if active else 'bayangan'}) ==")
        lines.append(head)
        by = {p: {g.score: g for g in groups.get((comp, p), [])} for p in periods}
        for score in sorted({s for p in periods for s in by[p]}):
            lines.append(
                f"{score:>6g} " + " ".join(_cell(by[p].get(score), min_n) for p in periods)
            )
        if rule == "pc25":
            status = verdict(groups.get((comp, "IS"), []), groups.get((comp, "OOS"), []), min_n)
            lines.append(f"status aktivasi (PC-25): {status}")
        else:
            parts = []
            for p in periods:
                pz, zz = pos_zero(groups.get((comp, p), []))
                parts.append(
                    f"{p}: >0 n={pz.n} R/tr {pz.r_per_trade:+.3f} vs 0 n={zz.n} R/tr {zz.r_per_trade:+.3f}"
                )
            lines.append("> 0 vs 0 | " + " | ".join(parts))
            real = groups.get((comp, "REAL"))
            status = verdict_v2(groups.get((comp, "IS"), []), groups.get((comp, "OOS"), []), real)
            lines.append(
                f"status aktivasi (v2, IS >= {MIN_IS_V2} / OOS >= {MIN_OOS_V2}, REAL tidak memburuk): {status}"
            )
        lines.append("")
    lines.append(f"* = sampel kecil (< {min_n} trade)")
    return "\n".join(lines)


def candidate_distribution(
    conn: sqlite3.Connection, first: int, last: int
) -> dict[tuple[str, str], dict[float, int]]:
    """(komponen, tahap) -> {nilai: jumlah kandidat}; tahap ACCEPTED untuk kandidat yang lolos."""
    out: dict[tuple[str, str], dict[float, int]] = defaultdict(dict)
    for comp, stage, score, n in conn.execute(
        "SELECT c.component, COALESCE(s.reject_stage, 'ACCEPTED'), c.score, COUNT(*) FROM signals s "
        "JOIN signal_scores c ON c.signal_id = s.id WHERE s.session_id BETWEEN ? AND ? GROUP BY 1, 2, 3",
        (first, last),
    ):
        out[(comp, stage)][float(score)] = n
    return dict(out)


def render_candidates(dist: dict[tuple[str, str], dict[float, int]]) -> str:
    lines = [f"{'komponen':<10} {'tahap':<18} nilai:jumlah"]
    for (comp, stage), vals in sorted(dist.items()):
        lines.append(
            f"{comp:<10} {stage:<18} " + "  ".join(f"{k:g}:{v}" for k, v in sorted(vals.items()))
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument(
        "--sessions", required=True, help="rentang id sesi A-B (inklusif), beberapa dipisah koma"
    )
    ap.add_argument("--periods", type=Path)
    ap.add_argument("--min-n", type=int, default=MIN_N)
    ap.add_argument("--candidates", action="store_true")
    ap.add_argument(
        "--rule",
        choices=("v2", "pc25"),
        default="v2",
        help="aturan aktivasi (spec 22 v2, atau PC-25 lama)",
    )
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        ranges = [
            tuple(int(x) for x in part.split("-", 1)) for part in args.sessions.split(",") if part
        ]
        if not ranges or any(len(r) != 2 for r in ranges):
            raise ValueError
    except ValueError:
        print("[component] --sessions harus berbentuk A-B[,C-D...]")
        return 2
    try:
        conn = sqlite3.connect(f"file:{args.db.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        print(f"[component] DB tidak terbaca: {exc}")
        return 2
    try:
        if args.candidates:
            dist: dict[tuple[str, str], dict[float, int]] = defaultdict(dict)
            for first, last in ranges:
                for key, vals in candidate_distribution(conn, first, last).items():
                    for score, n in vals.items():
                        dist[key][score] = dist[key].get(score, 0) + n
            print(render_candidates(dict(dist)))
        else:
            periods = (
                load_periods(args.periods)[0] if args.periods and args.periods.exists() else []
            )
            print(
                render(
                    merge_groups([group_trades(conn, a, b, periods) for a, b in ranges]),
                    args.min_n,
                    args.rule,
                )
            )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
