"""Laporan faktor profit dan hasil per tahap tolak (spec 31 Req 4, 5).

`factors`: R per trade per bucket faktor untuk trade nyata (`--source trades`) atau kandidat yang
disimulasikan `outcome_sim.py` (`--source candidates`), di beberapa periode sekaligus, dengan label
konsistensi. `stages`: hasil hipotetis kandidat per tahap tolak dibanding ACCEPTED.

Contoh:
    python factor_report.py factors --db <tester.sqlite> --period IS=1396-1407 --period OOS=1408-1419 \
        --period REAL=1420-1431 [--source candidates --sim-stem hasil.csv]
    python factor_report.py stages --db <tester.sqlite> --period IS=1396-1407 --sim-stem hasil.csv [--dedup-zone-day]
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from exit_report import CLOSED_EA_FROM, CLOSED_EA_WHERE, _where, parse_runs

MIN_BUCKET = 10  # glosarium: >= 10 trade per periode
FACTORS = (
    "status zona",
    "trendline",
    "jarak trendline",
    "pola PA",
    "jam UTC",
    "persen skor",
    "alasan bias",
    "arah",
    "R:R rencana",
    "sumber TP",
    "rezim ATR",
    "simbol",
)


@dataclass(frozen=True)
class Record:
    period: str
    factors: dict[str, str]
    r: float


@dataclass
class FactorRow:
    stats: dict[str, tuple[int, float]] = field(default_factory=dict)  # periode -> (n, R/trade)
    label: str = ""


def _bucket(value: float | None, edges: list[tuple[float, str]], last: str) -> str:
    if value is None:
        return "-"
    for edge, name in edges:
        if value < edge:
            return name
    return last


def _hour_block(time: int) -> str:
    h = (time % 86400) // 3600
    if 8 <= h < 13:
        return "08-13"
    if 13 <= h < 17:
        return "13-17"
    if 17 <= h < 22:
        return "17-22"
    return "lainnya"


def factors_of(
    ctx: dict[str, Any], direction: str, time: int, symbol: str, atr_tier: str
) -> dict[str, str]:
    """Bucket faktor satu kandidat (batas design §3.3, ditetapkan sebelum melihat hasil)."""
    touches = ctx.get("tl_touches")
    dist = ctx.get("tl_dist")
    if not touches:
        tl, tl_dist = "tanpa garis", "-"
    else:
        tl = "3+ sentuhan" if touches >= 3 else "2 sentuhan"
        tl_dist = (
            "-"
            if dist is None
            else ("<=0,1 ATR" if dist <= 0.1 else ("0,1-0,2 ATR" if dist <= 0.2 else ">0,2 ATR"))
        )
    return {
        "status zona": str(ctx.get("zone_status") or "-"),
        "trendline": tl,
        "jarak trendline": tl_dist,
        "pola PA": str(ctx.get("pa") or "-"),
        "jam UTC": _hour_block(time),
        "persen skor": _bucket(
            ctx.get("score_pct"), [(65, "<65"), (75, "65-75"), (85, "75-85")], ">=85"
        ),
        "alasan bias": str(ctx.get("bias_reason") or "-"),
        "arah": direction,
        "R:R rencana": _bucket(ctx.get("rr"), [(2, "<2"), (3, "2-3")], ">=3"),
        "sumber TP": str(ctx.get("tp_source") or "-"),
        "rezim ATR": atr_tier,
        "simbol": symbol,
    }


def factor_table(records: list[Record], periods: list[str]) -> dict[tuple[str, str], FactorRow]:
    """R per trade per (faktor, bucket) per periode + label konsistensi (Req 4.2)."""
    overall: dict[str, list[float]] = defaultdict(list)
    groups: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for rec in records:
        overall[rec.period].append(rec.r)
        for factor, bucket in rec.factors.items():
            groups[(factor, bucket)][rec.period].append(rec.r)
    mean = {p: sum(v) / len(v) for p, v in overall.items() if v}
    table: dict[tuple[str, str], FactorRow] = {}
    for key, per in groups.items():
        row = FactorRow()
        signs = []
        thin = False
        for p in periods:
            rs = per.get(p, [])
            if rs:
                row.stats[p] = (len(rs), sum(rs) / len(rs))
            if len(rs) < MIN_BUCKET:
                thin = True
            elif p in mean:
                signs.append(row.stats[p][1] - mean[p])
        if thin:
            row.label = "SAMPEL KURANG"
        elif all(d > 0 for d in signs):
            row.label = "KONSISTEN+"
        elif all(d < 0 for d in signs):
            row.label = "KONSISTEN-"
        else:
            row.label = "TIDAK KONSISTEN"
        table[key] = row
    return table


def render_factors(table: dict[tuple[str, str], FactorRow], periods: list[str]) -> str:
    head = (
        f"{'faktor':<16} {'bucket':<14}"
        + "".join(f" {p + ' n':>9} {'R':>7}" for p in periods)
        + "  label"
    )
    lines = [head, "-" * len(head)]
    order = {f: i for i, f in enumerate(FACTORS)}
    for (factor, bucket), row in sorted(
        table.items(), key=lambda kv: (order.get(kv[0][0], 99), kv[0][1])
    ):
        line = f"{factor:<16} {bucket:<14}"
        for p in periods:
            n, r = row.stats.get(p, (0, None))
            line += f" {n:>9} {'-' if r is None else format(r, '+.3f'):>7}"
        lines.append(line + "  " + row.label)
    return "\n".join(lines)


@dataclass(frozen=True)
class Cand:
    stage: str
    symbol: str
    zone_ref: str
    time: int
    r: float | None
    passes: bool
    real_r: float | None = None


@dataclass
class StageRow:
    stage: str
    candidates: int
    simulated: int
    r_avg: float | None
    pf: float | None
    pass_pct: float | None
    real_r_avg: float | None


def _dedup(cands: list[Cand]) -> list[Cand]:
    """Kandidat pertama per (simbol, zona, tanggal UTC): EA hanya mengambil satu entry per zona (Req 5.3)."""
    seen: set[tuple[str, str, int]] = set()
    out = []
    for c in sorted(cands, key=lambda c: c.time):
        key = (c.symbol, c.zone_ref, c.time // 86400)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def stage_table(cands: list[Cand], dedup: bool) -> list[StageRow]:
    pool = _dedup(cands) if dedup else cands
    by: dict[str, list[Cand]] = defaultdict(list)
    for c in pool:
        by[c.stage].append(c)
    rows = []
    for stage, cs in sorted(by.items(), key=lambda kv: (kv[0] != "ACCEPTED", kv[0])):
        sim = [c for c in cs if c.r is not None]
        rs = [c.r for c in sim if c.r is not None]
        win = sum(r for r in rs if r > 0)
        loss = -sum(r for r in rs if r < 0)
        reals = [c.real_r for c in cs if c.real_r is not None]
        rows.append(
            StageRow(
                stage,
                len(cs),
                len(sim),
                sum(rs) / len(rs) if rs else None,
                win / loss if loss > 0 else None,
                100.0 * sum(c.passes for c in sim) / len(sim) if sim else None,
                sum(reals) / len(reals) if reals else None,
            )
        )
    return rows


def _f(v: float | None, fmt: str) -> str:
    return "-" if v is None else format(v, fmt)


def render_stages(rows: list[StageRow]) -> str:
    head = (
        f"{'tahap':<20} {'kandidat':>9} {'tersimulasi':>12} {'R/trade sim':>12} {'PF sim':>7} "
        f"{'lolos SL/RR':>12} {'R nyata':>8}"
    )
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(
            f"{r.stage:<20} {r.candidates:>9} {r.simulated:>12} {_f(r.r_avg, '+.3f'):>12} {_f(r.pf, '.2f'):>7} "
            f"{_f(r.pass_pct, '.1f') + '%' if r.pass_pct is not None else '-':>12} {_f(r.real_r_avg, '+.3f'):>8}"
        )
    return "\n".join(lines)


# --- Data dari DB dan hasil simulasi ---


def _atr_tiers(rows: list[dict[str, Any]]) -> dict[int, str]:
    """Tersier ATR MTF per simbol dalam satu periode: 1 rendah, 2 tengah, 3 tinggi."""
    by: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for row in rows:
        atr = row["ctx"].get("atr_mtf")
        if atr is not None:
            by[row["symbol"]].append((float(atr), row["id"]))
    tiers: dict[int, str] = {}
    for vals in by.values():
        vals.sort()
        n = len(vals)
        for i, (_, sid) in enumerate(vals):
            tiers[sid] = str(1 + (3 * i) // n)
    return tiers


def _signals(conn: sqlite3.Connection, ranges: list[tuple[int, int]]) -> list[dict[str, Any]]:
    cond, params = _where("session_id", ranges)
    rows = conn.execute(
        "SELECT id, symbol, time, direction, status, reject_stage, zone_ref, context_json FROM signals "
        f"WHERE {cond}",
        params,
    ).fetchall()
    return [
        {
            "id": r[0],
            "symbol": r[1],
            "time": r[2],
            "direction": r[3],
            "stage": "ACCEPTED" if r[4] == "ACCEPTED" else (r[5] or "-"),
            "zone_ref": r[6] or "",
            "ctx": json.loads(r[7]) if r[7] else {},
        }
        for r in rows
    ]


def _real_r(conn: sqlite3.Connection, ranges: list[tuple[int, int]]) -> dict[int, float]:
    cond, params = _where("t.session_id", ranges)
    rows = conn.execute(
        f"SELECT t.signal_id, c.r_result FROM {CLOSED_EA_FROM} WHERE {CLOSED_EA_WHERE} "
        f"AND t.signal_id IS NOT NULL AND {cond}",
        params,
    ).fetchall()
    return {int(sid): float(r) for sid, r in rows}


def _sim(path: Path) -> dict[int, tuple[float, bool]]:
    with path.open(encoding="utf-8") as f:
        return {
            int(r["signal_id"]): (float(r["r"]), r["passes_rules"] == "1")
            for r in csv.DictReader(f)
        }


def _sim_path(stem: Path, name: str) -> Path:
    return stem.with_name(f"{stem.stem}.{name}{stem.suffix or '.csv'}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("factors", "stages"):
        p = sub.add_parser(name)
        p.add_argument("--db", required=True, type=Path)
        p.add_argument("--period", action="append", required=True, help="NAMA=A-B[,C-D]")
        p.add_argument(
            "--sim-stem", type=Path, help="stem CSV outcome_sim simulate (<stem>.<NAMA>.csv)"
        )
        if name == "factors":
            p.add_argument("--source", choices=("trades", "candidates"), default="trades")
        else:
            p.add_argument("--dedup-zone-day", action="store_true")
    args = ap.parse_args(argv)
    try:
        periods = parse_runs(args.period)
    except ValueError as exc:
        print(f"[factor_report] {exc}")
        return 2
    needs_sim = args.cmd == "stages" or args.source == "candidates"
    if needs_sim and args.sim_stem is None:
        print("[factor_report] --sim-stem wajib untuk kandidat")
        return 2
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        records: list[Record] = []
        for name, ranges in periods:
            sigs = _signals(conn, ranges)
            real = _real_r(conn, ranges)
            sim = _sim(_sim_path(args.sim_stem, name)) if needs_sim else {}
            if args.cmd == "stages":
                cands = [
                    Cand(
                        s["stage"],
                        s["symbol"],
                        s["zone_ref"],
                        s["time"],
                        sim[s["id"]][0] if s["id"] in sim else None,
                        sim[s["id"]][1] if s["id"] in sim else False,
                        real.get(s["id"]),
                    )
                    for s in sigs
                ]
                print(f"== {name}" + (" (dedup zona per hari)" if args.dedup_zone_day else ""))
                print(render_stages(stage_table(cands, args.dedup_zone_day)))
                continue
            tiers = _atr_tiers(sigs)
            for s in sigs:
                r = (
                    real.get(s["id"])
                    if args.source == "trades"
                    else (sim[s["id"]][0] if s["id"] in sim else None)
                )
                if r is None:
                    continue
                f = factors_of(
                    s["ctx"], s["direction"], s["time"], s["symbol"], tiers.get(s["id"], "-")
                )
                records.append(Record(name, f, r))
        if args.cmd == "factors":
            names = [n for n, _ in periods]
            print(f"sumber: {args.source}; {len(records)} trade/kandidat")
            print(render_factors(factor_table(records, names), names))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
