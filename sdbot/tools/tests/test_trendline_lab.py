"""Lab setup trendline H1 + PA M15 (spec 32): TS-116..124."""

import numpy as np
import outcome_sim as osim
import pytest
import trendline_lab as tl

T0 = 1_780_000_200 - (1_780_000_200 % 3600)  # awal jam
ATR = 0.0010


def _bars(
    rows: list[tuple[float, float, float, float]], start: int = T0, step: int = 60
) -> osim.Bars:
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


def test_ts116_aggregate() -> None:
    """TS-116: 30 bar M1 -> 2 bar M15: open bar pertama, high maks, low min, close bar terakhir, waktu awal."""
    rows = [
        (
            1.0 + i * 0.001,
            1.0 + i * 0.001 + 0.0005,
            1.0 + i * 0.001 - 0.0005,
            1.0 + i * 0.001 + 0.0002,
        )
        for i in range(30)
    ]
    m15 = tl.aggregate(_bars(rows), 900)
    assert list(m15.time) == [T0, T0 + 900]
    assert m15.open[0] == pytest.approx(1.0)
    assert m15.high[0] == pytest.approx(1.0 + 14 * 0.001 + 0.0005)
    assert m15.low[1] == pytest.approx(1.0 + 15 * 0.001 - 0.0005)
    assert m15.close[1] == pytest.approx(1.0 + 29 * 0.001 + 0.0002)


def test_ts117_find_swings() -> None:
    """TS-117: fractal berjeda kekuatan 2; high sama persis: hanya bar lebih awal; kanan belum lengkap = bukan swing."""
    highs = np.array([1.0, 1.1, 1.3, 1.1, 1.0, 1.2, 1.3, 1.3, 1.2, 1.1, 1.4])
    lows = highs - 0.5
    lows[4] = 0.3  # swing low di 4
    sw = tl.find_swings(highs, lows, 2)
    hs = [(s.index, s.price) for s in sw if s.is_high]
    ls = [(s.index, s.price) for s in sw if not s.is_high]
    assert hs == [(2, 1.3), (6, 1.3)]  # 7 sama dengan 6 -> hanya 6; 10 kanan belum lengkap
    assert (4, 0.3) in ls


def test_ts118_patterns() -> None:
    """TS-118: angka fixture TestPatterns (TC-PA-01, TC-PA-02) dan pin/engulfing/netral."""
    star = tl.Ohlc(
        [1.1020, 1.1007, 1.1009],
        [1.1022, 1.1010, 1.1019],
        [1.1006, 1.1004, 1.1008],
        [1.1008, 1.1008, 1.1018],
    )
    assert tl.detect_pattern(star, ATR, 1) == "STAR"
    not_star = tl.Ohlc(
        [1.1013, 1.1007, 1.1009],
        [1.1015, 1.1010, 1.1019],
        [1.1006, 1.1004, 1.1008],
        [1.1008, 1.1008, 1.1018],
    )
    assert tl.detect_pattern(not_star, ATR, 1) != "STAR"
    # pin bullish: badan kecil di atas, sumbu bawah panjang
    pin = tl.Ohlc(
        [1.1005, 1.1005, 1.1008],
        [1.1008, 1.1008, 1.1010],
        [1.1004, 1.1004, 1.0995],
        [1.1006, 1.1006, 1.1009],
    )
    assert tl.detect_pattern(pin, ATR, 1) == "PIN"
    assert tl.detect_pattern(pin, ATR, -1) == "NONE"
    # engulfing kuat bearish: bar bull lalu bar bear besar menelan dan menutup di bawah low sebelumnya
    eng = tl.Ohlc(
        [1.1005, 1.1000, 1.1012],
        [1.1008, 1.1012, 1.1013],
        [1.1004, 1.0999, 1.0996],
        [1.1006, 1.1011, 1.0997],
    )
    assert tl.detect_pattern(eng, ATR, -1) == "ENGULF_STRONG"
    flat = tl.Ohlc(
        [1.1, 1.1, 1.1], [1.1001, 1.1001, 1.1001], [1.0999, 1.0999, 1.0999], [1.1, 1.1, 1.1]
    )
    assert tl.detect_pattern(flat, ATR, 1) == "NONE"


def _h1_uptrend(n: int = 60) -> osim.Bars:
    """H1 naik bergelombang: swing low tiap 10 bar di atas garis support yang naik 0,0005 per bar."""
    rows = []
    for i in range(n):
        base = 1.1000 + 0.0005 * i
        dip = 0.0015 if i % 10 == 5 else 0.0
        rows.append((base + 0.0004, base + 0.0010, base - 0.0002 - dip, base + 0.0006))
    return _bars(rows, step=3600)


def test_ts119_trendline() -> None:
    """TS-119: support naik dari swing low; kemiringan kecil -> tidak ada; close tembus > 0,2 ATR -> patah."""
    h1 = _h1_uptrend()
    line = tl.trendline(h1, len(h1.time), buy=True, atr=ATR, strength=2, lookback=100)
    assert line is not None and line.touches >= 3
    assert line.slope_atr >= 0.02
    flat = _bars(
        [(1.1, 1.1005, 1.0995 - (0.001 if i % 10 == 5 else 0), 1.1) for i in range(60)], step=3600
    )
    assert tl.trendline(flat, 60, buy=True, atr=ATR, strength=2, lookback=100) is None
    broken = _h1_uptrend()
    broken.close[-1] = line.value_at(len(h1.time) - 1) - 0.0003  # > 0,2 ATR di bawah garis
    assert tl.trendline(
        broken, len(broken.time), buy=True, atr=ATR, strength=2, lookback=100
    ) is None or (
        tl.trendline(broken, len(broken.time), buy=True, atr=ATR, strength=2, lookback=100).t2
        != line.t2
    )


def test_ts120_bias() -> None:
    """TS-120: struktur BULL + EMA naik -> BULL; struktur BULL + EMA turun -> NONE (AND_EMA)."""
    assert tl.bias_of(1, 1) == 1
    assert tl.bias_of(1, -1) == 0
    assert tl.bias_of(1, 0) == 0
    assert tl.bias_of(0, 1) == 0
    closes = np.linspace(1.0, 1.2, 80)
    assert tl.ema_dir(closes, period=21, slope_bars=3) == 1
    assert tl.ema_dir(closes[::-1], period=21, slope_bars=3) == -1


def test_ts121_setup_a() -> None:
    """TS-121: sentuh support H1 + pin bullish M15 -> 1 kandidat BUY dengan SL di bawah ekstrem; tanpa pola -> 0."""
    line = tl.Line(i1=0, p1=1.1000, i2=10, p2=1.1050, touches=3, slope_atr=0.5, t2=0)
    lv = line.value_at(20)
    bar = tl.Ohlc(
        [lv + 0.0005, lv + 0.0005, lv + 0.0008],
        [lv + 0.0008, lv + 0.0008, lv + 0.0010],
        [lv + 0.0004, lv + 0.0004, lv - 0.0001],
        [lv + 0.0006, lv + 0.0006, lv + 0.0009],
    )
    hit = tl.setup_a_signal(bar, line, x=20, buy=True, atr_h1=ATR, atr_m15=ATR)
    assert hit is not None and hit.anchor == pytest.approx(min(lv - 0.0001, lv))
    far = 0.0010  # bar sama, digeser menjauh dari garis: pola ada tetapi tidak menyentuh
    away = tl.Ohlc(
        [v + far for v in bar.open],
        [v + far for v in bar.high],
        [v + far for v in bar.low],
        [v + far for v in bar.close],
    )
    assert tl.setup_a_signal(away, line, x=20, buy=True, atr_h1=ATR, atr_m15=ATR) is None
    flat = tl.Ohlc(
        [lv + 0.0005] * 3, [lv + 0.0006] * 3, [lv] * 3, [lv + 0.0005] * 3
    )  # menyentuh tanpa pola
    assert tl.setup_a_signal(flat, line, x=20, buy=True, atr_h1=ATR, atr_m15=ATR) is None


def test_ts122_setup_c_window() -> None:
    """TS-122: retest dalam 20 bar sesudah tembusan diterima; bar ke-21 tidak."""
    tracker = tl.BreakTracker(max_bars=20)
    tracker.on_break(bar_index=100, direction=-1, line=tl.Line(0, 1.1, 10, 1.105, 3, 0.5, 0))
    assert tracker.active(105) is not None
    assert tracker.active(120) is not None
    assert tracker.active(121) is None


def test_ts123_no_lookahead() -> None:
    """TS-123: jendela HTF pada bar M15 t hanya berisi bar yang tutup <= t + 900."""
    h1 = _h1_uptrend()
    t = int(h1.time[10]) + 900  # bar M15 di tengah jam ke-10
    n = tl.closed_count(h1.time, 3600, t)
    assert n == 10  # bar jam ke-10 belum tutup
    assert tl.closed_count(h1.time, 3600, int(h1.time[10]) + 2700) == 10  # masih di dalam jam ke-10
    assert tl.closed_count(h1.time, 3600, int(h1.time[10]) + 3600) == 11  # jam ke-10 sudah tutup


def test_ts124_sequential() -> None:
    """TS-124: kandidat kedua sebelum posisi pertama tutup dilewati."""
    times = [100, 200, 300]
    closes = {100: 250, 300: 400}
    taken = tl.sequential(times, lambda t: closes.get(t, t + 10))
    assert taken == [100, 300]
