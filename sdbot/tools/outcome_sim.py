"""Simulator hasil kandidat SDBot di atas bar M1 (spec 31 Req 2, 3).

Meniru `BuildStops` (SL di luar distal zona + buffer ATR, TP ke zona lawan atau R:R minimum) dan
`CPositionManager` (BE, partial, trailing ATR M15) agar kandidat yang ditolak bisa dinilai dengan
aturan yang sama dengan trade nyata. Bar M1 berisi harga bid; ask = bid + spread kandidat.

Urutan per bar (konservatif, design §3.2):
    1. gap: open melewati SL -> keluar di open;
    2. harga merugikan menyentuh SL -> keluar di SL;
    3. harga menguntungkan: partial di level partial, lalu TP;
    4. BE dan trailing dihitung dari ekstrem bar ini dan berlaku mulai bar berikutnya.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from exit_report import parse_runs

FArr = npt.NDArray[np.float64]
IArr = npt.NDArray[np.int64]

M15_SEC = 900
MIN_SL_STEP_PTS = 5  # SDB_MIN_SL_STEP_POINTS
CLOSE_REASON_TOL_PTS = 2  # SDB_CLOSE_REASON_TOLERANCE_PTS


@dataclass(frozen=True)
class Candidate:
    signal_id: int
    session_id: int
    symbol: str
    time: int  # awal bar M15 kandidat (UTC epoch)
    direction: str
    stage: str | None
    zone_prox: float
    zone_dist: float
    opp_prox: float | None
    bid: float
    ask: float
    atr_mtf: float
    point: float
    digits: int


@dataclass(frozen=True)
class ExitRules:
    sl_buffer_atr: float
    min_rr: float
    min_sl_atr: float
    max_sl_atr: float
    be_r: float
    be_buffer_pts: int
    partial_r: float
    partial_pct: float
    trail_atr_period: int
    trail_atr_mult: float
    min_sl_step_pts: int = MIN_SL_STEP_PTS


@dataclass(frozen=True)
class Stops:
    entry: float
    sl: float
    tp: float
    risk: float
    rr: float
    passes_rules: bool


@dataclass
class Outcome:
    r: float
    reason: str
    mfe_r: float
    passes_rules: bool
    open_at_end: bool = False
    closed_at: int = 0  # spec 32: waktu bar M1 saat posisi tutup (0 = tidak diketahui)


@dataclass
class Bars:
    time: IArr
    open: FArr
    high: FArr
    low: FArr
    close: FArr
    point: float
    digits: int
    spread: FArr | None = field(default=None)


@dataclass
class Atr:
    """ATR per bar M15 tertutup; `time` = waktu tutup bar (awal + 900)."""

    time: IArr
    value: FArr

    def value_at(self, t: int) -> float:
        i = int(np.searchsorted(self.time, t, side="right")) - 1
        return float(self.value[i]) if i >= 0 else 0.0


def exit_rules_from_inputs(inputs: dict[str, Any]) -> ExitRules:
    """Aturan exit dari `sessions.inputs_json` (design §7 keputusan 2)."""
    return ExitRules(
        sl_buffer_atr=float(inputs["InpSlBufferAtr"]),
        min_rr=float(inputs["InpMinRR"]),
        min_sl_atr=float(inputs["InpMinSlAtr"]),
        max_sl_atr=float(inputs["InpMaxSlAtr"]),
        be_r=float(inputs["InpBreakevenR"]),
        be_buffer_pts=int(inputs["InpBreakevenBufferPoints"]),
        partial_r=float(inputs["InpPartialR"]),
        partial_pct=float(inputs["InpPartialPct"]),
        trail_atr_period=int(inputs["InpTrailATRPeriod"]),
        trail_atr_mult=float(inputs["InpTrailATRMult"]),
    )


def candidate_from_row(ctx: dict[str, Any], row: dict[str, Any]) -> Candidate | None:
    """Kandidat dari `context_json` + kolom `signals`; None bila harga zona/bid/ask tidak ada (Req 2.6)."""
    if any(ctx.get(k) is None for k in ("zone_prox", "zone_dist", "bid", "ask", "atr_mtf")):
        return None
    return Candidate(
        signal_id=int(row["id"]),
        session_id=int(row["session_id"]),
        symbol=str(row["symbol"]),
        time=int(row["time"]),
        direction=str(row["direction"]),
        stage=row.get("reject_stage"),
        zone_prox=float(ctx["zone_prox"]),
        zone_dist=float(ctx["zone_dist"]),
        opp_prox=None if ctx.get("opp_prox") is None else float(ctx["opp_prox"]),
        bid=float(ctx["bid"]),
        ask=float(ctx["ask"]),
        atr_mtf=float(ctx["atr_mtf"]),
        point=float(row["point"]),
        digits=int(row["digits"]),
    )


def build_stops(c: Candidate, x: ExitRules) -> Stops:
    """Meniru `BuildStops`: entry di ask/bid, SL distal -/+ buffer (SELL + spread), TP zona lawan atau R:R min."""
    buy = c.direction == "BUY"
    spread = c.ask - c.bid
    entry = c.ask if buy else c.bid
    sl = (
        c.zone_dist - x.sl_buffer_atr * c.atr_mtf
        if buy
        else c.zone_dist + x.sl_buffer_atr * c.atr_mtf + spread
    )
    sl = round(sl, c.digits)
    risk = entry - sl if buy else sl - entry
    if risk <= 0:
        return Stops(entry, sl, 0.0, risk, 0.0, False)
    if c.opp_prox is not None:
        tp = round(c.opp_prox, c.digits)
    else:
        tp = round(entry + x.min_rr * risk if buy else entry - x.min_rr * risk, c.digits)
    rr = (tp - entry if buy else entry - tp) / risk
    eps = 1e-9 * c.atr_mtf
    min_dist = max(spread, x.min_sl_atr * c.atr_mtf)
    ok = risk >= min_dist - eps and risk <= x.max_sl_atr * c.atr_mtf + eps and rr >= x.min_rr - 1e-9
    return Stops(entry, sl, tp, risk, rr, ok)


def _reason(buy: bool, entry: float, level: float, be_sl: float | None, point: float) -> str:
    """Meniru `MapCloseReason` untuk exit lewat SL."""
    be = be_sl if be_sl is not None else entry
    tol = CLOSE_REASON_TOL_PTS * point
    if (level > be + tol) if buy else (level < be - tol):
        return "TRAIL_STOP"
    if (level >= entry - point / 2) if buy else (level <= entry + point / 2):
        return "BE_STOP"
    return "SL"


def simulate(
    c: Candidate, x: ExitRules, bars: Bars, atr15: Atr, close_after: int | None = None
) -> Outcome:
    """Hasil satu kandidat dalam R (Req 2.1-2.7); bar mulai sesudah bar M15 kandidat tutup.

    close_after (spec 38 Req 5.4): bar M1 pertama dengan waktu >= nilai ini menutup posisi di open-nya
    (alasan FRIDAY). None = perilaku spec 31.
    """
    s = build_stops(c, x)
    if s.risk <= 0:
        return Outcome(0.0, "INVALID", 0.0, False)
    buy = c.direction == "BUY"
    sign = 1.0 if buy else -1.0
    spread = c.ask - c.bid
    spread_pts = int(round(spread / c.point))
    adj = 0.0 if buy else spread  # BUY dinilai di bid, SELL di ask
    sl, vol, realized, mfe = s.sl, 1.0, 0.0, 0.0
    be_sl: float | None = None
    partial_done = False
    start = int(np.searchsorted(bars.time, c.time + M15_SEC, side="left"))

    def r_of(price: float) -> float:
        return sign * (price - s.entry) / s.risk

    for i in range(start, len(bars.time)):
        o = bars.open[i] + adj
        if close_after is not None and bars.time[i] >= close_after:
            return Outcome(
                realized + vol * r_of(o), "FRIDAY", mfe, s.passes_rules, closed_at=int(bars.time[i])
            )
        hi = bars.high[i] + adj
        lo = bars.low[i] + adj
        adverse, favorable = (lo, hi) if buy else (hi, lo)
        # 1-2: gap dan SL lebih dulu
        if (o <= sl) if buy else (o >= sl):
            return Outcome(
                realized + vol * r_of(o),
                _reason(buy, s.entry, sl, be_sl, c.point),
                mfe,
                s.passes_rules,
                closed_at=int(bars.time[i]),
            )
        if (adverse <= sl) if buy else (adverse >= sl):
            return Outcome(
                realized + vol * r_of(sl),
                _reason(buy, s.entry, sl, be_sl, c.point),
                mfe,
                s.passes_rules,
                closed_at=int(bars.time[i]),
            )
        peak_r = r_of(favorable)
        mfe = max(mfe, peak_r)
        # 3: partial lalu TP
        if not partial_done and peak_r >= x.partial_r - 1e-9:
            part = x.partial_pct / 100.0
            realized += part * x.partial_r
            vol -= part
            partial_done = True
        if (favorable >= s.tp) if buy else (favorable <= s.tp):
            return Outcome(
                realized + vol * r_of(s.tp), "TP", mfe, s.passes_rules, closed_at=int(bars.time[i])
            )
        # 4: BE / trailing untuk bar berikutnya (PickBestSl)
        be_active = be_sl is not None and ((sl >= s.entry) if buy else (sl <= s.entry))
        cand_be = 0.0
        if be_sl is None and peak_r >= x.be_r - 1e-9:
            off = (spread_pts + x.be_buffer_pts) * c.point
            cand_be = round(s.entry + off if buy else s.entry - off, c.digits)
        cand_trail = 0.0
        a = atr15.value_at(int(bars.time[i]))
        if be_active and a > 0:
            cand_trail = round(
                favorable - a * x.trail_atr_mult if buy else favorable + a * x.trail_atr_mult,
                c.digits,
            )
        best = cand_be
        if cand_trail and (not best or ((cand_trail > best) if buy else (cand_trail < best))):
            best = cand_trail
        if best:
            gain_pts = round(((best - sl) if buy else (sl - best)) / c.point)
            if gain_pts >= x.min_sl_step_pts:
                if cand_be and best == cand_be:
                    be_sl = cand_be
                sl = best
    last = len(bars.time) - 1
    if last < start:
        return Outcome(0.0, "NO_DATA", 0.0, s.passes_rules, open_at_end=True)
    return Outcome(
        realized + vol * r_of(bars.close[last] + adj),
        "END",
        mfe,
        s.passes_rules,
        open_at_end=True,
        closed_at=int(bars.time[last]),
    )


def m15_atr(bars: Bars, period: int) -> Atr:
    """ATR M15 (SMA dari True Range, sama dengan iATR) dari agregasi bar M1."""
    if len(bars.time) == 0:
        return Atr(np.array([], dtype=np.int64), np.array([]))
    key = bars.time // M15_SEC
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    ends = np.r_[starts[1:], len(key)]
    high = np.maximum.reduceat(bars.high, starts)
    low = np.minimum.reduceat(bars.low, starts)
    close = bars.close[ends - 1]
    prev = np.r_[np.nan, close[:-1]]
    tr = np.where(np.isnan(prev), high - low, np.maximum(high, prev) - np.minimum(low, prev))
    val = np.zeros(len(tr))
    if len(tr) >= period:
        cs = np.cumsum(np.r_[0.0, tr])
        val[period - 1 :] = (cs[period:] - cs[:-period]) / period
    return Atr(key[starts] * M15_SEC + M15_SEC, val)


def load_bars(csv: Path) -> Bars:
    """CSV ExportBars (`# symbol=.. point=.. digits=..`, header, `time,open,high,low,close,spread`) + cache .npz."""
    cache = csv.with_suffix(".npz")
    if cache.is_file() and cache.stat().st_mtime >= csv.stat().st_mtime:
        z = np.load(cache)
        return Bars(
            z["time"],
            z["open"],
            z["high"],
            z["low"],
            z["close"],
            float(z["point"]),
            int(z["digits"]),
            z["spread"],
        )
    with csv.open(encoding="utf-8") as f:
        meta = dict(kv.split("=", 1) for kv in f.readline().lstrip("#").split())
    data = np.loadtxt(csv, delimiter=",", skiprows=2, ndmin=2)
    point, digits = float(meta["point"]), int(meta["digits"])
    b = Bars(
        data[:, 0].astype(np.int64),
        data[:, 1],
        data[:, 2],
        data[:, 3],
        data[:, 4],
        point,
        digits,
        data[:, 5],
    )
    assert b.spread is not None
    np.savez(
        cache,
        time=b.time,
        open=b.open,
        high=b.high,
        low=b.low,
        close=b.close,
        spread=b.spread,
        point=point,
        digits=digits,
    )
    return b


# --- Kandidat dari DB, kalibrasi, CLI (spec 31 Req 2.6, 3) ---

CAL_SAME_REASON_PCT = 85.0  # Req 3.3
CAL_MEAN_ABS_DIFF = 0.15
CAL_AGG_DIFF = 0.03


class BarStore:
    """Bar M1 + ATR M15 per simbol dari folder ekspor, dimuat sekali."""

    def __init__(self, bars_dir: Path) -> None:
        self.dir = bars_dir
        self._bars: dict[str, Bars | None] = {}
        self._atr: dict[tuple[str, int], Atr] = {}

    def bars(self, symbol: str) -> Bars | None:
        if symbol not in self._bars:
            csv = self.dir / f"{symbol}_M1.csv"
            self._bars[symbol] = load_bars(csv) if csv.is_file() else None
        return self._bars[symbol]

    def atr(self, symbol: str, period: int) -> Atr:
        key = (symbol, period)
        if key not in self._atr:
            b = self.bars(symbol)
            empty = Atr(np.array([], dtype=np.int64), np.array([], dtype=np.float64))
            self._atr[key] = m15_atr(b, period) if b is not None else empty
        return self._atr[key]


@dataclass
class SimRow:
    cand: Candidate
    rules: ExitRules
    status: str
    real_reason: str | None = None
    real_r: float | None = None


def _ranges_sql(column: str, ranges: list[tuple[int, int]]) -> tuple[str, list[int]]:
    parts = " OR ".join(f"{column} BETWEEN ? AND ?" for _ in ranges)
    return "(" + parts + ")", [v for r in ranges for v in r]


def load_rows(
    conn: Any, ranges: list[tuple[int, int]], store: BarStore, accepted_only: bool
) -> tuple[list[SimRow], int]:
    """Kandidat (atau hanya trade EA yang sudah tutup) + aturan exit sesinya, dan jumlah yang dilewati."""
    cond, params = _ranges_sql("s.session_id", ranges)
    if accepted_only:
        join = (
            "JOIN trades t ON t.signal_id = s.id AND t.source = 'EA' "
            "JOIN closures c ON c.login = t.login AND c.run_key = t.run_key "
            "AND c.position_id = t.position_id AND c.r_result IS NOT NULL"
        )
        cols = "c.reason, c.r_result"
    else:
        join, cols = "", "NULL, NULL"
    rows = conn.execute(
        "SELECT s.id, s.session_id, s.symbol, s.time, s.direction, s.reject_stage, s.status, "
        f"s.context_json, x.inputs_json, {cols} FROM signals s JOIN sessions x ON x.id = s.session_id "
        f"{join} WHERE {cond} ORDER BY s.time",
        params,
    ).fetchall()
    out: list[SimRow] = []
    skipped = 0
    rules_cache: dict[str, ExitRules] = {}
    for sid, sess, symbol, t, direction, stage, status, ctx_json, inputs_json, reason, r in rows:
        b = store.bars(symbol)
        ctx = json.loads(ctx_json) if ctx_json else {}
        row = {
            "id": sid,
            "session_id": sess,
            "symbol": symbol,
            "time": t,
            "direction": direction,
            "reject_stage": stage,
        }
        cand = (
            None
            if b is None
            else candidate_from_row(ctx, {**row, "point": b.point, "digits": b.digits})
        )
        if cand is None:
            skipped += 1
            continue
        if inputs_json not in rules_cache:
            rules_cache[inputs_json] = exit_rules_from_inputs(json.loads(inputs_json))
        real_r = None if r is None else float(r)
        out.append(SimRow(cand, rules_cache[inputs_json], status, reason, real_r))
    return out, skipped


def run_sim(row: SimRow, store: BarStore) -> Outcome:
    b = store.bars(row.cand.symbol)
    assert b is not None
    return simulate(row.cand, row.rules, b, store.atr(row.cand.symbol, row.rules.trail_atr_period))


@dataclass
class CalibrationReport:
    n: int
    skipped: int
    same_reason_pct: float
    mean_diff: float
    mean_abs_diff: float
    real_r: float
    sim_r: float

    @property
    def passed(self) -> bool:
        return (
            self.n > 0
            and self.same_reason_pct >= CAL_SAME_REASON_PCT
            and self.mean_abs_diff <= CAL_MEAN_ABS_DIFF
            and abs(self.sim_r - self.real_r) <= CAL_AGG_DIFF
        )


def calibrate(conn: Any, ranges: list[tuple[int, int]], bars_dir: Path) -> CalibrationReport:
    """Simulasikan trade nyata dan bandingkan dengan `closures` (Req 3.1-3.3)."""
    store = BarStore(bars_dir)
    rows, skipped = load_rows(conn, ranges, store, accepted_only=True)
    same = 0
    diffs: list[float] = []
    reals: list[float] = []
    sims: list[float] = []
    for row in rows:
        o = run_sim(row, store)
        assert row.real_r is not None
        same += o.reason == row.real_reason
        diffs.append(o.r - row.real_r)
        reals.append(row.real_r)
        sims.append(o.r)
    n = len(rows)
    if n == 0:
        return CalibrationReport(0, skipped, 0.0, 0.0, 0.0, 0.0, 0.0)
    return CalibrationReport(
        n,
        skipped,
        100.0 * same / n,
        sum(diffs) / n,
        sum(abs(d) for d in diffs) / n,
        sum(reals) / n,
        sum(sims) / n,
    )


def render_calibration(reports: list[tuple[str, CalibrationReport]]) -> str:
    head = (
        f"{'run':<8} {'trade':>6} {'lewati':>7} {'alasan sama':>12} {'selisih R':>10} "
        f"{'|selisih|':>10} {'R nyata':>8} {'R sim':>7}  status"
    )
    lines = [head, "-" * len(head)]
    for name, r in reports:
        status = "LOLOS" if r.passed else "GAGAL"
        lines.append(
            f"{name:<8} {r.n:>6} {r.skipped:>7} {r.same_reason_pct:>11.1f}% {r.mean_diff:>+10.3f} "
            f"{r.mean_abs_diff:>10.3f} {r.real_r:>+8.3f} {r.sim_r:>+7.3f}  {status}"
        )
    lines.append(
        f"ambang: alasan sama >= {CAL_SAME_REASON_PCT:.0f}%, |selisih| <= {CAL_MEAN_ABS_DIFF}R, "
        f"selisih R/trade <= {CAL_AGG_DIFF}R"
    )
    return "\n".join(lines)


SIM_COLUMNS = (
    "signal_id",
    "session_id",
    "symbol",
    "time",
    "direction",
    "status",
    "stage",
    "r",
    "reason",
    "mfe_r",
    "passes_rules",
    "open_at_end",
)


def simulate_all(
    conn: Any, ranges: list[tuple[int, int]], bars_dir: Path, out: Path
) -> tuple[int, int]:
    """Semua kandidat rentang sesi -> CSV hasil (Req 2.5); kembalikan (tersimulasi, dilewati)."""
    store = BarStore(bars_dir)
    rows, skipped = load_rows(conn, ranges, store, accepted_only=False)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(SIM_COLUMNS)
        for row in rows:
            o = run_sim(row, store)
            c = row.cand
            w.writerow(
                [
                    c.signal_id,
                    c.session_id,
                    c.symbol,
                    c.time,
                    c.direction,
                    row.status,
                    c.stage or "",
                    f"{o.r:.4f}",
                    o.reason,
                    f"{o.mfe_r:.4f}",
                    int(o.passes_rules),
                    int(o.open_at_end),
                ]
            )
    return len(rows), skipped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("simulate", "calibrate"):
        p = sub.add_parser(name)
        p.add_argument("--db", required=True, type=Path)
        p.add_argument("--runs", action="append", required=True, help="NAMA=A-B[,C-D]")
        p.add_argument(
            "--bars", required=True, type=Path, help="folder <SIMBOL>_M1.csv dari ExportBars"
        )
        if name == "simulate":
            p.add_argument(
                "--out", required=True, type=Path, help="CSV hasil; per run <stem>.<NAMA>.csv"
            )
    args = ap.parse_args(argv)
    try:
        runs = parse_runs(args.runs)
    except ValueError as exc:
        print(f"[outcome_sim] {exc}")
        return 2
    if not args.db.is_file() or not args.bars.is_dir():
        print("[outcome_sim] DB atau folder bar tidak ditemukan")
        return 1
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        if args.cmd == "calibrate":
            reports = [(name, calibrate(conn, ranges, args.bars)) for name, ranges in runs]
            print(render_calibration(reports))
            return 0 if all(r.passed for _, r in reports) else 3
        for name, ranges in runs:
            path = args.out.with_name(f"{args.out.stem}.{name}{args.out.suffix or '.csv'}")
            done, skipped = simulate_all(conn, ranges, args.bars, path)
            print(
                f"[outcome_sim] {name}: {done} kandidat tersimulasi, {skipped} dilewati -> {path}"
            )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
