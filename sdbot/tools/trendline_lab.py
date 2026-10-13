"""Lab setup trendline H1 + PA M15 (spec 32).

Port aturan EA (FindSwings, StructureOf, EmaSeries/EmaDirectionOf, BiasOf AND_EMA, TlEvaluate, DetectPattern,
AtrSeries) di atas bar M1 hasil ExportBars yang diagregasi ke M15/H1/H4, dengan jendela bar yang sama dengan EA
(H4 105, H1 156, M15 45), tanpa lookahead. Setup:
    A pantulan: bar M15 menyentuh trendline H1 searah + pola PA searah;
    C break + retest: close M15 menembus trendline > 0,2 ATR, lalu dalam 20 bar retest garis + pola PA searah tembusan;
    B trendline + zona: dibaca dari trade EA (tl_touches >= 2).
Exit lewat outcome_sim.simulate (aturan EA). Satu posisi per simbol.

Contoh:
    python trendline_lab.py verify --db <tester.sqlite> --bars <sdbot_bars> --runs IS=1968-1979
    python trendline_lab.py run --bars <sdbot_bars> --db <tester.sqlite> --period IS --period OOS --period REAL
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import outcome_sim as osim
from exit_report import CLOSED_EA_FROM, CLOSED_EA_WHERE, _where, parse_runs

# --- Konstanta EA (Core/Constants.mqh, preset 1.31) ---
STRENGTH = 2
LOOKBACK = 100
EMA_BIAS = 21
EMA_SLOPE = 3
WARMUP = 3  # SDB_EMA_WARMUP_MULT
ATR_PERIOD = 14
H4_WINDOW = max(
    LOOKBACK + 2 * STRENGTH + 1, WARMUP * EMA_BIAS + EMA_SLOPE + 1
)  # BarsNeeded HTF = 105
H1_WINDOW = 100 + 10 + 2 * STRENGTH + WARMUP * ATR_PERIOD  # ZonesNeeded = 156
M15_WINDOW = 45  # SDB_PA_BARS
TL_TOL_ATR = 0.2
TL_MIN_SLOPE_ATR = 0.02
PA_EPS = 1e-9
SESSION_FROM_H, SESSION_TO_H = 8, 22  # London + New York, jam akhir 22 UTC
RETEST_BARS = 20
RULES = osim.ExitRules(
    sl_buffer_atr=0.1,
    min_rr=2.0,
    min_sl_atr=0.3,
    max_sl_atr=3.0,
    be_r=1.0,
    be_buffer_pts=2,
    partial_r=1.5,
    partial_pct=50.0,
    trail_atr_period=14,
    trail_atr_mult=2.0,
)


# --- Data ---


@dataclass
class Ohlc:
    open: Any
    high: Any
    low: Any
    close: Any


def aggregate(bars: osim.Bars, tf_sec: int) -> osim.Bars:
    """M1 -> TF: waktu awal bar, open pertama, high maks, low min, close dan spread terakhir."""
    key = bars.time // tf_sec
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    ends = np.r_[starts[1:], len(key)] - 1
    spread = bars.spread[ends] if bars.spread is not None else None
    return osim.Bars(
        time=(key[starts] * tf_sec).astype(np.int64),
        open=bars.open[starts],
        high=np.maximum.reduceat(bars.high, starts),
        low=np.minimum.reduceat(bars.low, starts),
        close=bars.close[ends],
        point=bars.point,
        digits=bars.digits,
        spread=spread,
    )


def closed_count(times: npt.NDArray[Any], tf_sec: int, t_eval: int) -> int:
    """Jumlah bar yang sudah tutup pada t_eval (waktu awal + tf <= t_eval)."""
    return int(np.searchsorted(times + tf_sec, t_eval, side="right"))


def wilder_atr(
    h: npt.NDArray[Any], lo: npt.NDArray[Any], c: npt.NDArray[Any], period: int = ATR_PERIOD
) -> float:
    """AtrSeries EA (Wilder, benih SMA) nilai terakhir; 0 bila bar < 3 x periode."""
    n = len(c)
    if n < WARMUP * period:
        return 0.0
    tr = h - lo
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(lo[1:] - c[:-1])))
    atr = tr[:period].sum() / period
    for i in range(period, n):
        atr = (atr * (period - 1) + tr[i]) / period
    return float(atr)


# --- Struktur dan bias ---


@dataclass(frozen=True)
class Swing:
    index: int
    price: float
    is_high: bool


def find_swings(highs: npt.NDArray[Any], lows: npt.NDArray[Any], n: int) -> list[Swing]:
    """FindSwings: high > n kiri (ketat) dan >= n kanan; kanan harus lengkap. Urut indeks, high sebelum low."""
    out: list[Swing] = []
    last = len(highs) - 1
    for i in range(n, last - n + 1):
        hi = highs[i]
        if all(highs[i - k] < hi and highs[i + k] <= hi for k in range(1, n + 1)):
            out.append(Swing(i, float(hi), True))
        lo = lows[i]
        if all(lows[i - k] > lo and lows[i + k] >= lo for k in range(1, n + 1)):
            out.append(Swing(i, float(lo), False))
    return out


def structure_dir(close: npt.NDArray[Any], sw: list[Swing], n: int, lookback: int) -> int:
    """StructureOf: arah BOS terakhir di jendela (1 BULL, -1 BEAR, 0)."""
    last = len(close) - 1
    window_start = max(0, last - lookback + 1)
    broken_hi = broken_lo = -1
    out = 0
    for b in range(last + 1):
        hi = lo = -1
        for k, s in enumerate(sw):
            if s.index + n >= b:
                break
            if s.is_high:
                hi = k
            else:
                lo = k
        bos = 0
        if hi >= 0 and hi != broken_hi and close[b] > sw[hi].price:
            broken_hi, bos = hi, 1
        elif lo >= 0 and lo != broken_lo and close[b] < sw[lo].price:
            broken_lo, bos = lo, -1
        if bos and b >= window_start:
            out = bos
    return out


def ema_dir(closes: npt.NDArray[Any], period: int, slope_bars: int) -> int:
    """EmaSeries + EmaDirectionOf: close > EMA dan EMA naik dibanding slope_bars lalu = 1; kebalikan = -1."""
    n = len(closes)
    if period < 1 or n < WARMUP * period:
        return 0
    ema = np.zeros(n)
    ema[period - 1] = closes[:period].mean()
    alpha = 2.0 / (period + 1.0)
    for i in range(period, n):
        ema[i] = ema[i - 1] + alpha * (closes[i] - ema[i - 1])
    last = n - 1
    if last - slope_bars < 0:
        return 0
    now, before = ema[last], ema[last - slope_bars]
    if closes[last] > now > before:
        return 1
    if closes[last] < now < before:
        return -1
    return 0


def bias_of(structure: int, ema: int) -> int:
    """BiasOf mode AND_EMA."""
    return structure if structure != 0 and structure == ema else 0


def bias_at(h4: osim.Bars, n_closed: int) -> int:
    lo = max(0, n_closed - H4_WINDOW)
    if n_closed - lo < H4_WINDOW:
        return 0
    h, low, c = h4.high[lo:n_closed], h4.low[lo:n_closed], h4.close[lo:n_closed]
    sw = find_swings(h, low, STRENGTH)
    return bias_of(structure_dir(c, sw, STRENGTH, LOOKBACK), ema_dir(c, EMA_BIAS, EMA_SLOPE))


# --- Pola PA (PatternRules.mqh) ---


def _body(o: float, c: float) -> float:
    return abs(c - o)


def _dir(o: float, c: float) -> int:
    return 1 if c > o else (-1 if c < o else 0)


def detect_pattern(r: Ohlc, atr: float, d: int) -> str:
    """DetectPattern untuk bar terakhir dan arah d (1 BULL, -1 BEAR); urutan spesifik -> umum."""
    n = len(r.close)
    if n < 3 or atr <= 0 or d == 0 or r.high[-1] - r.low[-1] <= 0:
        return "NONE"
    o, h, lo, c = r.open, r.high, r.low, r.close
    i = n - 1
    tol = PA_EPS * atr

    def ge(a: float, b: float) -> bool:
        return a >= b - tol

    def gt(a: float, b: float) -> bool:
        return a > b + tol

    def engulf() -> bool:
        if _dir(o[i - 1], c[i - 1]) != -d or _dir(o[i], c[i]) != d:
            return False
        if not gt(_body(o[i], c[i]), _body(o[i - 1], c[i - 1])):
            return False
        if d == 1:
            return ge(c[i], o[i - 1]) and ge(c[i - 1], o[i])
        return ge(o[i - 1], c[i]) and ge(o[i], c[i - 1])

    first = _body(o[i - 2], c[i - 2])
    star = (
        _dir(o[i - 2], c[i - 2]) == -d
        and gt(first, 0.5 * atr)
        and not _body(o[i - 1], c[i - 1]) >= 0.3 * first - tol
        and _dir(o[i], c[i]) == d
        and (gt(c[i], (o[i - 2] + c[i - 2]) / 2) if d == 1 else gt((o[i - 2] + c[i - 2]) / 2, c[i]))
    )
    if star:
        return "STAR"
    body = _body(o[i], c[i])
    rng = h[i] - lo[i]
    if engulf():
        strong = (
            ge(body, 0.6 * rng)
            and ge(body, 0.8 * atr)
            and (gt(c[i], h[i - 1]) if d == 1 else gt(lo[i - 1], c[i]))
        )
        if strong:
            return "ENGULF_STRONG"
    lower = min(o[i], c[i]) - lo[i]
    upper = h[i] - max(o[i], c[i])
    wick, other = (lower, upper) if d == 1 else (upper, lower)
    if (
        ge(0.35 * rng, body)
        and ge(wick, 2.0 * body)
        and ge(wick, 0.6 * rng)
        and gt(wick, 2.0 * other)
        and ge(rng, 0.8 * atr)
    ):
        return "PIN"
    if engulf():
        return "ENGULF"
    if _dir(o[i - 1], c[i - 1]) == -d and _dir(o[i], c[i]) == d:
        diff = abs(lo[i] - lo[i - 1]) if d == 1 else abs(h[i] - h[i - 1])
        if ge(0.1 * atr, diff):
            return "TWEEZER"
    if gt(h[i], h[i - 1]) and gt(lo[i - 1], lo[i]) and _dir(o[i], c[i]) == d:
        if gt(c[i], c[i - 1]) if d == 1 else gt(c[i - 1], c[i]):
            return "OUTSIDE"
    return "NONE"


# --- Trendline (TrendlineRules.mqh) ---


@dataclass(frozen=True)
class Line:
    i1: int
    p1: float
    i2: int
    p2: float
    touches: int
    slope_atr: float
    t2: int

    def value_at(self, x: float) -> float:
        return self.p1 + (self.p2 - self.p1) / (self.i2 - self.i1) * (x - self.i1)


def _lines(
    h1: osim.Bars, end: int, buy: bool, atr: float, strength: int, lookback: int
) -> tuple[list[tuple[Line, int]], int]:
    """Semua garis searah yang tidak patah di jendela EA berakhir di `end`; indeks absolut. (garis, sentuhan pertama)."""
    lo = max(0, end - H1_WINDOW)
    n = end - lo
    if n < 2 * strength + 2 or atr <= 0:
        return [], lo
    h, low, c = h1.high[lo:end], h1.low[lo:end], h1.close[lo:end]
    sw = [s for s in find_swings(h, low, strength) if s.is_high != buy and s.index >= n - lookback]
    tol = TL_TOL_ATR * atr
    xs = np.arange(n)
    out: list[tuple[Line, int]] = []
    for a in range(len(sw)):
        for b in range(a + 1, len(sw)):
            i1, i2, p1, p2 = sw[a].index, sw[b].index, sw[a].price, sw[b].price
            slope = (p2 - p1) / (i2 - i1) / atr
            if (slope < TL_MIN_SLOPE_ATR) if buy else (slope > -TL_MIN_SLOPE_ATR):
                continue
            touches, first = 0, i1
            for s in sw:
                if abs(s.price - (p1 + (p2 - p1) / (i2 - i1) * (s.index - i1))) <= tol + 1e-12:
                    touches += 1
                    first = min(first, s.index)
            line_v = p1 + (p2 - p1) / (i2 - i1) * (xs[first:] - i1)
            seg = c[first:]
            broken = (
                np.any(seg < line_v - tol - 1e-12) if buy else np.any(seg > line_v + tol + 1e-12)
            )
            if broken:
                continue
            ln = Line(lo + i1, p1, lo + i2, p2, touches, slope, int(h1.time[lo + i2]))
            out.append((ln, lo + first))
    return out, lo


def _best(cands: list[Line]) -> Line | None:
    best: Line | None = None
    for ln in cands:
        if (
            best is None
            or ln.touches > best.touches
            or (
                ln.touches == best.touches
                and (ln.i2 > best.i2 or (ln.i2 == best.i2 and ln.i1 > best.i1))
            )
        ):
            best = ln
    return best


def trendline(
    h1: osim.Bars,
    end: int,
    buy: bool,
    atr: float,
    strength: int = STRENGTH,
    lookback: int = LOOKBACK,
) -> Line | None:
    """Garis terbaik (sentuhan terbanyak, lalu terbaru) tanpa syarat zona; dipakai setup A dan C."""
    lines, _ = _lines(h1, end, buy, atr, strength, lookback)
    return _best([ln for ln, _ in lines])


def tl_vs_zone(
    h1: osim.Bars, end: int, buy: bool, atr: float, zone_lo: float, zone_hi: float
) -> tuple[int, float]:
    """TlEvaluate EA (dengan jarak garis ke zona di bar `end`): (sentuhan, jarak/ATR); (0, -1) bila tidak ada garis."""
    lines, _ = _lines(h1, end, buy, atr, STRENGTH, LOOKBACK)
    tol = TL_TOL_ATR * atr
    ok = []
    for ln, _ in lines:
        v = ln.value_at(end)
        dist = zone_lo - v if v < zone_lo else (v - zone_hi if v > zone_hi else 0.0)
        if dist <= tol + 1e-12:
            ok.append((ln, dist))
    best = _best([ln for ln, _ in ok])
    if best is None:
        return 0, -1.0
    return best.touches, next(d for ln, d in ok if ln is best) / atr


# --- Setup ---


@dataclass(frozen=True)
class Signal:
    anchor: float
    pattern: str


def setup_a_signal(
    bar: Ohlc, line: Line, x: float, buy: bool, atr_h1: float, atr_m15: float
) -> Signal | None:
    """Setup A: ekstrem bar M15 terakhir dalam 0,2 ATR H1 dari garis + pola searah; jangkar SL = ekstrem/garis terjauh."""
    lv = line.value_at(x)
    tol = TL_TOL_ATR * atr_h1
    extreme = bar.low[-1] if buy else bar.high[-1]
    if abs(extreme - lv) > tol + 1e-12:
        return None
    pat = detect_pattern(bar, atr_m15, 1 if buy else -1)
    if pat == "NONE":
        return None
    return Signal(min(extreme, lv) if buy else max(extreme, lv), pat)


@dataclass
class BreakState:
    bar_index: int
    direction: int  # arah entry: -1 support patah (SELL), 1 resistance patah (BUY)
    line: Line


@dataclass
class BreakTracker:
    max_bars: int
    state: BreakState | None = None

    def on_break(self, bar_index: int, direction: int, line: Line) -> None:
        self.state = BreakState(bar_index, direction, line)

    def active(self, bar_index: int) -> BreakState | None:
        if self.state is None or bar_index - self.state.bar_index > self.max_bars:
            self.state = None
            return None
        return self.state


def sequential(times: list[int], close_of: Callable[[int], int]) -> list[int]:
    """Satu posisi per simbol: kandidat sebelum posisi sebelumnya tutup dilewati."""
    taken: list[int] = []
    busy_until = -1
    for t in times:
        if t < busy_until:
            continue
        taken.append(t)
        busy_until = close_of(t)
    return taken


@dataclass
class Trade:
    setup: str
    symbol: str
    time: int
    direction: str
    pattern: str
    outcome: osim.Outcome


@dataclass
class SymbolData:
    m1: osim.Bars
    m15: osim.Bars
    h1: osim.Bars
    h4: osim.Bars
    atr15: osim.Atr
    h1_cache: dict[int, tuple[float, Line | None, Line | None]] = field(default_factory=dict)
    h4_cache: dict[int, int] = field(default_factory=dict)

    def h1_state(self, n: int) -> tuple[float, Line | None, Line | None]:
        if n not in self.h1_cache:
            lo = max(0, n - H1_WINDOW)
            atr = wilder_atr(
                self.h1.high[lo:n].copy(), self.h1.low[lo:n].copy(), self.h1.close[lo:n].copy()
            )
            self.h1_cache[n] = (
                atr,
                trendline(self.h1, n, True, atr) if atr > 0 else None,
                trendline(self.h1, n, False, atr) if atr > 0 else None,
            )
        return self.h1_cache[n]

    def bias(self, n4: int) -> int:
        if n4 not in self.h4_cache:
            self.h4_cache[n4] = bias_at(self.h4, n4)
        return self.h4_cache[n4]


def load_symbol(bars_dir: Path, symbol: str) -> SymbolData | None:
    csv = bars_dir / f"{symbol}_M1.csv"
    if not csv.is_file():
        return None
    m1 = osim.load_bars(csv)
    return SymbolData(
        m1, aggregate(m1, 900), aggregate(m1, 3600), aggregate(m1, 14400), osim.m15_atr(m1, 14)
    )


def _m15_window(d: SymbolData, j: int) -> tuple[Ohlc, float]:
    lo = max(0, j + 1 - M15_WINDOW)
    h, low, c, o = (
        d.m15.high[lo : j + 1],
        d.m15.low[lo : j + 1],
        d.m15.close[lo : j + 1],
        d.m15.open[lo : j + 1],
    )
    atr = wilder_atr(h.copy(), low.copy(), c.copy()) if j + 1 - lo >= M15_WINDOW else 0.0
    return Ohlc(o, h, low, c), atr


def candidates(
    d: SymbolData, symbol: str, t_from: int, t_to: int, use_bias: bool
) -> list[tuple[str, osim.Candidate, str]]:
    """Kandidat setup A dan C urut waktu dalam [t_from, t_to)."""
    out: list[tuple[str, osim.Candidate, str]] = []
    trackers = {True: BreakTracker(RETEST_BARS), False: BreakTracker(RETEST_BARS)}
    prev_lines: dict[bool, Line | None] = {True: None, False: None}
    j0 = int(np.searchsorted(d.m15.time, t_from - 60 * 86400))
    j1 = int(np.searchsorted(d.m15.time, t_to))
    for j in range(max(j0, 3), j1):
        t = int(d.m15.time[j])
        t_eval = t + 900
        n1 = closed_count(d.h1.time, 3600, t_eval)
        atr_h1, sup, res = d.h1_state(n1)
        if atr_h1 <= 0:
            continue
        bar, atr_m15 = _m15_window(d, j)
        tol = TL_TOL_ATR * atr_h1
        close = float(d.m15.close[j])
        # tembusan garis jam sebelumnya (setup C)
        for buy_line, line in ((True, prev_lines[True]), (False, prev_lines[False])):
            if line is None:
                continue
            lv = line.value_at(n1)
            if buy_line and close < lv - tol - 1e-12:
                trackers[True].on_break(j, -1, line)
            if not buy_line and close > lv + tol + 1e-12:
                trackers[False].on_break(j, 1, line)
        prev_lines = {True: sup, False: res}
        hour = (t % 86400) // 3600
        if not (SESSION_FROM_H <= hour < SESSION_TO_H) or t < t_from or atr_m15 <= 0:
            continue
        bias = d.bias(closed_count(d.h4.time, 14400, t_eval)) if use_bias else 0
        spread = float(d.m15.spread[j]) * d.m15.point if d.m15.spread is not None else 0.0
        for buy, line in ((True, sup), (False, res)):
            if line is None or (use_bias and bias != (1 if buy else -1)):
                continue
            sig = setup_a_signal(bar, line, n1, buy, atr_h1, atr_m15)
            if sig is not None:
                out.append(
                    ("A", _cand(symbol, t, buy, sig.anchor, close, spread, atr_h1, d), sig.pattern)
                )
        for key in (True, False):
            st = trackers[key].active(j)
            if st is None or st.bar_index == j:
                continue
            buy = st.direction == 1
            if use_bias and bias != st.direction:
                continue
            lv = st.line.value_at(n1)
            touched = (
                (bar.low[-1] <= lv + tol and close > lv)
                if buy
                else (bar.high[-1] >= lv - tol and close < lv)
            )
            if not touched:
                continue
            pat = detect_pattern(bar, atr_m15, st.direction)
            if pat == "NONE":
                continue
            anchor = float(bar.low[-1]) if buy else float(bar.high[-1])
            out.append(("C", _cand(symbol, t, buy, anchor, close, spread, atr_h1, d), pat))
            trackers[key].state = None
    return out


def _cand(
    symbol: str,
    t: int,
    buy: bool,
    anchor: float,
    close: float,
    spread: float,
    atr: float,
    d: SymbolData,
) -> osim.Candidate:
    return osim.Candidate(
        signal_id=t,
        session_id=0,
        symbol=symbol,
        time=t,
        direction="BUY" if buy else "SELL",
        stage=None,
        zone_prox=anchor,
        zone_dist=anchor,
        opp_prox=None,
        bid=close,
        ask=close + spread,
        atr_mtf=atr,
        point=d.m15.point,
        digits=d.m15.digits,
    )


def run_symbol(d: SymbolData, symbol: str, t_from: int, t_to: int, use_bias: bool) -> list[Trade]:
    """Simulasi berurutan per setup: setup baru selama posisi setup yang sama masih terbuka dilewati."""
    trades: list[Trade] = []
    for setup in ("A", "C"):
        busy = -1
        for s, c, pat in candidates(d, symbol, t_from, t_to, use_bias):
            if s != setup or c.time < t_from or c.time < busy:
                continue
            if not osim.build_stops(c, RULES).passes_rules:
                continue
            o = osim.simulate(c, RULES, d.m1, d.atr15)
            busy = o.closed_at or c.time
            trades.append(Trade(setup, symbol, c.time, c.direction, pat, o))
    return trades


# --- Laporan ---


def summarize(rs: list[float], months: float) -> dict[str, float]:
    if not rs:
        return {"n": 0, "per_month": 0.0, "r": 0.0, "total": 0.0, "pf": 0.0, "dd": 0.0}
    win = sum(r for r in rs if r > 0)
    loss = -sum(r for r in rs if r < 0)
    eq = peak = dd = 0.0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {
        "n": len(rs),
        "per_month": len(rs) / months if months > 0 else 0.0,
        "r": sum(rs) / len(rs),
        "total": sum(rs),
        "pf": win / loss if loss > 0 else float("inf"),
        "dd": dd,
    }


def passes_is(s: dict[str, float]) -> bool:
    return s["n"] >= 100 and s["r"] >= 0.10 and s["pf"] >= 1.20


def _periods(names: list[str], ini: Path) -> dict[str, tuple[int, int]]:
    sec = ""
    data: dict[str, dict[str, str]] = {}
    for line in ini.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            sec = line[1:-1]
            data[sec] = {}
        elif "=" in line and sec and not line.startswith(";"):
            k, v = line.split("=", 1)
            data[sec][k.strip()] = v.strip()
    out = {}
    for n in names:
        f = datetime.strptime(data[n]["FromDate"], "%Y.%m.%d").replace(tzinfo=UTC)
        t = datetime.strptime(data[n]["ToDate"], "%Y.%m.%d").replace(tzinfo=UTC)
        out[n] = (int(f.timestamp()), int(t.timestamp()))
    return out


def setup_b(conn: sqlite3.Connection, ranges: list[tuple[int, int]]) -> list[float]:
    """Setup B: trade EA dengan trendline di zona (tl_touches >= 2, tl_dist <= 0,2)."""
    cond, params = _where("t.session_id", ranges)
    rows = conn.execute(
        f"SELECT s.context_json, c.r_result FROM {CLOSED_EA_FROM} JOIN signals s ON s.id = t.signal_id "
        f"WHERE {CLOSED_EA_WHERE} AND {cond}",
        params,
    ).fetchall()
    out = []
    for ctx_json, r in rows:
        ctx = json.loads(ctx_json or "{}")
        if (ctx.get("tl_touches") or 0) >= 2 and (
            ctx.get("tl_dist") if ctx.get("tl_dist") is not None else 9
        ) <= TL_TOL_ATR:
            out.append(float(r))
    return out


def verify(
    conn: sqlite3.Connection, ranges: list[tuple[int, int]], bars_dir: Path
) -> dict[str, tuple[int, int]]:
    """Cocokkan pola PA, bias, dan trendline lab dengan context_json kandidat EA (Req 1.3)."""
    cond, params = _where("session_id", ranges)
    rows = conn.execute(
        f"SELECT symbol, time, direction, context_json FROM signals WHERE {cond} AND context_json IS NOT NULL",
        params,
    ).fetchall()
    stats = {"pa": [0, 0], "bias": [0, 0], "tl": [0, 0]}
    cache: dict[str, SymbolData | None] = {}
    for symbol, t, direction, ctx_json in rows:
        if symbol not in cache:
            cache[symbol] = load_symbol(bars_dir, symbol)
        d = cache[symbol]
        if d is None:
            continue
        ctx = json.loads(ctx_json)
        j = int(np.searchsorted(d.m15.time, t))
        if j >= len(d.m15.time) or int(d.m15.time[j]) != t:
            continue
        dsign = 1 if direction == "BUY" else -1
        bar, atr_m15 = _m15_window(d, j)
        if ctx.get("pa") is not None and atr_m15 > 0:
            stats["pa"][1] += 1
            stats["pa"][0] += detect_pattern(bar, atr_m15, dsign) == ctx["pa"]
        n4 = closed_count(d.h4.time, 14400, t + 900)
        stats["bias"][1] += 1
        stats["bias"][0] += d.bias(n4) == dsign
        if ctx.get("zone_prox") is not None and ctx.get("tl_touches") is not None:
            n1 = closed_count(d.h1.time, 3600, t + 900)
            atr_h1 = d.h1_state(n1)[0]
            zlo, zhi = sorted((float(ctx["zone_prox"]), float(ctx["zone_dist"])))
            touches, dist = tl_vs_zone(d.h1, n1, dsign == 1, atr_h1, zlo, zhi)
            stats["tl"][1] += 1
            stats["tl"][0] += (
                touches == int(ctx["tl_touches"])
                and abs(dist - float(ctx["tl_dist"])) <= 0.02 + 1e-9
            )
    return {k: (v[0], v[1]) for k, v in stats.items()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("verify")
    pv.add_argument("--db", required=True, type=Path)
    pv.add_argument("--bars", required=True, type=Path)
    pv.add_argument("--runs", action="append", required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--bars", required=True, type=Path)
    pr.add_argument("--db", type=Path, help="DB tester untuk setup B")
    pr.add_argument(
        "--b-runs",
        action="append",
        default=[],
        help="NAMA=A-B sesi acuan untuk setup B per periode",
    )
    pr.add_argument("--period", action="append", required=True, choices=("IS", "OOS", "REAL"))
    pr.add_argument(
        "--symbols",
        default="AUDUSDc,BTCUSDc,EURJPYc,EURUSDc,GBPJPYc,GBPUSDc,NZDUSDc,USDCADc,USDCHFc,USDJPYc,XAGUSDc,XAUUSDc",
    )
    pr.add_argument(
        "--periods-ini",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "ea" / "tests" / "baseline" / "periods.ini",
    )
    args = ap.parse_args(argv)
    if args.cmd == "verify":
        vconn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
        try:
            for name, ranges in parse_runs(args.runs):
                st = verify(vconn, ranges, args.bars)
                ok = (
                    st["pa"][0] >= 0.95 * st["pa"][1]
                    and st["bias"][0] >= 0.95 * st["bias"][1]
                    and st["tl"][0] >= 0.90 * st["tl"][1]
                )
                print(
                    f"{name}: "
                    + ", ".join(
                        f"{k} {a}/{b} ({100 * a / b if b else 0:.1f}%)" for k, (a, b) in st.items()
                    )
                    + f" -> {'LOLOS' if ok else 'GAGAL'}"
                )
        finally:
            vconn.close()
        return 0
    periods = _periods(args.period, args.periods_ini)
    data = {s: load_symbol(args.bars, s) for s in args.symbols.split(",")}
    b_runs = dict(parse_runs(args.b_runs)) if args.b_runs else {}
    conn: sqlite3.Connection | None = (
        sqlite3.connect(f"file:{args.db}?mode=ro", uri=True) if args.db else None
    )
    print(
        f"{'setup':<6} {'bias':<5} {'periode':<6} {'trade':>6} {'/bln':>5} {'R/trade':>8} {'total':>7} {'PF':>5} {'DD':>6}  IS"
    )
    per_symbol: dict[tuple[str, bool, str], dict[str, list[float]]] = {}
    for pname, (f, t) in periods.items():
        months = (t - f) / (30.4375 * 86400)
        for use_bias in (True, False):
            trades: list[Trade] = []
            for sym, d in data.items():
                if d is not None:
                    trades += run_symbol(d, sym, f, t, use_bias)
            for setup in ("A", "C"):
                sel = sorted((x for x in trades if x.setup == setup), key=lambda x: x.time)
                s = summarize([x.outcome.r for x in sel], months)
                mark = ("LOLOS" if passes_is(s) else "-") if pname == "IS" else ""
                print(
                    f"{setup:<6} {'ya' if use_bias else 'tidak':<5} {pname:<6} {s['n']:>6} {s['per_month']:>5.1f} {s['r']:>+8.3f} {s['total']:>+7.1f} {s['pf']:>5.2f} {s['dd']:>6.1f}  {mark}"
                )
                bysym = per_symbol.setdefault((setup, use_bias, pname), {})
                for x in sel:
                    bysym.setdefault(x.symbol, []).append(x.outcome.r)
        if conn is not None and pname in b_runs:
            s = summarize(setup_b(conn, b_runs[pname]), months)
            print(
                f"{'B':<6} {'ya':<5} {pname:<6} {s['n']:>6} {s['per_month']:>5.1f} {s['r']:>+8.3f} {s['total']:>+7.1f} {s['pf']:>5.2f} {s['dd']:>6.1f}"
            )
    print("\nper simbol (trade, R/trade):")
    for (setup, use_bias, pname), m in sorted(per_symbol.items()):
        print(
            f"{setup} bias={'ya' if use_bias else 'tidak'} {pname}: "
            + " ".join(f"{s[:6]}:{len(v)}({sum(v) / len(v):+.2f})" for s, v in sorted(m.items()))
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
