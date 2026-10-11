"""Laporan faktor profit dan per tahap tolak (spec 31 Req 4, 5): TS-110, TS-111."""

import factor_report as fr
import pytest


def _recs(period: str, bucket_rs: dict[str, list[float]]) -> list[fr.Record]:
    out = []
    for bucket, rs in bucket_rs.items():
        for r in rs:
            out.append(fr.Record(period=period, factors={"zona": bucket}, r=r))
    return out


def test_ts110_consistency_labels() -> None:
    """TS-110: KONSISTEN+ / KONSISTEN- / TIDAK KONSISTEN / SAMPEL KURANG sesuai definisi glosarium."""
    recs: list[fr.Record] = []
    # A selalu di atas rata-rata, B selalu di bawah, C naik-turun, D < 10 trade di OOS
    for period, c_r in (("IS", 1.0), ("OOS", -1.0), ("REAL", 1.0)):
        recs += _recs(
            period,
            {
                "A": [1.0] * 10,
                "B": [-1.0] * 10,
                "C": [c_r] * 10,
                "D": [0.5] * (5 if period == "OOS" else 10),
            },
        )
    table = fr.factor_table(recs, ["IS", "OOS", "REAL"])
    labels = {bucket: row.label for (factor, bucket), row in table.items()}
    assert labels["A"] == "KONSISTEN+"
    assert labels["B"] == "KONSISTEN-"
    assert labels["C"] == "TIDAK KONSISTEN"
    assert labels["D"] == "SAMPEL KURANG"
    a = table[("zona", "A")]
    assert a.stats["IS"] == (10, pytest.approx(1.0))
    text = fr.render_factors(table, ["IS", "OOS", "REAL"])
    assert "KONSISTEN+" in text and "zona" in text


def test_ts110_buckets_from_context() -> None:
    """TS-110: bucket faktor dari context_json (batas design §3.3)."""
    ctx = {
        "zone_status": "FRESH",
        "tl_touches": 3,
        "tl_dist": 0.15,
        "pa": "PIN",
        "score_pct": 72.7,
        "bias_reason": "OK",
        "rr": 2.6,
        "tp_source": "ZONE",
        "atr_mtf": 0.0010,
    }
    f = fr.factors_of(
        ctx, direction="SELL", time=1_780_000_200 + 14 * 3600, symbol="EURUSDc", atr_tier="2"
    )
    assert f["status zona"] == "FRESH"
    assert f["trendline"] == "3+ sentuhan"
    assert f["jarak trendline"] == "0,1-0,2 ATR"
    assert f["pola PA"] == "PIN"
    assert f["persen skor"] == "65-75"
    assert f["R:R rencana"] == "2-3"
    assert f["sumber TP"] == "ZONE"
    assert f["arah"] == "SELL"
    assert f["simbol"] == "EURUSDc"
    assert f["rezim ATR"] == "2"
    none = fr.factors_of({}, direction="BUY", time=1_780_000_200, symbol="X", atr_tier="1")
    assert none["trendline"] == "tanpa garis"
    assert none["R:R rencana"] == "-"


def test_ts111_stages_and_dedup() -> None:
    """TS-111: per tahap tolak: kandidat, tersimulasi, R/trade, PF, % lolos aturan; dedup zona per hari."""
    day = 1_780_000_200 - (1_780_000_200 % 86400)
    cands = [
        fr.Cand("NO_PA_TRIGGER", "EURUSDc", "H1-1-D", day + 3600, r=1.0, passes=True),
        fr.Cand(
            "NO_PA_TRIGGER", "EURUSDc", "H1-1-D", day + 4500, r=-1.0, passes=True
        ),  # zona sama, hari sama
        fr.Cand("NO_PA_TRIGGER", "EURUSDc", "H1-2-D", day + 3600, r=-1.0, passes=False),
        fr.Cand("SCORE_TOO_LOW", "GBPUSDc", "H1-3-S", day + 3600, r=2.0, passes=True),
        fr.Cand("ACCEPTED", "GBPUSDc", "H1-4-S", day + 3600, r=0.5, passes=True, real_r=0.4),
        fr.Cand(
            "NO_PA_TRIGGER", "EURUSDc", "H1-5-D", day + 3600, r=None, passes=False
        ),  # tidak tersimulasi
    ]
    rows = {r.stage: r for r in fr.stage_table(cands, dedup=False)}
    pa = rows["NO_PA_TRIGGER"]
    assert pa.candidates == 4
    assert pa.simulated == 3
    assert pa.r_avg == pytest.approx(-1 / 3)
    assert pa.pf == pytest.approx(0.5)
    assert pa.pass_pct == pytest.approx(200 / 3)
    assert rows["ACCEPTED"].real_r_avg == pytest.approx(0.4)
    dedup = {r.stage: r for r in fr.stage_table(cands, dedup=True)}
    assert dedup["NO_PA_TRIGGER"].candidates == 3
    assert dedup["NO_PA_TRIGGER"].r_avg == pytest.approx(0.0)
    assert "NO_PA_TRIGGER" in fr.render_stages(fr.stage_table(cands, dedup=False))
