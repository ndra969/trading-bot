"""Lab strategi kedua untuk frekuensi (spec 38, H11).

Tiga setup intraday tanpa zona S&D di atas bar M1 ekspor (spec 31) dengan port aturan EA dari
`trendline_lab` (spec 32) dan exit lewat `outcome_sim.simulate` (BE/partial dimatikan, TP tetap):

- S1 London breakout: range Asia 00:00-07:00 UTC ditembus close M15 07:00-11:00.
- S2 New York opening range: range 13:30-14:00 UTC ditembus close M15 14:00-17:00.
- S3 pullback EMA 21 H1 searah bias H4 dengan pola PA M15, sesi London/NY.

Jam server Broker B = UTC (diperiksa 2026-10-14; TS-137), jadi waktu bar dipakai apa adanya.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import outcome_sim as osim
import trendline_lab as tl

DEFAULT_BARS_DIR = (
    Path(os.environ.get("APPDATA", ""))
    / "MetaQuotes"
    / "Terminal"
    / "Common"
    / "Files"
    / "sdbot_bars"
)

DAY = 86400
HOUR = 3600
FRIDAY_CLOSE_SEC = 21 * HOUR + 45 * 60  # Req 5.4: 21:45 UTC Jumat
EPOCH_WEEKDAY_THU = 3  # 1970-01-01 = Kamis; Senin = 0
FRIDAY = 4
NO_BE_R = 99.0  # BE dan partial tidak pernah tercapai -> SL/TP murni (Req 5.1)


def _rules(rr: float) -> osim.ExitRules:
    return osim.ExitRules(
        sl_buffer_atr=0.1,
        min_rr=rr,
        min_sl_atr=0.3,
        max_sl_atr=3.0,
        be_r=NO_BE_R,
        be_buffer_pts=2,
        partial_r=NO_BE_R,
        partial_pct=50.0,
        trail_atr_period=14,
        trail_atr_mult=2.0,
    )


TP_VARIANTS = (1.5, 2.0)
LAB_RULES = {rr: _rules(rr) for rr in TP_VARIANTS}


def friday_close(t: int, crypto: bool) -> int | None:
    """Jumat 21:45 UTC pertama sesudah t (Req 5.4); None untuk crypto (EC-05)."""
    if crypto:
        return None
    day0 = t - t % DAY
    weekday = (day0 // DAY + EPOCH_WEEKDAY_THU) % 7
    cut = day0 + ((FRIDAY - weekday) % 7) * DAY + FRIDAY_CLOSE_SEC
    return cut if cut > t else cut + 7 * DAY


# --- Range sesi dan breakout (Req 2, 3) ---

MAX_RANGE_GAP_SEC = 30 * 60  # EC-02: celah data > 30 menit di jendela range -> hari dilewati
BREAK_ATR = 0.1  # tembus = close di luar range > 0,1 ATR H1
M1_SEC = 60
M15_SEC = 900


@dataclass(frozen=True)
class Range:
    high: float
    low: float


@dataclass(frozen=True)
class RangeSpec:
    name: str
    range_from: int  # detik sejak 00:00 UTC
    range_to: int
    win_from: int  # awal bar M15 yang boleh menjadi sinyal
    win_to: int
    min_width_atr: float
    max_width_atr: float


S1 = RangeSpec("S1", 0, 7 * HOUR, 7 * HOUR, 11 * HOUR, 0.5, 2.5)
S2 = RangeSpec("S2", 13 * HOUR + 30 * 60, 14 * HOUR, 14 * HOUR, 17 * HOUR, 0.3, 2.0)


@dataclass(frozen=True)
class Signal:
    setup: str
    time: int  # awal bar M15 sinyal; entry di open bar berikutnya
    direction: str
    anchor: float  # jangkar SL (build_stops menambah 0,1 ATR, SELL + spread)
    pattern: str = ""
    tp: float | None = None  # spec 40: TP tetap di harga (garis tengah BB); None = TP min_rr x R


def session_range(m1: osim.Bars, day_start: int, start_sec: int, end_sec: int) -> Range | None:
    """High/low bar M1 dalam [awal, akhir); None bila tidak ada bar atau ada celah > 30 menit."""
    a, b = day_start + start_sec, day_start + end_sec
    i0 = int(np.searchsorted(m1.time, a, side="left"))
    i1 = int(np.searchsorted(m1.time, b, side="left"))
    if i1 <= i0:
        return None
    t = np.concatenate(([a - M1_SEC], m1.time[i0:i1], [b]))
    if np.max(np.diff(t)) > MAX_RANGE_GAP_SEC + M1_SEC:
        return None
    return Range(float(np.max(m1.high[i0:i1])), float(np.min(m1.low[i0:i1])))


def range_signal(
    m1: osim.Bars, m15: osim.Bars, day_start: int, spec: RangeSpec, atr: float
) -> Signal | None:
    """Tembusan pertama close M15 di luar range +- 0,1 ATR dalam jendela (Req 2.1-2.3, 3.1-3.3, EC-03)."""
    if atr <= 0:
        return None
    rng = session_range(m1, day_start, spec.range_from, spec.range_to)
    if rng is None:
        return None
    width = rng.high - rng.low
    if width < spec.min_width_atr * atr or width > spec.max_width_atr * atr:
        return None
    j0 = int(np.searchsorted(m15.time, day_start + spec.win_from, side="left"))
    j1 = int(np.searchsorted(m15.time, day_start + spec.win_to, side="left"))
    for j in range(j0, j1):
        close = float(m15.close[j])
        if close > rng.high + BREAK_ATR * atr:
            return Signal(spec.name, int(m15.time[j]), "BUY", rng.low)
        if close < rng.low - BREAK_ATR * atr:
            return Signal(spec.name, int(m15.time[j]), "SELL", rng.high)
    return None


# --- Data per simbol (port spec 32) dan S3 pullback EMA H1 (Req 1, 4) ---

H1_SEC = 3600
H4_SEC = 4 * 3600
EMA_PULLBACK = 21
EMA_WINDOW = 200  # bar H1 untuk EMA 21 (>= 3 x periode, konvergen)
PULLBACK_ATR = 0.2  # Req 4.1: low/high dalam 0,2 ATR H1 dari EMA


@dataclass
class LabData:
    m1: osim.Bars
    m15: osim.Bars
    h1: osim.Bars
    h4: osim.Bars
    atr15: osim.Atr
    crypto: bool
    _atr: dict[int, float]
    _ema: dict[int, float]
    _bias: dict[int, int]

    def atr_h1(self, n1: int) -> float:
        """ATR(14) H1 Wilder EA atas n1 bar H1 tertutup (jendela spec 32)."""
        if n1 not in self._atr:
            lo = max(0, n1 - tl.H1_WINDOW)
            h, low, c = self.h1.high[lo:n1], self.h1.low[lo:n1], self.h1.close[lo:n1]
            self._atr[n1] = tl.wilder_atr(h.copy(), low.copy(), c.copy())
        return self._atr[n1]

    def ema_h1(self, n1: int) -> float:
        if n1 not in self._ema:
            self._ema[n1] = ema_last(self.h1.close[max(0, n1 - EMA_WINDOW) : n1], EMA_PULLBACK)
        return self._ema[n1]

    def bias(self, n4: int) -> int:
        if n4 not in self._bias:
            self._bias[n4] = tl.bias_at(self.h4, n4)
        return self._bias[n4]


def _lab_from_m1(m1: osim.Bars, symbol: str) -> LabData:
    return LabData(
        m1,
        tl.aggregate(m1, M15_SEC),
        tl.aggregate(m1, H1_SEC),
        tl.aggregate(m1, H4_SEC),
        osim.m15_atr(m1, 14),
        symbol.startswith(("BTC", "ETH")),
        {},
        {},
        {},
    )


def load_lab(bars_dir: Path, symbol: str) -> LabData | None:
    csv = bars_dir / f"{symbol}_M1.csv"
    return _lab_from_m1(osim.load_bars(csv), symbol) if csv.is_file() else None


def truncate(d: LabData, t: int) -> LabData:
    """Data sampai sebelum t (uji tanpa lookahead, TS-142)."""
    n = int(np.searchsorted(d.m1.time, t, side="left"))
    m = d.m1
    sp = m.spread[:n] if m.spread is not None else None
    cut = osim.Bars(
        m.time[:n], m.open[:n], m.high[:n], m.low[:n], m.close[:n], m.point, m.digits, sp
    )
    out = _lab_from_m1(cut, "")
    out.crypto = d.crypto
    return out


def ema_last(closes: np.ndarray, period: int) -> float:
    """EmaSeries EA (benih SMA) nilai terakhir; 0 bila bar < 3 x periode."""
    n = len(closes)
    if n < tl.WARMUP * period:
        return 0.0
    ema = float(closes[:period].mean())
    alpha = 2.0 / (period + 1.0)
    for i in range(period, n):
        ema += alpha * (float(closes[i]) - ema)
    return ema


def s3_decision(
    bar: tl.Ohlc, atr_m15: float, ema: float, atr_h1: float, bias: int, hour: int
) -> tuple[str, float, str] | None:
    """Req 4.1-4.3: arah, jangkar SL, pola; None bila tidak ada setup."""
    if bias == 0 or ema <= 0 or atr_h1 <= 0 or not (tl.SESSION_FROM_H <= hour < tl.SESSION_TO_H):
        return None
    edge = float(bar.low[-1]) if bias == 1 else float(bar.high[-1])
    if abs(edge - ema) > PULLBACK_ATR * atr_h1:
        return None
    pattern = tl.detect_pattern(bar, atr_m15, bias)
    if pattern == "NONE":
        return None
    return ("BUY" if bias == 1 else "SELL", edge, pattern)


def setup_s3_at(d: LabData, j: int) -> Signal | None:
    t = int(d.m15.time[j])
    t_eval = t + M15_SEC
    hour = (t % DAY) // HOUR
    if not (tl.SESSION_FROM_H <= hour < tl.SESSION_TO_H):
        return None
    bias = d.bias(tl.closed_count(d.h4.time, H4_SEC, t_eval))
    if bias == 0:
        return None
    n1 = tl.closed_count(d.h1.time, H1_SEC, t_eval)
    ema, atr_h1 = d.ema_h1(n1), d.atr_h1(n1)
    edge = float(d.m15.low[j]) if bias == 1 else float(d.m15.high[j])
    if ema <= 0 or atr_h1 <= 0 or abs(edge - ema) > PULLBACK_ATR * atr_h1:
        return None
    bar, atr_m15 = tl._m15_window(d, j)  # type: ignore[arg-type]
    res = s3_decision(bar, atr_m15, ema, atr_h1, bias, hour)
    return None if res is None else Signal("S3", t, res[0], res[1], res[2])


def setup_range_day(d: LabData, day_start: int, spec: RangeSpec) -> Signal | None:
    n1 = tl.closed_count(d.h1.time, H1_SEC, day_start + spec.win_from)
    return range_signal(d.m1, d.m15, day_start, spec, d.atr_h1(n1))


def signals(d: LabData, t_from: int, t_to: int) -> list[Signal]:
    """Semua sinyal S1, S2, S3 dengan waktu bar dalam [t_from, t_to), urut waktu."""
    out: list[Signal] = []
    for day in range(t_from - t_from % DAY, t_to, DAY):
        for spec in (S1, S2):
            s = setup_range_day(d, day, spec)
            if s is not None and t_from <= s.time < t_to:
                out.append(s)
    j0 = int(np.searchsorted(d.m15.time, t_from, side="left"))
    j1 = int(np.searchsorted(d.m15.time, t_to, side="left"))
    for j in range(max(j0, 3), j1):
        s3 = setup_s3_at(d, j)
        if s3 is not None:
            out.append(s3)
    return sorted(out, key=lambda s: (s.time, s.setup))


# --- Kandidat, filter, simulasi berurutan, gabungan, aturan lolos (Req 5, 6) ---

MAX_SPREAD_SHARE = 0.15  # Req 5.3: spread saat entry <= 15% R
IS_MIN_TRADES = 120  # Req 6.2
IS_MIN_R = 0.10
IS_MIN_PF = 1.20
IS_MIN_POSITIVE_SYMBOLS = 7
CONFIRM_MIN_R = 0.05  # Req 6.3


@dataclass(frozen=True)
class LabTrade:
    setup: str
    symbol: str
    time: int  # awal bar M15 sinyal
    direction: str
    r: float
    reason: str
    closed_at: int
    pattern: str
    spread_r: float = 0.0  # spread saat entry dibagi R


@dataclass(frozen=True)
class EaTrade:
    symbol: str
    opened_at: int
    closed_at: int
    r: float


@dataclass(frozen=True)
class Merged:
    source: str  # EA atau LAB
    symbol: str
    time: int
    closed_at: int
    r: float


def to_candidate(
    sig: Signal,
    symbol: str,
    close: float,
    spread: float,
    atr_h1: float,
    point: float,
    digits: int,
    tp: float | None = None,
) -> osim.Candidate:
    """Kandidat simulator: jangkar SL di zone_dist; TP = tp (opp_prox) atau min_rr x R bila None; ask = bid + spread."""
    return osim.Candidate(
        signal_id=sig.time,
        session_id=0,
        symbol=symbol,
        time=sig.time,
        direction=sig.direction,
        stage=None,
        zone_prox=sig.anchor,
        zone_dist=sig.anchor,
        opp_prox=tp,
        bid=close,
        ask=close + spread,
        atr_mtf=atr_h1,
        point=point,
        digits=digits,
    )


def spread_share(spread: float, risk: float) -> float:
    return spread / risk if risk > 0 else float("inf")


def spread_too_wide(spread: float, risk: float) -> bool:
    return spread_share(spread, risk) > MAX_SPREAD_SHARE + 1e-9


def filter_candidate(c: osim.Candidate, x: osim.ExitRules) -> str | None:
    """Alasan kandidat dilewati (Req 5.2, 5.3): SL_RANGE atau SPREAD; None bila lolos."""
    st = osim.build_stops(c, x)
    # Batas jarak SL saja (Req 5.2). passes_rules juga menguji R:R TP yang sudah dibulatkan ke digit, dan TP
    # tetap 1,5R bisa jatuh ke 1,4999R sehingga kandidat sah tertolak (bug run IS 2026-10-15, TS-144b).
    eps = 1e-9 * c.atr_mtf
    lo = max(c.ask - c.bid, x.min_sl_atr * c.atr_mtf)
    if st.risk <= 0 or st.risk < lo - eps or st.risk > x.max_sl_atr * c.atr_mtf + eps:
        return "SL_RANGE"
    if spread_too_wide(c.ask - c.bid, st.risk):
        return "SPREAD"
    return None


def run_sequential(sigs: list[Signal], sim: Callable[[Signal], LabTrade | None]) -> list[LabTrade]:
    """Satu posisi per simbol per setup (Req 5.5): sinyal sebelum posisi setup itu tutup dilewati."""
    busy: dict[str, int] = {}
    out: list[LabTrade] = []
    for s in sorted(sigs, key=lambda x: (x.time, x.setup)):
        if s.time < busy.get(s.setup, -1):
            continue
        t = sim(s)
        if t is None:
            continue
        busy[s.setup] = t.closed_at or s.time
        out.append(t)
    return out


def combine(ea: list[EaTrade], lab: list[LabTrade]) -> list[Merged]:
    """Req 6.4: trade EA selalu dipertahankan; trade lab yang tumpang tindih posisi EA di simbol sama dilewati."""
    out = [Merged("EA", e.symbol, e.opened_at, e.closed_at, e.r) for e in ea]
    for t in lab:
        clash = any(
            e.symbol == t.symbol
            and e.opened_at < max(t.closed_at, t.time + 1)
            and t.time < e.closed_at
            for e in ea
        )
        if not clash:
            out.append(Merged("LAB", t.symbol, t.time, t.closed_at, t.r))
    return sorted(out, key=lambda m: m.time)


def ea_trades(db: Path, ranges: list[tuple[int, int]]) -> list[EaTrade]:
    """Trade EA tertutup dari tester DB (read-only) untuk rentang sesi."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        out: list[EaTrade] = []
        for a, b in ranges:
            rows = con.execute(
                "SELECT t.symbol, t.opened_at, c.closed_at, c.r_result FROM trades t JOIN closures c "
                "ON c.position_id = t.position_id AND c.session_id = t.session_id "
                "WHERE t.session_id BETWEEN ? AND ? AND c.r_result IS NOT NULL",
                (a, b),
            ).fetchall()
            out += [EaTrade(str(r[0]), int(r[1]), int(r[2]), float(r[3])) for r in rows]
        return out
    finally:
        con.close()


def passes_is(s: dict[str, float], per_symbol_total: dict[str, float]) -> bool:
    positive = sum(1 for v in per_symbol_total.values() if v > 0)
    return (
        s["n"] >= IS_MIN_TRADES
        and s["r"] >= IS_MIN_R - 1e-9
        and s["pf"] >= IS_MIN_PF - 1e-9
        and positive >= IS_MIN_POSITIVE_SYMBOLS
    )


def passes_confirm(s: dict[str, float]) -> bool:
    return s["r"] >= CONFIRM_MIN_R - 1e-9 and s["total"] > 0


# --- Simulasi per simbol, laporan, CLI (Req 6.1) ---

SETUPS = ("S1", "S2", "S3")
DEFAULT_SYMBOLS = "AUDUSDc,BTCUSDc,EURJPYc,EURUSDc,GBPJPYc,GBPUSDc,NZDUSDc,USDCADc,USDCHFc,USDJPYc,XAGUSDc,XAUUSDc"
DEFAULT_PERIODS_INI = (
    Path(__file__).resolve().parents[1] / "ea" / "tests" / "baseline" / "periods.ini"
)
MONTH_SEC = 30.4375 * DAY


def run_symbol(
    d: LabData, symbol: str, sigs: list[Signal], rr: float, skipped: Counter[str]
) -> list[LabTrade]:
    """Simulasi berurutan satu simbol untuk satu varian TP; kandidat yang dilewati dihitung di `skipped`."""
    x = LAB_RULES[rr]

    def sim(s: Signal) -> LabTrade | None:
        j = int(np.searchsorted(d.m15.time, s.time, side="left"))
        if j >= len(d.m15.time) or int(d.m15.time[j]) != s.time:
            skipped[f"{s.setup} NO_BAR"] += 1
            return None
        close = float(d.m15.close[j])
        spread = float(d.m15.spread[j]) * d.m15.point if d.m15.spread is not None else 0.0
        atr = d.atr_h1(tl.closed_count(d.h1.time, H1_SEC, s.time + M15_SEC))
        c = to_candidate(s, symbol, close, spread, atr, d.m15.point, d.m15.digits)
        why = filter_candidate(c, x)
        if why is not None:
            skipped[f"{s.setup} {why}"] += 1
            return None
        cut = friday_close(s.time + M15_SEC, d.crypto)
        o = osim.simulate(c, x, d.m1, d.atr15, close_after=cut)
        if o.open_at_end:
            skipped[f"{s.setup} OPEN_END"] += 1
            return None
        risk = osim.build_stops(c, x).risk
        return LabTrade(
            s.setup,
            symbol,
            s.time,
            s.direction,
            o.r,
            o.reason,
            o.closed_at,
            s.pattern,
            spread / risk,
        )

    return run_sequential(sigs, sim)


def stats(trades: list[LabTrade], months: float, entry_lag: int = M15_SEC) -> dict[str, float]:
    st = tl.summarize([t.r for t in trades], months)
    n = len(trades)
    st["win"] = 100.0 * sum(1 for t in trades if t.r > 0) / n if n else 0.0
    st["spread_r"] = sum(t.spread_r for t in trades) / n if n else 0.0
    hold = sum(max(0, t.closed_at - t.time - entry_lag) for t in trades)
    st["hold_h"] = hold / n / HOUR if n else 0.0
    return st


HEADER = (
    f"{'setup':<6} {'TP':>4} {'periode':<7} {'trade':>6} {'/bln':>5} {'win%':>5} {'R/trade':>8} "
    f"{'total':>7} {'PF':>5} {'DD':>6} {'spread/R':>8} {'lama j':>7}  keputusan"
)


def _row(setup: str, rr: float, period: str, st: dict[str, float], mark: str) -> str:
    return (
        f"{setup:<6} {rr:>4.1f} {period:<7} {int(st['n']):>6} {st['per_month']:>5.1f} "
        f"{st['win']:>5.1f} {st['r']:>+8.3f} {st['total']:>+7.1f} {st['pf']:>5.2f} {st['dd']:>6.1f} "
        f"{st['spread_r']:>8.3f} {st['hold_h']:>7.1f}  {mark}"
    )


def _load(bars: Path, symbols: list[str]) -> dict[str, LabData]:
    out: dict[str, LabData] = {}
    for sym in symbols:
        d = load_lab(bars, sym)
        if d is None:
            print(f"[strategy_lab] {sym}: CSV bar tidak ada, dilewati")
        else:
            out[sym] = d
    return out


def _lab_trades(
    data: dict[str, LabData],
    f: int,
    t: int,
    setups: list[str],
    rrs: list[float],
    skipped: Counter[str],
) -> dict[tuple[str, float], list[LabTrade]]:
    res: dict[tuple[str, float], list[LabTrade]] = {}
    for sym, d in data.items():
        sigs = [s for s in signals(d, f, t) if s.setup in setups]
        for rr in rrs:
            for tr in run_symbol(d, sym, sigs, rr, skipped):
                res.setdefault((tr.setup, rr), []).append(tr)
    return res


def _mark(period: str, st: dict[str, float], by_symbol: dict[str, float]) -> str:
    if period == "IS":
        return "LOLOS IS" if passes_is(st, by_symbol) else "-"
    return "LOLOS konfirmasi" if passes_confirm(st) else "GAGAL konfirmasi"


def _write_csv(path: Path, rows: list[LabTrade]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("setup,symbol,time,direction,r,reason,closed_at,pattern,spread_r\n")
        for tr in rows:
            fh.write(
                f"{tr.setup},{tr.symbol},{tr.time},{tr.direction},{tr.r:.4f},{tr.reason},"
                f"{tr.closed_at},{tr.pattern},{tr.spread_r:.4f}\n"
            )


def cmd_run(args: argparse.Namespace) -> int:
    """Req 6.1-6.3: laporan per setup x TP x periode; IS -> aturan lolos, OOS/REAL -> konfirmasi."""
    periods = tl._periods(args.period, args.periods_ini)
    setups = [x for x in args.setups.split(",") if x]
    rrs = [float(x) for x in args.rr.split(",")]
    data = _load(args.bars, args.symbols.split(","))
    rows: list[LabTrade] = []
    per_symbol_lines: list[str] = []
    print(HEADER)
    for pname, (f, t) in periods.items():
        months = (t - f) / MONTH_SEC
        skipped: Counter[str] = Counter()
        res = _lab_trades(data, f, t, setups, rrs, skipped)
        for setup in setups:
            for rr in rrs:
                trades = sorted(res.get((setup, rr), []), key=lambda x: x.time)
                rows += trades
                st = stats(trades, months)
                by_symbol = {sym: sum(x.r for x in trades if x.symbol == sym) for sym in data}
                reasons = Counter(x.reason for x in trades)
                tail = " ".join(f"{k}:{v}" for k, v in sorted(reasons.items()))
                print(_row(setup, rr, pname, st, _mark(pname, st, by_symbol)) + "  " + tail)
                parts = []
                for sym in data:
                    sel = [x.r for x in trades if x.symbol == sym]
                    avg = sum(sel) / len(sel) if sel else 0.0
                    parts.append(f"{sym} {len(sel)}/{avg:+.2f}")
                per_symbol_lines.append(f"{setup} {rr:.1f} {pname}: " + ", ".join(parts))
        if skipped:
            print(
                f"  {pname} dilewati: " + ", ".join(f"{k} {v}" for k, v in sorted(skipped.items()))
            )
    print("\nper simbol (trade/R per trade):")
    for line in per_symbol_lines:
        print("  " + line)
    if args.out:
        _write_csv(Path(args.out), rows)
    return 0


def _parse_ranges(spec: str) -> list[tuple[int, int]]:
    out = []
    for part in spec.split(","):
        a, b = part.split("-")
        out.append((int(a), int(b)))
    return out


def cmd_combine(args: argparse.Namespace) -> int:
    """Req 6.4-6.5: EA 1.35 + setup terpilih per periode, satu posisi per simbol (EA lebih dulu)."""
    ea_runs = dict(x.split("=", 1) for x in args.ea)
    periods = tl._periods(list(ea_runs), args.periods_ini)
    data = _load(args.bars, args.symbols.split(","))
    print(
        f"{'periode':<7} {'sumber':<9} {'trade':>6} {'/bln':>5} {'R/trade':>8} {'total':>7} "
        f"{'PF':>5} {'DD':>6}  syarat 6.5"
    )
    for pname, (f, t) in periods.items():
        months = (t - f) / MONTH_SEC
        ea = ea_trades(args.db, _parse_ranges(ea_runs[pname]))
        found = _lab_trades(data, f, t, [args.setup], [args.rr], Counter())
        merged = combine(ea, found.get((args.setup, args.rr), []))
        s_ea = tl.summarize([e.r for e in sorted(ea, key=lambda e: e.opened_at)], months)
        s_all = tl.summarize([m.r for m in merged], months)
        added = sum(1 for m in merged if m.source == "LAB")
        verdict = (
            "LOLOS" if s_all["total"] >= s_ea["total"] else "GAGAL"
        ) + f" (+{added} trade lab)"
        for name, st, mark in (("EA 1.35", s_ea, ""), (f"+{args.setup}", s_all, verdict)):
            print(
                f"{pname:<7} {name:<9} {int(st['n']):>6} {st['per_month']:>5.1f} {st['r']:>+8.3f} "
                f"{st['total']:>+7.1f} {st['pf']:>5.2f} {st['dd']:>6.1f}  {mark}"
            )
    return 0


# --- Spec 40: scalping XAUUSD, X2 mean reversion M5 ---

M5_SEC = 300
BB_N = 20
BB_K = 2.0
RSI_N = 14
RSI_HI = 75.0
RSI_LO = 25.0
MR_FROM_H, MR_TO_H = 7, 17  # Req 2.5: London + overlap New York (UTC)
MR_MIN_RR = 1.5
XAU_MIN_PER_MONTH = 20.0  # Req 3.1
XAU_MAX_DD = 25.0

MR_RULES = osim.ExitRules(
    sl_buffer_atr=0.1,
    min_rr=MR_MIN_RR,
    min_sl_atr=0.5,
    max_sl_atr=3.0,
    be_r=NO_BE_R,
    be_buffer_pts=2,
    partial_r=NO_BE_R,
    partial_pct=50.0,
    trail_atr_period=14,
    trail_atr_mult=2.0,
)


def bollinger(close: np.ndarray, n: int = BB_N, k: float = BB_K) -> tuple[np.ndarray, ...]:
    """iBands MT5: SMA n close dan deviasi standar populasi; NaN sebelum n bar."""
    c = np.asarray(close, dtype=float)
    mid = np.full(len(c), np.nan)
    sd = np.full(len(c), np.nan)
    if len(c) >= n:
        win = np.lib.stride_tricks.sliding_window_view(c, n)
        mid[n - 1 :] = win.mean(axis=1)
        sd[n - 1 :] = win.std(axis=1)
    return mid, mid + k * sd, mid - k * sd


def rsi_wilder(close: np.ndarray, n: int = RSI_N) -> np.ndarray:
    """iRSI MT5 (Wilder): benih rata-rata sederhana n perubahan pertama; NaN sebelum indeks n."""
    c = np.asarray(close, dtype=float)
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    d = np.diff(c)
    gain, loss = np.maximum(d, 0.0), np.maximum(-d, 0.0)
    ag, al = gain[:n].mean(), loss[:n].mean()

    def value(g: float, lo: float) -> float:
        if lo == 0.0:
            return 100.0 if g > 0.0 else 50.0
        return 100.0 - 100.0 / (1.0 + g / lo)

    out[n] = value(ag, al)
    for i in range(n, len(d)):
        ag = (ag * (n - 1) + gain[i]) / n
        al = (al * (n - 1) + loss[i]) / n
        out[i + 1] = value(ag, al)
    return out


def mr_decision(
    close: float, up: float, lo: float, mid: float, rsi: float, hour: int
) -> tuple[str, float] | None:
    """Req 2.2, 2.5: arah dan TP garis tengah; None bila tidak ada setup."""
    if not (MR_FROM_H <= hour < MR_TO_H) or np.isnan(mid) or np.isnan(rsi):
        return None
    if close > up and rsi >= RSI_HI:
        return ("SELL", mid)
    if close < lo and rsi <= RSI_LO:
        return ("BUY", mid)
    return None


def filter_mr(c: osim.Candidate, x: osim.ExitRules) -> str | None:
    """Req 2.4: SL_RANGE, RR (R:R ke TP sebelum pembulatan, lihat TS-144b), SPREAD; None bila lolos."""
    st = osim.build_stops(c, x)
    eps = 1e-9 * c.atr_mtf
    lo = max(c.ask - c.bid, x.min_sl_atr * c.atr_mtf)
    if st.risk <= 0 or st.risk < lo - eps or st.risk > x.max_sl_atr * c.atr_mtf + eps:
        return "SL_RANGE"
    if c.opp_prox is None:
        return "RR"
    reward = (c.opp_prox - st.entry) if c.direction == "BUY" else (st.entry - c.opp_prox)
    if reward / st.risk < x.min_rr - 1e-9:
        return "RR"
    if spread_too_wide(c.ask - c.bid, st.risk):
        return "SPREAD"
    return None


XAU = "XAUUSDc"
ATR_N = 14


def atr_series(h: np.ndarray, lo: np.ndarray, c: np.ndarray, n: int = ATR_N) -> np.ndarray:
    """ATR Wilder per bar (benih SMA n TR pertama); 0 sebelum terisi."""
    tr = h - lo
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(lo[1:] - c[:-1])))
    out = np.zeros(len(c))
    if len(c) < n:
        return out
    a = tr[:n].mean()
    out[n - 1] = a
    for i in range(n, len(c)):
        a = (a * (n - 1) + tr[i]) / n
        out[i] = a
    return out


@dataclass
class Xau5:
    m1: osim.Bars
    m5: osim.Bars
    atr15: osim.Atr
    mid: np.ndarray
    up: np.ndarray
    lo: np.ndarray
    rsi: np.ndarray
    atr5: np.ndarray


def _xau5_from_m1(m1: osim.Bars) -> Xau5:
    m5 = tl.aggregate(m1, M5_SEC)
    mid, up, lo = bollinger(m5.close)
    return Xau5(
        m1,
        m5,
        osim.m15_atr(m1, 14),
        mid,
        up,
        lo,
        rsi_wilder(m5.close),
        atr_series(m5.high.copy(), m5.low.copy(), m5.close.copy()),
    )


def load_xau5(bars_dir: Path) -> Xau5 | None:
    csv = bars_dir / f"{XAU}_M1.csv"
    return _xau5_from_m1(osim.load_bars(csv)) if csv.is_file() else None


def truncate_xau5(d: Xau5, t: int) -> Xau5:
    """Data sebelum t (uji tanpa lookahead, TS-154)."""
    n = int(np.searchsorted(d.m1.time, t, side="left"))
    m = d.m1
    sp = m.spread[:n] if m.spread is not None else None
    return _xau5_from_m1(
        osim.Bars(m.time[:n], m.open[:n], m.high[:n], m.low[:n], m.close[:n], m.point, m.digits, sp)
    )


def _m5_range(d: Xau5, t_from: int, t_to: int) -> range:
    j0 = int(np.searchsorted(d.m5.time, t_from, side="left"))
    j1 = int(np.searchsorted(d.m5.time, t_to, side="left"))
    return range(max(j0, BB_N), j1)


def mr_signals(d: Xau5, t_from: int, t_to: int) -> list[Signal]:
    """Sinyal X2 di bar M5 tertutup dalam [t_from, t_to) (Req 2.1-2.3)."""
    out: list[Signal] = []
    for j in _m5_range(d, t_from, t_to):
        t = int(d.m5.time[j])
        res = mr_decision(
            float(d.m5.close[j]),
            float(d.up[j]),
            float(d.lo[j]),
            float(d.mid[j]),
            float(d.rsi[j]),
            (t % DAY) // HOUR,
        )
        if res is None:
            continue
        anchor = float(d.m5.high[j]) if res[0] == "SELL" else float(d.m5.low[j])
        out.append(Signal("X2", t, res[0], anchor, "", res[1]))
    return out


def random_signals(d: Xau5, t_from: int, t_to: int, n: int, seed: int) -> list[Signal]:
    """Pembanding acak (Req 3.3): jam 07-17 UTC, arah acak, SL 1 ATR M5 (jangkar 0,9 ATR + buffer 0,1)."""
    rng = np.random.default_rng(seed)
    idx = [
        j
        for j in _m5_range(d, t_from, t_to)
        if MR_FROM_H <= (int(d.m5.time[j]) % DAY) // HOUR < MR_TO_H and d.atr5[j] > 0
    ]
    if not idx:
        return []
    pick = sorted(rng.choice(idx, size=min(n, len(idx)), replace=False))
    out: list[Signal] = []
    for j in pick:
        buy = bool(rng.integers(0, 2))
        close, atr = float(d.m5.close[j]), float(d.atr5[j])
        anchor = close - 0.9 * atr if buy else close + 0.9 * atr
        out.append(Signal("ACAK", int(d.m5.time[j]), "BUY" if buy else "SELL", anchor))
    return out


def run_xau(
    d: Xau5,
    sigs: list[Signal],
    rules: osim.ExitRules,
    filt: Callable[[osim.Candidate, osim.ExitRules], str | None],
    skipped: Counter[str],
) -> list[LabTrade]:
    """Simulasi berurutan satu posisi sekaligus per setup (Req 2.5, 2.6); entry sesudah bar M5 tutup."""

    def sim(s: Signal) -> LabTrade | None:
        j = int(np.searchsorted(d.m5.time, s.time, side="left"))
        close = float(d.m5.close[j])
        spread = float(d.m5.spread[j]) * d.m5.point if d.m5.spread is not None else 0.0
        c = to_candidate(s, XAU, close, spread, float(d.atr5[j]), d.m5.point, d.m5.digits, tp=s.tp)
        why = filt(c, rules)
        if why is not None:
            skipped[f"{s.setup} {why}"] += 1
            return None
        o = osim.simulate(
            c,
            rules,
            d.m1,
            d.atr15,
            close_after=friday_close(s.time + M5_SEC, False),
            bar_sec=M5_SEC,
        )
        if o.open_at_end:
            skipped[f"{s.setup} OPEN_END"] += 1
            return None
        risk = osim.build_stops(c, rules).risk
        return LabTrade(
            s.setup, XAU, s.time, s.direction, o.r, o.reason, o.closed_at, "", spread / risk
        )

    return run_sequential(sigs, sim)


@dataclass
class EaReport:
    trades: list[LabTrade]
    rejects: dict[str, int]


def ea_report(db: Path, ranges: list[tuple[int, int]], point: float) -> EaReport:
    """Trade EA (X1) dan tahap tolak dari tester DB read-only (Req 1.2, 1.3); spread/R dari spread sinyal."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        trades: list[LabTrade] = []
        rejects: Counter[str] = Counter()
        for a, b in ranges:
            rows = con.execute(
                "SELECT t.opened_at, c.closed_at, c.r_result, c.reason, t.price_open, t.sl_initial,"
                " s.spread_points FROM trades t JOIN closures c ON c.position_id = t.position_id"
                " AND c.session_id = t.session_id LEFT JOIN signals s ON s.id = t.signal_id"
                " WHERE t.session_id BETWEEN ? AND ? AND c.r_result IS NOT NULL ORDER BY t.opened_at",
                (a, b),
            ).fetchall()
            for opened, closed, r, reason, entry, sl0, spread_pts in rows:
                risk = abs(float(entry) - float(sl0))
                share = (float(spread_pts or 0) * point / risk) if risk > 0 else 0.0
                trades.append(
                    LabTrade(
                        "X1", XAU, int(opened), "", float(r), str(reason), int(closed), "", share
                    )
                )
            for stage, n in con.execute(
                "SELECT reject_stage, COUNT(*) FROM signals WHERE session_id BETWEEN ? AND ?"
                " AND reject_stage IS NOT NULL GROUP BY reject_stage",
                (a, b),
            ):
                rejects[str(stage)] += int(n)
        return EaReport(trades, dict(rejects))
    finally:
        con.close()


def passes_xau_is(st: dict[str, float]) -> bool:
    """Req 3.1: >= 20 trade/bulan, R/trade >= +0,10, PF >= 1,20, DD <= 25R."""
    return (
        st["per_month"] >= XAU_MIN_PER_MONTH - 1e-9
        and st["r"] >= IS_MIN_R - 1e-9
        and st["pf"] >= IS_MIN_PF - 1e-9
        and st["dd"] <= XAU_MAX_DD + 1e-9
    )


def _xrow(name: str, tp: str, period: str, st: dict[str, float], mark: str) -> str:
    return (
        f"{name:<6} {tp:>5} {period:<7} {int(st['n']):>6} {st['per_month']:>5.1f} {st['win']:>5.1f} "
        f"{st['r']:>+8.3f} {st['total']:>+7.1f} {st['pf']:>5.2f} {st['dd']:>6.1f} {st['spread_r']:>8.3f} "
        f"{st['hold_h']:>7.1f}  {mark}"
    )


def cmd_xau(args: argparse.Namespace) -> int:
    """Spec 40: X1 (EA, dari --ea), X2 mean reversion M5, pembanding ACAK; aturan Req 3.1-3.3."""
    d = load_xau5(args.bars)
    if d is None:
        print(f"[strategy_lab] {XAU}: CSV bar tidak ada")
        return 2
    ea_runs = dict(x.split("=", 1) for x in args.ea)
    if ea_runs and args.db is None:
        print("[strategy_lab] --ea butuh --db")
        return 2
    periods = tl._periods(args.period, args.periods_ini)
    print(HEADER)
    for pname, (f, t) in periods.items():
        months = (t - f) / MONTH_SEC
        skipped: Counter[str] = Counter()
        rows: list[tuple[str, str, list[LabTrade], int]] = []
        if pname in ea_runs:
            rep = ea_report(args.db, _parse_ranges(ea_runs[pname]), d.m5.point)
            rows.append(("X1", "zona", rep.trades, 0))
            top = sorted(rep.rejects.items(), key=lambda kv: -kv[1])[:5]
            print(f"  {pname} X1 tolak: " + ", ".join(f"{k} {v}" for k, v in top))
        x2 = run_xau(d, mr_signals(d, f, t), MR_RULES, filter_mr, skipped)
        rows.append(("X2", "mid", x2, M5_SEC))
        rnd = run_xau(
            d,
            random_signals(d, f, t, args.random_n, args.seed),
            LAB_RULES[1.5],
            filter_candidate,
            skipped,
        )
        rows.append(("ACAK", "1.5R", rnd, M5_SEC))
        for name, tp, trades, lag in rows:
            st = stats(trades, months, entry_lag=lag)
            if name == "ACAK":
                mark = "pembanding"
            elif pname == "IS":
                mark = "LOLOS IS" if passes_xau_is(st) else "-"
            else:
                mark = "LOLOS konfirmasi" if passes_confirm(st) else "GAGAL konfirmasi"
            reasons = Counter(x.reason for x in trades)
            tail = " ".join(f"{k}:{v}" for k, v in sorted(reasons.items()))
            print(_xrow(name, tp, pname, st, mark) + "  " + tail)
        if skipped:
            print(
                f"  {pname} dilewati: " + ", ".join(f"{k} {v}" for k, v in sorted(skipped.items()))
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "combine", "xau"):
        p = sub.add_parser(name)
        p.add_argument("--bars", type=Path, default=DEFAULT_BARS_DIR)
        p.add_argument("--symbols", default=DEFAULT_SYMBOLS)
        p.add_argument("--periods-ini", type=Path, default=DEFAULT_PERIODS_INI)
        if name == "run":
            p.add_argument(
                "--period", action="append", required=True, choices=("IS", "OOS", "REAL")
            )
            p.add_argument("--setups", default=",".join(SETUPS))
            p.add_argument("--rr", default=",".join(str(x) for x in TP_VARIANTS))
            p.add_argument("--out", help="CSV trade")
        elif name == "xau":
            p.add_argument(
                "--period", action="append", required=True, choices=("IS", "OOS", "REAL")
            )
            p.add_argument("--db", type=Path, help="tester DB untuk baris X1")
            p.add_argument(
                "--ea", action="append", default=[], help="PERIODE=A-B sesi X1 (gaya SCALPING)"
            )
            p.add_argument("--random-n", type=int, default=3000)
            p.add_argument("--seed", type=int, default=7)
        else:
            p.add_argument("--db", required=True, type=Path)
            p.add_argument("--setup", required=True, choices=SETUPS)
            p.add_argument("--rr", required=True, type=float, choices=TP_VARIANTS)
            p.add_argument("--ea", action="append", required=True, help="PERIODE=A-B sesi EA 1.35")
    args = ap.parse_args(argv)
    if args.cmd == "xau":
        return cmd_xau(args)
    return cmd_run(args) if args.cmd == "run" else cmd_combine(args)


if __name__ == "__main__":
    raise SystemExit(main())
