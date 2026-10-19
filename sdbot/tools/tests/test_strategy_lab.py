"""Lab strategi kedua (spec 38): TS-137..149."""

import datetime as dt

import numpy as np
import outcome_sim as osim
import pytest
import strategy_lab as sl

UTC = dt.UTC
FRI = int(dt.datetime(2026, 10, 16, 0, 0, tzinfo=UTC).timestamp())  # Jumat
ATR = 0.0010


def _bars(rows: list[tuple[float, float, float, float]], start: int, step: int = 60) -> osim.Bars:
    arr = np.array(rows, dtype=float).reshape(len(rows), 4)
    n = len(rows)
    return osim.Bars(
        time=np.arange(start, start + step * n, step, dtype=np.int64),
        open=arr[:, 0],
        high=arr[:, 1],
        low=arr[:, 2],
        close=arr[:, 3],
        point=0.00001,
        digits=5,
        spread=np.full(n, 10.0),
    )


def _cand(t: int, direction: str = "BUY") -> osim.Candidate:
    return osim.Candidate(
        signal_id=1,
        session_id=0,
        symbol="EURUSDc",
        time=t,
        direction=direction,
        stage=None,
        zone_prox=1.1000,
        zone_dist=1.0990 if direction == "BUY" else 1.1010,
        opp_prox=None,
        bid=1.1000,
        ask=1.1000,
        atr_mtf=ATR,
        point=0.00001,
        digits=5,
    )


def test_ts145_simulate_close_after() -> None:
    """TS-145: posisi masih terbuka saat close_after -> FRIDAY di open bar itu; tanpa parameter -> END."""
    t_sig = FRI + 21 * 3600  # bar M15 21:00, entry sesudah 21:15
    start = t_sig + 900
    rows = [(1.1002, 1.1003, 1.1001, 1.1002)] * 60  # 21:15..22:14, tidak menyentuh SL/TP
    bars = _bars(rows, start)
    atr = osim.Atr(np.array([], dtype=np.int64), np.array([]))
    c = _cand(t_sig)
    x = sl.LAB_RULES[2.0]
    cut = FRI + 21 * 3600 + 45 * 60
    out = osim.simulate(c, x, bars, atr, close_after=cut)
    risk = 1.1000 - (1.0990 - 0.1 * ATR)
    assert out.reason == "FRIDAY"
    assert out.closed_at == cut
    assert out.r == pytest.approx((1.1002 - 1.1000) / risk)
    plain = osim.simulate(c, x, bars, atr)
    assert plain.reason == "END" and plain.open_at_end


def test_ts146_friday_close() -> None:
    """TS-146: Jumat 21:45 UTC pertama sesudah t; BTC tanpa penutupan."""
    wed = FRI - 2 * 86400 + 10 * 3600
    assert sl.friday_close(wed, crypto=False) == FRI + 21 * 3600 + 45 * 60
    fri_late = FRI + 22 * 3600
    assert sl.friday_close(fri_late, crypto=False) == FRI + 7 * 86400 + 21 * 3600 + 45 * 60
    assert sl.friday_close(wed, crypto=True) is None


# --- Range sesi dan breakout (task 2) ---

DAY0 = int(dt.datetime(2026, 10, 14, 0, 0, tzinfo=UTC).timestamp())  # Rabu
BARS_DIR = sl.DEFAULT_BARS_DIR


def _flat_m1(
    start: int, minutes: int, lo: float, hi: float
) -> list[tuple[float, float, float, float]]:
    mid = (lo + hi) / 2
    return [(mid, mid, mid, mid)] * minutes


def _day_bars(
    edits: dict[int, tuple[float, float, float, float]], minutes: int = 24 * 60
) -> osim.Bars:
    """Bar M1 sehari datar di 1.1000; edits = {menit sejak 00:00: (o, h, l, c)}."""
    rows = [(1.1000, 1.1000, 1.1000, 1.1000)] * minutes
    for m, r in edits.items():
        rows[m] = r
    return _bars(rows, DAY0)


@pytest.mark.skipif(
    not (sl.DEFAULT_BARS_DIR / "EURUSDc_M1.csv").is_file(), reason="bar ekspor tidak ada"
)
def test_ts137_server_time_is_utc() -> None:
    """TS-137: server Broker B = UTC. Bar terakhir sebelum akhir pekan jatuh Jumat 20:5x/21:5x (tutup New York
    dalam UTC; server UTC+3 akan 23:5x), dan >= 90% pembukaan mingguan Minggu 21:00/22:00. Celah libur
    (Natal, Tahun Baru) dan histori Minggu yang kosong di awal data (Senin 00:00, April 2024) diabaikan.
    """
    m1 = osim.load_bars(sl.DEFAULT_BARS_DIR / "EURUSDc_M1.csv")
    gaps = np.flatnonzero(np.diff(m1.time) > 24 * 3600)
    closes = [dt.datetime.fromtimestamp(int(m1.time[g]), UTC) for g in gaps]
    fridays = [d for d in closes if d.weekday() == 4]
    assert len(fridays) > 20
    assert all(d.hour in (20, 21) and d.minute >= 50 for d in fridays), [
        d for d in fridays if d.hour not in (20, 21)
    ]
    opens = [dt.datetime.fromtimestamp(int(m1.time[g + 1]), UTC) for g in gaps]
    sunday = sum(1 for d in opens if d.weekday() == 6 and d.hour in (21, 22))
    assert sunday >= 0.9 * len(fridays)


def test_ts138_session_range() -> None:
    """TS-138: high/low dalam jendela; celah > 30 menit -> None; tanpa bar -> None."""
    b = _day_bars(
        {
            60: (1.1000, 1.1012, 1.0997, 1.1000),
            400: (1.1, 1.1, 1.0990, 1.1),
            420: (1.1, 1.1050, 1.1, 1.1),
        }
    )
    r = sl.session_range(b, DAY0, 0, 7 * 3600)
    assert r is not None and r.high == pytest.approx(1.1012) and r.low == pytest.approx(1.0990)
    keep = (b.time < DAY0 + 3600) | (b.time >= DAY0 + 3600 + 31 * 60)
    gap = osim.Bars(
        b.time[keep], b.open[keep], b.high[keep], b.low[keep], b.close[keep], b.point, b.digits
    )
    assert sl.session_range(gap, DAY0, 0, 7 * 3600) is None
    assert sl.session_range(b, DAY0 + 3 * 86400, 0, 7 * 3600) is None


def _m15_from(b: osim.Bars) -> osim.Bars:
    import trendline_lab as tl

    return tl.aggregate(b, 900)


def test_ts139_s1_breakout() -> None:
    """TS-139: S1 tembus atas > 0,1 ATR -> BUY; 0,05 ATR -> tidak; hanya tembusan pertama; 11:00 -> tidak; lebar."""
    rng = {120: (1.1, 1.1010, 1.0995, 1.1)}  # range Asia 1.0995-1.1010 (lebar 1,5 ATR)
    up = {
        **rng,
        7 * 60 + 14: (1.1, 1.1030, 1.1, 1.10115 + 0.00005),
    }  # close bar 07:00 = high + 0,15 ATR
    s = sl.range_signal(*_pair(up), DAY0, sl.S1, ATR)
    assert s is not None and s.direction == "BUY" and s.time == DAY0 + 7 * 3600
    assert s.anchor == pytest.approx(1.0995)  # SL di sisi lain range
    weak = {**rng, 7 * 60 + 14: (1.1, 1.1020, 1.1, 1.10105)}  # + 0,05 ATR
    assert sl.range_signal(*_pair(weak), DAY0, sl.S1, ATR) is None
    both = {**up, 8 * 60 + 14: (1.1, 1.1, 1.0970, 1.0975)}
    first = sl.range_signal(*_pair(both), DAY0, sl.S1, ATR)
    assert first is not None and first.direction == "BUY"
    late = {**rng, 11 * 60 + 14: (1.1, 1.1030, 1.1, 1.1013)}
    assert sl.range_signal(*_pair(late), DAY0, sl.S1, ATR) is None
    narrow = {120: (1.1, 1.1003, 1.0999, 1.1), 7 * 60 + 14: (1.1, 1.1030, 1.1, 1.1013)}  # 0,4 ATR
    assert sl.range_signal(*_pair(narrow), DAY0, sl.S1, ATR) is None
    wide = {120: (1.1, 1.1016, 1.0990, 1.1), 7 * 60 + 14: (1.1, 1.1040, 1.1, 1.1030)}  # 2,6 ATR
    assert sl.range_signal(*_pair(wide), DAY0, sl.S1, ATR) is None


def _pair(edits: dict[int, tuple[float, float, float, float]]) -> tuple[osim.Bars, osim.Bars]:
    b = _day_bars(edits)
    return b, _m15_from(b)


def test_ts140_s2_opening_range() -> None:
    """TS-140: S2 range 13:30-14:00; tembus 13:45 (sebelum jendela) -> tidak; 14:15 -> ya; lebar 0,25 ATR -> None."""
    rng = {13 * 60 + 35: (1.1, 1.1006, 1.0998, 1.1)}  # lebar 0,8 ATR
    early = {**rng, 13 * 60 + 59: (1.1, 1.1020, 1.1, 1.1010)}
    assert sl.range_signal(*_pair(early), DAY0, sl.S2, ATR) is None
    later = {
        **rng,
        14 * 60 + 29: (1.1, 1.1, 1.0980, 1.0986),
    }  # bar 14:15 tutup di bawah low - 0,1 ATR
    s = sl.range_signal(*_pair(later), DAY0, sl.S2, ATR)
    assert s is not None and s.direction == "SELL" and s.time == DAY0 + 14 * 3600 + 15 * 60
    assert s.anchor == pytest.approx(1.1006)
    tiny = {13 * 60 + 35: (1.1, 1.10015, 1.09995, 1.1), 14 * 60 + 29: (1.1, 1.1, 1.0980, 1.0986)}
    assert sl.range_signal(*_pair(tiny), DAY0, sl.S2, ATR) is None


# --- S3 pullback EMA dan tanpa lookahead (task 3) ---


def _pin_bull(low: float) -> "object":
    import trendline_lab as tl

    off = low - 1.0995
    return tl.Ohlc(
        [1.1005 + off, 1.1005 + off, 1.1008 + off],
        [1.1008 + off, 1.1008 + off, 1.1010 + off],
        [1.1004 + off, 1.1004 + off, 1.0995 + off],
        [1.1006 + off, 1.1006 + off, 1.1009 + off],
    )


def test_ts141_s3_decision() -> None:
    """TS-141: bias BULL + low dalam 0,2 ATR H1 dari EMA + pin bullish -> BUY (jangkar = low); 0,25 ATR -> tidak;
    pola netral / bias 0 / jam 23 -> tidak."""
    import trendline_lab as tl

    atr_h1 = 0.0020
    ema = 1.0995 + 0.15 * atr_h1  # low 1.0995 berada 0,15 ATR di bawah EMA
    s = sl.s3_decision(_pin_bull(1.0995), ATR, ema, atr_h1, 1, 14)
    assert s is not None and s[0] == "BUY" and s[1] == pytest.approx(1.0995) and s[2] == "PIN"
    far = 1.0995 + 0.25 * atr_h1
    assert sl.s3_decision(_pin_bull(1.0995), ATR, far, atr_h1, 1, 14) is None
    flat = tl.Ohlc(
        [1.1, 1.1, 1.1], [1.1001, 1.1001, 1.1001], [1.0999, 1.0999, 1.0995], [1.1, 1.1, 1.1]
    )
    assert sl.s3_decision(flat, ATR, ema, atr_h1, 1, 14) is None
    assert sl.s3_decision(_pin_bull(1.0995), ATR, ema, atr_h1, 0, 14) is None
    assert sl.s3_decision(_pin_bull(1.0995), ATR, ema, atr_h1, 1, 23) is None
    assert sl.s3_decision(_pin_bull(1.0995), ATR, ema, atr_h1, -1, 14) is None


@pytest.mark.skipif(
    not (sl.DEFAULT_BARS_DIR / "EURUSDc_M1.csv").is_file(), reason="bar ekspor tidak ada"
)
def test_ts142_no_lookahead() -> None:
    """TS-142: sinyal S1/S2/S3 identik sebelum dan sesudah data sesudah penutupan bar sinyal dibuang."""
    full = sl.load_lab(sl.DEFAULT_BARS_DIR, "EURUSDc")
    assert full is not None
    t_from = int(dt.datetime(2026, 3, 2, tzinfo=UTC).timestamp())
    t_to = int(dt.datetime(2026, 3, 21, tzinfo=UTC).timestamp())
    sigs = sl.signals(full, t_from, t_to)
    assert {s.setup for s in sigs} >= {"S1", "S2", "S3"}
    for s in sigs[:30]:
        cut = sl.truncate(full, s.time + sl.M15_SEC)
        again = [
            x
            for x in sl.signals(cut, t_from, s.time + sl.M15_SEC)
            if x.setup == s.setup and x.time == s.time
        ]
        assert again == [s], s


# --- Kandidat, filter, berurutan, gabungan, aturan lolos (task 4) ---


def _sig_cand(direction: str, anchor: float, close: float, spread_pts: float) -> osim.Candidate:
    return sl.to_candidate(
        sl.Signal("S1", DAY0 + 7 * 3600, direction, anchor),
        "EURUSDc",
        close,
        spread_pts * 0.00001,
        ATR,
        0.00001,
        5,
    )


def test_ts143_candidate_stops() -> None:
    """TS-143: SELL S1, jangkar 1.10500, ATR 0.0010, spread 2 point -> SL 1.10512; TP = entry - 2R."""
    c = _sig_cand("SELL", 1.10500, 1.10300, 2)
    s = osim.build_stops(c, sl.LAB_RULES[2.0])
    assert s.sl == pytest.approx(1.10512)
    assert s.entry == pytest.approx(1.10300)
    assert s.tp == pytest.approx(round(1.10300 - 2 * (1.10512 - 1.10300), 5))
    assert c.opp_prox is None and c.zone_dist == pytest.approx(1.10500)


def test_ts144_filter_candidate() -> None:
    """TS-144: SL < 0,3 ATR -> SL_RANGE; spread 16% R -> SPREAD; tepat 15% -> lolos."""
    x = sl.LAB_RULES[2.0]
    near = _sig_cand("BUY", 1.10290, 1.10300, 0)  # R = 0,0001 + 0,0001 = 0,2 ATR
    assert sl.filter_candidate(near, x) == "SL_RANGE"

    # BUY: entry = ask = close + spread; R = ask - (anchor - 0,0001)
    def buy_with(spread_pts: float) -> osim.Candidate:
        return _sig_cand("BUY", 1.10300 - 0.0009, 1.10300, spread_pts)

    r = lambda c: (c.ask - (c.zone_dist - 0.1 * ATR))  # noqa: E731
    wide = buy_with(18)
    assert (wide.ask - wide.bid) / r(wide) > 0.15
    assert sl.filter_candidate(wide, x) == "SPREAD"
    ok = buy_with(15)  # 0,00015 / 0,00115 = 13%
    assert sl.filter_candidate(ok, x) is None
    exact = sl.spread_share(0.00015, 0.0010)
    assert exact == pytest.approx(0.15) and not sl.spread_too_wide(0.00015, 0.0010)


def _lt(setup: str, sym: str, t: int, closed: int, r: float) -> sl.LabTrade:
    return sl.LabTrade(setup, sym, t, "BUY", r, "TP", closed, "")


def test_ts147_sequential_and_combine() -> None:
    """TS-147: sinyal kedua saat posisi setup sama terbuka dilewati; trade lab tumpang tindih EA dilewati, EA tetap."""
    calls: list[int] = []

    def sim(s: sl.Signal) -> sl.LabTrade | None:
        calls.append(s.time)
        return _lt(s.setup, "EURUSDc", s.time, s.time + 3600, 1.0)

    sigs = [
        sl.Signal("S1", 1000, "BUY", 1.0),
        sl.Signal("S1", 2000, "BUY", 1.0),
        sl.Signal("S2", 2000, "BUY", 1.0),
        sl.Signal("S1", 5000, "BUY", 1.0),
    ]
    out = sl.run_sequential(sigs, sim)
    assert [(t.setup, t.time) for t in out] == [("S1", 1000), ("S2", 2000), ("S1", 5000)]
    ea = [sl.EaTrade("EURUSDc", 900, 1500, -1.0), sl.EaTrade("GBPUSDc", 0, 10_000, 2.0)]
    lab = [
        _lt("S1", "EURUSDc", 1000, 4600, 1.0),
        _lt("S1", "EURUSDc", 5000, 8600, 1.5),
        _lt("S1", "EURUSDc", 100, 950, 0.5),
    ]
    merged = sl.combine(ea, lab)
    assert sorted((m.source, m.symbol, m.time) for m in merged) == [
        ("EA", "EURUSDc", 900),
        ("EA", "GBPUSDc", 0),
        ("LAB", "EURUSDc", 5000),
    ]


def test_ts148_pass_rules() -> None:
    """TS-148: batas tepat lolos; 119 trade / +0,099 / PF 1,19 / 6 simbol gagal; konfirmasi R >= +0,05 dan total > 0."""
    base = {"n": 120, "r": 0.10, "pf": 1.20, "total": 12.0}
    seven = {f"S{i}": (1.0 if i < 7 else -1.0) for i in range(12)}
    six = {f"S{i}": (1.0 if i < 6 else -1.0) for i in range(12)}
    assert sl.passes_is(base, seven)
    assert not sl.passes_is({**base, "n": 119}, seven)
    assert not sl.passes_is({**base, "r": 0.099}, seven)
    assert not sl.passes_is({**base, "pf": 1.19}, seven)
    assert not sl.passes_is(base, six)
    assert sl.passes_confirm({"n": 10, "r": 0.05, "pf": 1.1, "total": 0.5})
    assert not sl.passes_confirm({"n": 10, "r": 0.049, "pf": 1.1, "total": 0.5})
    assert not sl.passes_confirm({"n": 10, "r": 0.1, "pf": 1.1, "total": 0.0})


# --- CLI dan laporan (task 5) ---


def _write_symbol(path, symbol: str, start: int, days: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    n = days * 1440
    steps = rng.normal(0, 0.00012, n)
    close = 1.1 + np.cumsum(steps)
    open_ = np.r_[1.1, close[:-1]]
    hi = np.maximum(open_, close) + np.abs(rng.normal(0, 0.00005, n))
    lo = np.minimum(open_, close) - np.abs(rng.normal(0, 0.00005, n))
    t = start + 60 * np.arange(n)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# symbol={symbol} point=0.0000100000 digits=5\ntime,open,high,low,close,spread\n")
        for i in range(n):
            f.write(f"{t[i]},{open_[i]:.5f},{hi[i]:.5f},{lo[i]:.5f},{close[i]:.5f},10\n")


def test_ts149_cli_run(tmp_path, capsys) -> None:
    """TS-149: `run` pada dua simbol sintetis -> tabel memuat kolom Req 6.1 dan baris per simbol."""
    start = int(dt.datetime(2026, 1, 5, tzinfo=UTC).timestamp())
    for i, sym in enumerate(("AAAUSDc", "BBBUSDc")):
        _write_symbol(tmp_path / f"{sym}_M1.csv", sym, start, 45, seed=i)
    ini = tmp_path / "periods.ini"
    ini.write_text("[IS]\nFromDate=2026.01.26\nToDate=2026.02.18\nModel=1\n", encoding="utf-8")
    rc = sl.main(
        [
            "run",
            "--bars",
            str(tmp_path),
            "--period",
            "IS",
            "--periods-ini",
            str(ini),
            "--symbols",
            "AAAUSDc,BBBUSDc",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    for col in (
        "setup",
        "TP",
        "periode",
        "trade",
        "/bln",
        "win%",
        "R/trade",
        "total",
        "PF",
        "DD",
        "spread/R",
        "lama j",
    ):
        assert col in out, col
    assert "AAAUSDc" in out and "BBBUSDc" in out
    assert "S1" in out and "S2" in out and "S3" in out


def test_ts144b_tp_rounding_not_rejected() -> None:
    """TS-144b (bug run IS 2026-10-15): TP 1,5R dibulatkan ke digit membuat R:R 1,4999 -> kandidat BUY sah
    tidak boleh ditolak SL_RANGE; penolakan hanya karena jarak SL di luar 0,3-3 ATR."""
    x = sl.LAB_RULES[1.5]
    rejected = 0
    for pts in range(60, 300):
        c = sl.to_candidate(
            sl.Signal("S1", 0, "BUY", round(1.10377 - pts * 1e-5, 5)),
            "X",
            1.10377,
            0.0001,
            ATR,
            0.00001,
            5,
        )
        risk = c.ask - (c.zone_dist - 0.1 * ATR)
        legit = risk < 0.3 * ATR or risk > 3.0 * ATR
        if sl.filter_candidate(c, x) == "SL_RANGE" and not legit:
            rejected += 1
    assert rejected == 0


# --- Spec 40: scalping XAUUSD ---


def test_ts150_simulate_bar_sec() -> None:
    """TS-150: bar_sec=300 -> entry sesudah bar M5 tutup (t + 300); default tetap t + 900."""
    t = FRI
    rows = [(1.1000, 1.1000, 1.1000, 1.1000)] * 20
    rows[5] = (1.1000, 1.1030, 1.1000, 1.1000)  # menit ke-5: TP 2R tersentuh
    rows[15] = (1.1000, 1.1000, 1.0980, 1.0985)  # menit ke-15: SL tersentuh
    bars = _bars(rows, t)
    atr = osim.Atr(np.array([], dtype=np.int64), np.array([]))
    c = _cand(t)
    x = sl.LAB_RULES[2.0]
    assert osim.simulate(c, x, bars, atr, bar_sec=300).reason == "TP"
    assert osim.simulate(c, x, bars, atr).reason == "SL"


def test_ts151_indicators() -> None:
    """TS-151: BB(20,2) pada 1..20 -> mid 10,5, sd populasi 5,766; RSI naik terus 100, selang-seling 50 di benih."""
    close = np.arange(1.0, 21.0)
    mid, up, lo = sl.bollinger(close, 20, 2.0)
    assert np.isnan(mid[18]) and mid[19] == pytest.approx(10.5)
    sd = np.sqrt(399.0 / 12.0)
    assert up[19] == pytest.approx(10.5 + 2 * sd) and lo[19] == pytest.approx(10.5 - 2 * sd)
    up_only = sl.rsi_wilder(np.arange(1.0, 40.0), 14)
    assert (
        np.isnan(up_only[13])
        and up_only[14] == pytest.approx(100.0)
        and up_only[-1] == pytest.approx(100.0)
    )
    alt = np.array([10.0 + (i % 2) for i in range(30)])
    assert sl.rsi_wilder(alt, 14)[14] == pytest.approx(50.0)


def test_ts152_mr_decision() -> None:
    """TS-152: close > band atas + RSI 76 jam 10 -> SELL tp = mid; RSI 74 -> None; close < band bawah + RSI 24 -> BUY;
    jam 18 -> None."""
    assert sl.mr_decision(105.0, 104.0, 96.0, 100.0, 76.0, 10) == ("SELL", 100.0)
    assert sl.mr_decision(105.0, 104.0, 96.0, 100.0, 74.0, 10) is None
    assert sl.mr_decision(95.0, 104.0, 96.0, 100.0, 24.0, 10) == ("BUY", 100.0)
    assert sl.mr_decision(105.0, 104.0, 96.0, 100.0, 80.0, 18) is None
    assert sl.mr_decision(105.0, 104.0, 96.0, 100.0, 80.0, 6) is None


def _mr_cand(high: float, tp: float, spread: float) -> osim.Candidate:
    sig = sl.Signal("X2", DAY0 + 10 * 3600, "SELL", high, "", tp)
    return sl.to_candidate(sig, "XAUUSDc", 1.1000, spread, ATR, 0.00001, 5, tp=tp)


def test_ts153_filter_mr() -> None:
    """TS-153: TP 1,4R -> RR; SL 0,4 ATR -> SL_RANGE; spread 16,7% R -> SPREAD; R:R 1,5 tepat -> lolos."""
    x = sl.MR_RULES
    risk = 0.0007  # high 1.1006 + 0,1 ATR = SL 1.1007, entry 1.1000
    assert sl.filter_mr(_mr_cand(1.1006, 1.1000 - 1.4 * risk, 0.0), x) == "RR"
    assert sl.filter_mr(_mr_cand(1.1003, 1.0980, 0.0), x) == "SL_RANGE"
    assert sl.filter_mr(_mr_cand(1.1006, 1.0980, 0.00014), x) == "SPREAD"
    assert sl.filter_mr(_mr_cand(1.1006, 1.1000 - 1.5 * risk, 0.0), x) is None


XAU_CSV = sl.DEFAULT_BARS_DIR / "XAUUSDc_M1.csv"


@pytest.mark.skipif(not XAU_CSV.is_file(), reason="bar ekspor XAU tidak ada")
def test_ts154_mr_no_lookahead() -> None:
    """TS-154: sinyal X2 XAUUSDc Mar 2026 identik sebelum dan sesudah data sesudah bar sinyal dibuang."""
    full = sl.load_xau5(sl.DEFAULT_BARS_DIR)
    assert full is not None
    t_from = int(dt.datetime(2026, 3, 2, tzinfo=UTC).timestamp())
    t_to = int(dt.datetime(2026, 3, 14, tzinfo=UTC).timestamp())
    sigs = sl.mr_signals(full, t_from, t_to)
    assert len(sigs) >= 5
    for s in sigs[:15]:
        cut = sl.truncate_xau5(full, s.time + sl.M5_SEC)
        again = [x for x in sl.mr_signals(cut, t_from, s.time + sl.M5_SEC) if x.time == s.time]
        assert again == [s], s


@pytest.mark.skipif(not XAU_CSV.is_file(), reason="bar ekspor XAU tidak ada")
def test_ts155_random_signals() -> None:
    """TS-155: seed sama -> hasil sama; jam 07-17 UTC; jangkar 0,9 ATR M5 dari close bar sinyal."""
    d = sl.load_xau5(sl.DEFAULT_BARS_DIR)
    assert d is not None
    t_from = int(dt.datetime(2026, 3, 2, tzinfo=UTC).timestamp())
    t_to = int(dt.datetime(2026, 3, 14, tzinfo=UTC).timestamp())
    a = sl.random_signals(d, t_from, t_to, 50, seed=3)
    b = sl.random_signals(d, t_from, t_to, 50, seed=3)
    assert a == b and len(a) == 50
    assert {x.direction for x in a} == {"BUY", "SELL"}
    for x in a:
        assert 7 <= (x.time % 86400) // 3600 < 17
        j = int(np.searchsorted(d.m5.time, x.time))
        dist = abs(float(d.m5.close[j]) - x.anchor)
        assert dist == pytest.approx(0.9 * float(d.atr5[j]))


def test_ts156_ea_report(tmp_path) -> None:
    """TS-156: ea_report pada DB sintetis: 2 trade (+2R, -1R), spread/R 0,02, satu tolak SPREAD_TOO_WIDE."""
    import sqlite3

    db = tmp_path / "t.sqlite"
    con = sqlite3.connect(db)
    con.executescript(
        "CREATE TABLE trades (session_id INT, position_id INT, opened_at INT, price_open REAL, sl_initial REAL,"
        " signal_id INT);"
        "CREATE TABLE closures (session_id INT, position_id INT, closed_at INT, r_result REAL, reason TEXT,"
        " holding_sec INT);"
        "CREATE TABLE signals (id INT, session_id INT, spread_points INT, status TEXT, reject_stage TEXT);"
        "INSERT INTO trades VALUES (5, 1, 1000, 4000.0, 3990.0, 11), (5, 2, 9000, 4000.0, 4015.0, 12);"
        "INSERT INTO closures VALUES (5, 1, 4600, 2.0, 'TP', 3600), (5, 2, 16200, -1.0, 'SL', 7200);"
        "INSERT INTO signals VALUES (11, 5, 200, 'ACCEPTED', NULL), (12, 5, 300, 'ACCEPTED', NULL),"
        " (13, 5, 900, 'REJECTED', 'SPREAD_TOO_WIDE');"
    )
    con.commit()
    con.close()
    rep = sl.ea_report(db, [(5, 5)], point=0.001)
    assert [t.r for t in rep.trades] == [2.0, -1.0]
    assert rep.trades[0].spread_r == pytest.approx(0.02) and rep.trades[
        1
    ].spread_r == pytest.approx(0.02)
    assert rep.trades[1].closed_at - rep.trades[1].time == 7200
    assert rep.rejects == {"SPREAD_TOO_WIDE": 1}
