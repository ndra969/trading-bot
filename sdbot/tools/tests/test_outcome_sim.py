"""Simulator hasil kandidat (spec 31 Req 2): TS-100..108."""

from pathlib import Path

import numpy as np
import outcome_sim as osim
import pytest

T0 = 1_780_000_200  # kelipatan 900: awal bar M15 kandidat
POINT = 0.00001


def _cand(direction: str = "BUY", opp: float | None = None, **kw: float) -> osim.Candidate:
    base: dict = {
        "signal_id": 1,
        "session_id": 1,
        "symbol": "EURUSDc",
        "time": T0,
        "direction": direction,
        "stage": None,
        "zone_prox": 1.10060 if direction == "BUY" else 1.10140,
        "zone_dist": 1.10000 if direction == "BUY" else 1.10200,
        "opp_prox": opp,
        "bid": 1.10080,
        "ask": 1.10090,
        "atr_mtf": 0.0010,
        "point": POINT,
        "digits": 5,
    }
    base.update(kw)
    return osim.Candidate(**base)


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


def _bars(rows: list[tuple[float, float, float, float]], start: int = T0 + 900) -> osim.Bars:
    """Bar M1 (bid) mulai `start`, satu per menit, spread 10 point."""
    n = len(rows)
    arr = np.array(rows, dtype=float).reshape(n, 4)
    return osim.Bars(
        time=np.arange(start, start + 60 * n, 60, dtype=np.int64),
        open=arr[:, 0],
        high=arr[:, 1],
        low=arr[:, 2],
        close=arr[:, 3],
        point=POINT,
        digits=5,
    )


def _flat_atr(value: float = 0.0005) -> osim.Atr:
    return osim.Atr(time=np.array([0], dtype=np.int64), value=np.array([value]))


def test_ts100_build_stops_matches_ea() -> None:
    """TS-100: angka F0 TC-SG-21 (BUY, zona lawan 1.10350): SL 1.09990, TP 1.10350, R:R 2,60; SELL + spread."""
    s = osim.build_stops(_cand(opp=1.10350), RULES)
    assert s.entry == pytest.approx(1.10090)
    assert s.sl == pytest.approx(1.09990)
    assert s.tp == pytest.approx(1.10350)
    assert s.rr == pytest.approx(2.60)
    assert s.passes_rules
    sell = osim.build_stops(_cand("SELL"), RULES)
    # SELL: entry bid 1.10080, SL = distal 1.10200 + 0,1 ATR + spread 0.00010 = 1.10220; TP 2R
    assert sell.entry == pytest.approx(1.10080)
    assert sell.sl == pytest.approx(1.10220)
    assert sell.tp == pytest.approx(1.10080 - 2 * 0.00140)
    assert sell.passes_rules


def test_ts101_sl_and_tp() -> None:
    """TS-101: BUY langsung kena SL = -1R; BUY kena TP tanpa BE = +R:R."""
    c = _cand(opp=1.10350)
    sl_bars = _bars([(1.10080, 1.10085, 1.09980, 1.09985)])
    out = osim.simulate(c, RULES, sl_bars, _flat_atr())
    assert out.reason == "SL"
    assert out.r == pytest.approx(-1.0)
    tp_bars = _bars([(1.10080, 1.10360, 1.10075, 1.10355)])
    out = osim.simulate(c, RULES, tp_bars, _flat_atr())
    assert out.reason == "TP"
    # partial 50% di 1,5R terpicu di bar yang sama sebelum TP: 0,5 x 1,5 + 0,5 x 2,6
    assert out.r == pytest.approx(0.5 * 1.5 + 0.5 * 2.6)


def test_ts102_breakeven() -> None:
    """TS-102: naik 1R lalu kembali: BE aktif mulai bar berikut, keluar di entry + (spread + 2) point."""
    c = _cand(opp=1.10350)
    bars = _bars(
        [
            (
                1.10080,
                1.10195,
                1.10075,
                1.10190,
            ),  # +1R (risk 0.00100 dari entry ask 1.10090; bid 1.10190)
            (1.10190, 1.10195, 1.10050, 1.10060),  # turun menembus BE
        ]
    )
    out = osim.simulate(c, RULES, bars, _flat_atr())
    be = 1.10090 + 12 * POINT
    assert out.reason == "BE_STOP"
    assert out.r == pytest.approx((be - 1.10090) / 0.00100)


def test_ts103_partial_then_trailing() -> None:
    """TS-103: naik 1,6R (partial 50% di 1,5R), BE, lalu trailing ATR x 2 kena: alasan TRAIL_STOP."""
    c = _cand(opp=1.10600)
    atr = 0.00020
    bars = _bars(
        [
            (1.10080, 1.10250, 1.10075, 1.10245),  # +1,6R: partial + BE dihitung
            (
                1.10245,
                1.10300,
                1.10240,
                1.10295,
            ),  # BE aktif; trailing = 1.10300 - 0.00040 = 1.10260
            (1.10295, 1.10296, 1.10200, 1.10210),  # kena trailing 1.10260
        ]
    )
    out = osim.simulate(c, RULES, bars, _flat_atr(atr))
    assert out.reason == "TRAIL_STOP"
    assert out.r == pytest.approx(0.5 * 1.5 + 0.5 * (1.10260 - 1.10090) / 0.00100)


def test_ts104_same_bar_sl_first() -> None:
    """TS-104: SL dan TP di bar M1 yang sama: SL (konservatif)."""
    c = _cand(opp=1.10350)
    bars = _bars([(1.10080, 1.10400, 1.09900, 1.10100)])
    out = osim.simulate(c, RULES, bars, _flat_atr())
    assert out.reason == "SL"
    assert out.r == pytest.approx(-1.0)


def test_ts105_gap_through_sl() -> None:
    """TS-105: open bar melewati SL: keluar di open, R < -1."""
    c = _cand(opp=1.10350)
    bars = _bars([(1.10080, 1.10085, 1.10070, 1.10075), (1.09900, 1.09950, 1.09880, 1.09940)])
    out = osim.simulate(c, RULES, bars, _flat_atr())
    assert out.reason == "SL"
    assert out.r == pytest.approx((1.09900 - 1.10090) / 0.00100)
    assert out.r < -1.0


def test_ts106_sell_exits_at_ask() -> None:
    """TS-106: SELL keluar di ask = bid + spread: TP tersentuh saat ask <= TP."""
    c = _cand("SELL")
    s = osim.build_stops(c, RULES)
    # TP 1.09800 (2R); bid 1.09795 -> ask 1.09805 belum kena; bid 1.09785 -> ask 1.09795 kena
    bars = _bars([(1.10080, 1.10085, 1.09795, 1.09800), (1.09800, 1.09802, 1.09785, 1.09790)])
    out = osim.simulate(c, RULES, bars, _flat_atr())
    assert s.tp == pytest.approx(1.09800)
    assert out.reason == "TP"
    assert out.r == pytest.approx(0.5 * 1.5 + 0.5 * 2.0)


def test_ts107_skip_and_end() -> None:
    """TS-107: kandidat tanpa harga zona dilewati; bar habis sebelum tutup = END di close terakhir."""
    assert osim.candidate_from_row({"zone_prox": None, "zone_dist": 1.1}, {}) is None
    c = _cand(opp=1.10350)
    bars = _bars([(1.10080, 1.10120, 1.10070, 1.10110)])
    out = osim.simulate(c, RULES, bars, _flat_atr())
    assert out.reason == "END"
    assert out.open_at_end
    assert out.r == pytest.approx((1.10110 - 1.10090) / 0.00100)


def test_ts108_m15_atr(tmp_path: Path) -> None:
    """TS-108: ATR SMA dari TR M15 hasil agregasi M1 (sama dengan iATR), nilai bar M15 tertutup terakhir."""
    rows = []
    start = T0
    for k in range(3):  # 3 bar M15 x 15 menit
        for m in range(15):
            base = 1.0 + 0.01 * k
            rows.append((base, base + 0.002 if m == 7 else base + 0.001, base - 0.001, base))
    bars = _bars(rows, start=start)
    atr = osim.m15_atr(bars, period=2)
    # M15: H-L = 0.003 tiap bar; TR bar 2 dan 3 = max(H, prevC) - min(L, prevC) = 0.003 (prevC di dalam rentang... )
    # bar k: H = base+0.002, L = base-0.001, prevC = base-0.01 -> TR = (base+0.002) - (base-0.01) = 0.012
    assert atr.value_at(start + 2 * 900 + 60) == pytest.approx((0.003 + 0.012) / 2)
    # di tengah bar M15 ke-2, nilai yang dipakai = ATR bar M15 tertutup terakhir (bar 1): belum cukup 2 bar -> 0
    assert atr.value_at(start + 900 + 60) == 0.0
    csv = tmp_path / "EURUSDc_M1.csv"
    csv.write_text(
        "# symbol=EURUSDc point=0.00001 digits=5\ntime,open,high,low,close,spread\n"
        f"{T0},1.1,1.2,1.0,1.1,10\n{T0 + 60},1.1,1.3,1.0,1.2,12\n",
        encoding="utf-8",
    )
    b = osim.load_bars(csv)
    assert b.point == POINT and b.digits == 5 and len(b.time) == 2
    assert (tmp_path / "EURUSDc_M1.npz").is_file()
    assert len(osim.load_bars(csv).time) == 2


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sc31_accepted.json"
SCHEMA = Path(__file__).resolve().parents[2] / "shared" / "schema" / "data_db.sql"
INPUTS = {
    "InpSlBufferAtr": 0.1,
    "InpMinRR": 2.0,
    "InpMinSlAtr": 0.3,
    "InpMaxSlAtr": 3.0,
    "InpBreakevenR": 1.0,
    "InpBreakevenBufferPoints": 2,
    "InpPartialR": 1.5,
    "InpPartialPct": 50.0,
    "InpTrailATRPeriod": 14,
    "InpTrailATRMult": 2.0,
}


def test_ts112_build_stops_matches_harness_context() -> None:
    """TS-112: SL/TP dari kunci context run harness 1.29 (SC-31) sama dengan sl/tp yang dicatat EA."""
    import json

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rules = osim.exit_rules_from_inputs(data["inputs"])
    assert len(data["signals"]) >= 4
    for sig in data["signals"]:
        ctx = sig["context"]
        c = osim.candidate_from_row(ctx, {**sig, "point": data["point"], "digits": data["digits"]})
        assert c is not None
        s = osim.build_stops(c, rules)
        assert s.sl == pytest.approx(ctx["sl"], abs=1e-9), sig["id"]
        assert s.tp == pytest.approx(ctx["tp"], abs=1e-9), sig["id"]
        assert s.passes_rules


def _write_bars(path: Path, rows: list[tuple[int, float, float, float, float]]) -> None:
    lines = ["# symbol=EURUSDc point=0.00001 digits=5", "time,open,high,low,close,spread"]
    lines += [f"{t},{o},{h},{lo},{c},10" for t, o, h, lo, c in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_ts109_calibrate(tmp_path: Path) -> None:
    """TS-109: 3 trade nyata, simulasi cocok 2 (SL, TP) dan beda 1 -> 66,7% alasan sama, kalibrasi gagal."""
    import json
    import sqlite3

    db = tmp_path / "t.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.execute(
        "INSERT INTO sessions (id, login, magic, symbol, mode, ea_version, input_hash, inputs_json, started_at, run_key) "
        "VALUES (1, 1, 2026091901, 'EURUSDc', 'TESTER', '1.29', 'h', ?, 0, 1)",
        (json.dumps(INPUTS),),
    )
    days = [T0, T0 + 86400, T0 + 2 * 86400]
    real = [("SL", -1.0), ("TP", 2.0), ("SL", -1.0)]
    ctx = {
        "zone_prox": 1.10060,
        "zone_dist": 1.10000,
        "opp_prox": None,
        "bid": 1.10080,
        "ask": 1.10090,
        "atr_mtf": 0.0010,
    }
    for k, (t, (reason, r)) in enumerate(zip(days, real, strict=True), start=1):
        conn.execute(
            "INSERT INTO signals (id, session_id, login, magic, symbol, time, direction, style, spread_points, status, "
            "context_json) VALUES (?, 1, 1, 2026091901, 'EURUSDc', ?, 'BUY', 'DAY', 10, 'ACCEPTED', ?)",
            (k, t, json.dumps(ctx)),
        )
        conn.execute(
            "INSERT INTO trades (session_id, login, run_key, position_id, magic, symbol, direction, source, "
            "volume_initial, price_open, sl_initial, tp_initial, signal_id, ea_version, opened_at) "
            "VALUES (1, 1, 1, ?, 2026091901, 'EURUSDc', 'BUY', 'EA', 1, 1.1009, 1.0999, 1.1029, ?, '1.29', ?)",
            (k, k, t + 900),
        )
        conn.execute(
            "INSERT INTO closures (session_id, login, run_key, position_id, magic, symbol, closed_at, reason, "
            "price_close, volume_total, profit, commission, swap, fee, net_profit, r_result, mfe_r, holding_sec, "
            "be_activated, partial_done, trail_activated) "
            "VALUES (1, 1, 1, ?, 2026091901, 'EURUSDc', ?, ?, 1, 1, 0, 0, 0, 0, ?, ?, 0, 60, 0, 0, 0)",
            (k, t + 1000, reason, r * 10, r),
        )
    conn.commit()
    conn.close()
    # hari 1 kena SL, hari 2 kena TP 2R (partial 1,5R dulu), hari 3 juga TP (beda dengan nyata SL)
    rows = [(days[0] + 900, 1.10080, 1.10085, 1.09980, 1.09985)]
    rows += [(days[1] + 900, 1.10080, 1.10300, 1.10075, 1.10295)]
    rows += [(days[2] + 900, 1.10080, 1.10300, 1.10075, 1.10295)]
    bars_dir = tmp_path / "bars"
    bars_dir.mkdir()
    _write_bars(bars_dir / "EURUSDc_M1.csv", rows)
    conn = sqlite3.connect(db)
    rep = osim.calibrate(conn, [(1, 1)], bars_dir)
    conn.close()
    assert rep.n == 3
    assert rep.same_reason_pct == pytest.approx(200 / 3)
    sim_tp = 0.5 * 1.5 + 0.5 * 2.0
    assert rep.sim_r == pytest.approx((-1.0 + 2 * sim_tp) / 3)
    assert rep.real_r == pytest.approx(0.0)
    assert rep.mean_abs_diff == pytest.approx((0 + abs(sim_tp - 2.0) + abs(sim_tp + 1.0)) / 3)
    assert not rep.passed
    assert "GAGAL" in osim.render_calibration([("IS", rep)])
