"""Replay periode live dan perbandingan dengan tester (spec 29): TS-128..105."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import live_compare as lc
import pytest

SCHEMA = Path(__file__).resolve().parents[2] / "shared" / "schema" / "data_db.sql"
T0 = int(datetime(2026, 10, 9, tzinfo=UTC).timestamp())
H = 3600
ENUMS = """
enum ENUM_SDB_LOG_LEVEL
  {
   SDB_LOG_DEBUG = 0,
   SDB_LOG_INFO = 1,      // komentar
  };
enum ENUM_SDB_COMPONENT_MODE { SDB_COMPONENT_OFF = 0, SDB_COMPONENT_SHADOW = 1, SDB_COMPONENT_ACTIVE = 2 };
#define SDB_SOMETHING 7
"""
INPUTS = {
    "InpMagicNumber": 2026091901,
    "InpAllowLiveTrading": True,
    "InpRiskPerTradePct": 0.1,
    "InpTelegramConfigured": True,
    "InpLogLevel": "SDB_LOG_INFO",
    "InpScoreFibMode": "SDB_COMPONENT_SHADOW",
    "InpAllowTestedZones": False,
    "InpMinRR": 2.0,
    "InpSymbolSuffix": "c",
}


def _db(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    return path


def _session(conn, sid, symbol, start, end=None, inputs=None, mode="LIVE", tfrom=None, tto=None):
    data = json.dumps(inputs or INPUTS, sort_keys=True)
    conn.execute(
        "INSERT INTO sessions (id, login, magic, symbol, mode, ea_version, input_hash, inputs_json, started_at, "
        "ended_at, tester_from, tester_to, run_key) VALUES (?, 1, 2026091901, ?, ?, '1.25', ?, ?, ?, ?, ?, ?, ?)",
        (
            sid,
            symbol,
            mode,
            str(hash(data)),
            data,
            start,
            end,
            tfrom,
            tto,
            sid if mode == "TESTER" else 0,
        ),
    )


@pytest.fixture
def types_file(tmp_path: Path) -> Path:
    p = tmp_path / "Types.mqh"
    p.write_text(ENUMS, encoding="utf-8")
    return p


def test_ts128_enum_values(types_file: Path) -> None:
    e = lc.enum_values(types_file)
    assert e["SDB_LOG_INFO"] == 1 and e["SDB_COMPONENT_ACTIVE"] == 2 and e["SDB_LOG_DEBUG"] == 0
    assert "SDB_SOMETHING" not in e


def test_ts129_replay_inputs(tmp_path: Path, types_file: Path) -> None:
    db = _db(tmp_path / "live.sqlite")
    conn = sqlite3.connect(db)
    _session(conn, 1, "EURUSDc", T0, T0 + 2 * H)
    _session(conn, 2, "EURUSDc", T0 + 3 * H)  # hash sama, restart
    conn.commit()
    enums = lc.enum_values(types_file)
    items = lc.replay_inputs(conn, "EURUSDc", T0, T0 + 24 * H, enums)
    d = dict(x.split("=", 1) for x in items)
    for dropped in ("InpAllowLiveTrading", "InpRiskPerTradePct", "InpTelegramConfigured"):
        assert dropped not in d
    assert d["InpLogLevel"] == "1" and d["InpScoreFibMode"] == "1"
    assert (
        d["InpAllowTestedZones"] == "false"
        and d["InpMinRR"] == "2.0"
        and d["InpSymbolSuffix"] == "c"
    )
    assert d["InpMagicNumber"] == "2026091901"
    changed = dict(INPUTS, InpMinRR=3.0)
    _session(conn, 3, "EURUSDc", T0 + 5 * H, inputs=changed)
    conn.commit()
    with pytest.raises(lc.ReplayInputError) as err:
        lc.replay_inputs(conn, "EURUSDc", T0, T0 + 24 * H, enums)
    assert "2026-10-09 05:00" in str(err.value)
    with pytest.raises(lc.ReplayInputError):
        lc.replay_inputs(conn, "GBPUSDc", T0, T0 + 24 * H, enums)  # tidak ada sesi
    conn.execute("UPDATE sessions SET ea_version = '1.24' WHERE id = 3")
    conn.commit()
    only = dict(
        x.split("=", 1)
        for x in lc.replay_inputs(conn, "EURUSDc", T0, T0 + 24 * H, enums, version="1.25")
    )
    assert only["InpMinRR"] == "2.0"  # sesi 1.24 dengan input lain diabaikan
    conn.close()


def _c(symbol, t, stage, direction="BUY", score=40):
    return lc.Cand(symbol, t, direction, stage, score)


def test_ts130_pair_candidates() -> None:
    win = {"EURUSDc": [(T0, T0 + 4 * H)]}
    live = [
        _c("EURUSDc", T0 + 900, "SCORE_TOO_LOW"),
        _c("EURUSDc", T0 + 1800, "SPREAD_TOO_WIDE"),
        _c("EURUSDc", T0 + 2700, "ACCEPTED"),
        _c("EURUSDc", T0 + 5 * H, "ACCEPTED"),  # di luar jendela live
    ]
    replay = [
        _c("EURUSDc", T0 + 900, "NO_PA_TRIGGER"),
        _c("EURUSDc", T0 + 1800, "ACCEPTED"),
        _c("EURUSDc", T0 + 2700, "ACCEPTED"),
        _c("EURUSDc", T0 + 3600, "NO_PA_TRIGGER"),
        _c("EURUSDc", T0 + 5 * H, "ACCEPTED"),  # di luar jendela live
    ]
    p = lc.pair_candidates(live, replay, win)
    assert (p.n_live, p.n_replay, p.same) == (3, 4, 1)
    assert [x[0].stage for x in p.diff_unknown] == ["SCORE_TOO_LOW"]
    assert [x[0].stage for x in p.diff_known] == ["SPREAD_TOO_WIDE"]
    assert p.only_live == [] and [x.time for x in p.only_replay] == [T0 + 3600]
    assert p.match_live == pytest.approx(0.5) and p.match_replay == pytest.approx(1 / 3)
    nn = lc.pair_candidates(
        [_c("EURUSDc", T0 + 900, "NEWS_BLACKOUT")],
        [_c("EURUSDc", T0 + 900, "NO_PA_TRIGGER")],
        win,
        no_news=True,
    )
    assert (nn.n_live, nn.n_replay, nn.same) == (0, 0, 0) and nn.match_live is None


def _t(symbol, opened, reason, r, direction="BUY", price=1.1000, sl=1.0950):
    return lc.Trade(symbol, direction, opened, reason, r, price, sl)


def test_ts131_pair_trades() -> None:
    live = [
        _t("EURUSDc", T0 + 600, "TP", 2.0, price=1.1002),
        _t("EURUSDc", T0 + 2 * H, "SL", -1.0),
        _t("EURUSDc", T0 - H, "SL", -1.0),  # dibuka sebelum periode
        _t("GBPUSDc", T0 + H, "BE_STOP", 0.2),
    ]
    replay = [
        _t("EURUSDc", T0 + 600 + 600, "TP", 1.9),  # 10 menit -> pasangan
        _t("EURUSDc", T0 + 2 * H + 1200, "SL", -1.0),  # 20 menit -> bukan pasangan
        _t("GBPUSDc", T0 + H, "TRAIL_STOP", 0.8),
    ]
    p = lc.pair_trades(live, replay, T0)
    assert p.n_live == 3 and p.excluded == 1
    assert len(p.pairs) == 2 and len(p.only_live) == 1 and len(p.only_replay) == 1
    assert p.reason_same == pytest.approx(0.5)
    assert p.r_diff_avg == pytest.approx((0.1 + 0.6) / 2) and p.r_diff_max == pytest.approx(0.6)
    assert p.open_diff_r_avg == pytest.approx((0.0002 / 0.0052 + 0.0) / 2)


def test_ts132_assess() -> None:
    cands = lc.CandidatePairs(n_live=100, n_replay=100, same=97)
    trades = lc.TradePairs(n_live=20, pairs=[(None, None)] * 19, reason_same=0.95, r_diff_avg=0.05)
    status = {name: st for name, _v, _thr, st in lc.assess(cands, trades)}
    assert set(status.values()) == {"LOLOS"}
    low = lc.CandidatePairs(n_live=100, n_replay=100, same=94)
    assert {n: st for n, _v, _t2, st in lc.assess(low, trades)}["kandidat live cocok"] == "TIDAK"
    few = lc.TradePairs(n_live=5, pairs=[(None, None)] * 5, reason_same=1.0, r_diff_avg=0.0)
    st_few = {n: st for n, _v, _t2, st in lc.assess(cands, few)}
    assert (
        st_few["trade live berpasangan"] == "SAMPEL KURANG"
        and st_few["selisih R rata-rata"] == "SAMPEL KURANG"
    )


def test_ts133_extra_inputs_and_cli(
    tmp_path: Path, types_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert lc.extra_inputs({"A": 1}, {"A": 1, "InpSessionEndHourUtc": 22}) == {
        "InpSessionEndHourUtc": 22
    }
    live = _db(tmp_path / "live.sqlite")
    conn = sqlite3.connect(live)
    _session(conn, 1, "EURUSDc", T0)
    _session(conn, 2, "EURUSDc", T0 + H, inputs=dict(INPUTS, InpMinRR=3.0))
    conn.commit()
    conn.close()
    base = ["--db", str(live), "--from", "2026-10-09", "--to", "2026-10-10"]
    assert lc.main(["inputs", "EURUSDc", "--types", str(types_file), *base]) == 3
    assert (
        lc.main(["compare", *base, "--tester", str(tmp_path / "x.sqlite"), "--replay", "1-2"]) == 1
    )
    tester = _db(tmp_path / "tester.sqlite")
    assert lc.main(["compare", *base, "--tester", str(tester), "--replay", "5-1"]) == 2
    out = tmp_path / "cmp.txt"
    capsys.readouterr()
    assert (
        lc.main(["compare", *base, "--tester", str(tester), "--replay", "1-2", "--out", str(out)])
        == 0
    )
    assert out.read_text(encoding="utf-8").strip() == capsys.readouterr().out.strip()


def test_ts134_legacy_inputs(tmp_path: Path, types_file: Path) -> None:
    """Spec 29 (penyesuaian v1.28): input yang belum ada di sesi live diisi nilai perilaku lama, bukan default baru."""
    db = _db(tmp_path / "live.sqlite")
    conn = sqlite3.connect(db)
    _session(
        conn, 1, "EURUSDc", T0
    )  # INPUTS: punya InpAllowTestedZones, tanpa input bias dan jam akhir
    conn.commit()
    d = dict(
        x.split("=", 1)
        for x in lc.replay_inputs(conn, "EURUSDc", T0, T0 + H, lc.enum_values(types_file))
    )
    conn.close()
    assert (
        d["InpBiasMode"] == "0"
        and d["InpBiasEmaPeriod"] == "0"
        and d["InpSessionEndHourUtc"] == "22"
    )
    assert d["InpAllowTestedZones"] == "false"  # nilai live menang atas nilai lama
    assert "InpAllowTestedZones" in lc.LEGACY_INPUTS
