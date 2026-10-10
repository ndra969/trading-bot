"""Laporan DB live (spec 28): TS-120..99."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import live_report as lr
import pytest

SCHEMA = Path(__file__).resolve().parents[2] / "shared" / "schema" / "data_db.sql"
T0 = int(datetime(2026, 10, 9, tzinfo=UTC).timestamp())
H = 3600


def _session(conn, sid, symbol, version, start, end=None, mode="LIVE", magic=2026091901):
    conn.execute(
        "INSERT INTO sessions (id, login, magic, symbol, mode, ea_version, input_hash, inputs_json, started_at, "
        "ended_at, end_reason, run_key) VALUES (?, 1, ?, ?, ?, ?, 'h', '{}', ?, ?, ?, 0)",
        (sid, magic, symbol, mode, version, start, end, "CLOSE" if end else None),
    )


def _trade(
    conn,
    sid,
    pos,
    symbol,
    opened,
    closed=None,
    r=None,
    reason="SL",
    requested=1.1000,
    price=1.1000,
    sl=1.0950,
    spread=10,
    close_slip=0,
):
    conn.execute(
        "INSERT INTO trades (session_id, login, run_key, position_id, magic, symbol, direction, source, "
        "volume_initial, price_requested, price_open, slippage_points, spread_points, sl_initial, tp_initial, "
        "ea_version, opened_at) VALUES (?, 1, 0, ?, 2026091901, ?, 'BUY', 'EA', 1, ?, ?, ?, ?, ?, 1.2, '1.25', ?)",
        (
            sid,
            pos,
            symbol,
            requested,
            price,
            round(abs(price - requested) / 0.00001),
            spread,
            sl,
            opened,
        ),
    )
    if closed is not None:
        conn.execute(
            "INSERT INTO closures (session_id, login, run_key, position_id, magic, symbol, closed_at, reason, "
            "price_close, slippage_points, volume_total, profit, commission, swap, fee, net_profit, r_result, "
            "holding_sec, be_activated, partial_done, trail_activated) "
            "VALUES (?, 1, 0, ?, 2026091901, ?, ?, ?, 1, ?, 1, 0, 0, 0, 0, ?, ?, 60, 0, 0, 0)",
            (sid, pos, symbol, closed, reason, close_slip, r * 10, r),
        )


def _signal(conn, sid, sig_id, symbol, t, stage=None):
    conn.execute(
        "INSERT INTO signals (id, session_id, login, magic, symbol, time, direction, style, score_total, "
        "spread_points, status, reject_stage) VALUES (?, ?, 1, 2026091901, ?, ?, 'BUY', 'DAY', 40, 5, ?, ?)",
        (sig_id, sid, symbol, t, "REJECTED" if stage else "ACCEPTED", stage),
    )


def _alert(conn, sid, t, kind, sev, status, msg="pesan"):
    conn.execute(
        "INSERT INTO alerts (session_id, login, magic, symbol, time, type, severity, message, status) "
        "VALUES (?, 1, 2026091901, 'EURUSDc', ?, ?, ?, ?, ?)",
        (sid, t, kind, sev, msg, status),
    )


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "live.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    _session(
        conn, 1, "EURUSDc", "1.24", T0 - 10 * H, T0 - 2 * H
    )  # 1.24, berakhir sebelum periode uji
    _session(conn, 2, "EURUSDc", "1.25", T0, T0 + 1 * H)
    _session(conn, 3, "EURUSDc", "1.25", T0 + 2 * H)  # masih aktif
    _session(conn, 4, "GBPUSDc", "1.25", T0, T0 + 1 * H, magic=2026091902)
    _session(conn, 9, "EURUSDc", "1.25", T0, T0 + 5 * H, mode="TESTER")
    conn.commit()
    conn.close()
    return path


def _add(db: Path, fn) -> None:
    conn = sqlite3.connect(db)
    fn(conn)
    conn.commit()
    conn.close()


def _scope(db: Path, frm=None, to=None, version=None) -> lr.Scope:
    with sqlite3.connect(db) as conn:
        return lr.resolve_scope(conn, frm, to, version)


def test_ts120_scope(db: Path) -> None:
    s = _scope(db, version="1.25", to=T0 + 4 * H)
    assert s.session_ids == [2, 3, 4]
    s_all = _scope(db, to=T0 + 4 * H)
    assert (
        s_all.session_ids == [1, 2, 3, 4] and s_all.start == T0 - 10 * H
    )  # TESTER (9) tidak pernah ikut
    assert _scope(db, version="9.99", to=T0).session_ids == []


def test_ts121_trade_stats(db: Path) -> None:
    def fill(conn):
        _trade(
            conn, 1, 1, "EURUSDc", T0 - 3 * H, T0 + 600, 2.0, "TP"
        )  # buka sebelum periode, tutup di dalam
        _trade(conn, 2, 2, "EURUSDc", T0 + 700, T0 + 1200, -1.0, "SL")
        _trade(conn, 4, 3, "GBPUSDc", T0 + 800, T0 + 1800, 0.3, "BE_STOP")
        _trade(conn, 3, 4, "EURUSDc", T0 + 2 * H, T0 + 3 * H, -1.0, "SL")
        _trade(conn, 3, 5, "EURUSDc", T0 + 3 * H + 60)  # masih terbuka

    _add(db, fill)
    with sqlite3.connect(db) as conn:
        t = lr.trade_stats(conn, _scope(db, frm=T0, to=T0 + 4 * H))
    total = t.total
    assert total.n == 4 and total.total_r == pytest.approx(0.3)
    assert total.pf_r == pytest.approx(1.15)
    assert total.dd_r == pytest.approx(1.7)
    assert total.win_pct == pytest.approx(50.0)
    assert t.per_symbol["GBPUSDc"].n == 1
    assert t.reasons["SL"] == (2, pytest.approx(-1.0))
    assert t.open_positions == {"EURUSDc": 1}


def test_ts122_no_trades(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        t = lr.trade_stats(conn, _scope(db, frm=T0, to=T0 + 4 * H))
    assert (
        t.total.n == 0
        and t.total.r_per_trade is None
        and t.total.pf_r is None
        and t.total.dd_r == 0.0
    )
    out = lr.render(_scope(db, frm=T0, to=T0 + 4 * H), t)
    assert "0 trade" in out


def test_ts127_cli(db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert lr.main(["--db", str(tmp_path / "tidak_ada.sqlite")]) == 1
    assert lr.main(["--db", str(db), "--from", "2026-10-10", "--to", "2026-10-09"]) == 2
    assert lr.main(["--db", str(db), "--from", "2026-13-01"]) == 2
    out_file = tmp_path / "lap.txt"
    capsys.readouterr()  # buang pesan error panggilan sebelumnya
    assert (
        lr.main(
            ["--db", str(db), "--from", "2026-10-09", "--to", "2026-10-10", "--out", str(out_file)]
        )
        == 0
    )
    printed = capsys.readouterr().out
    assert out_file.read_text(encoding="utf-8").strip() == printed.strip()
    assert lr.default_db().name == "sdbot.sqlite"


def test_ts123_exec_stats(db: Path) -> None:
    def fill(conn):
        _trade(
            conn,
            2,
            1,
            "EURUSDc",
            T0 + 600,
            T0 + 1200,
            -1.0,
            "SL",
            requested=1.1000,
            price=1.1005,
            sl=1.0955,
            spread=12,
            close_slip=3,
        )
        _trade(
            conn,
            2,
            2,
            "EURUSDc",
            T0 + 700,
            T0 + 1300,
            1.0,
            "TP",
            requested=1.1000,
            price=1.1000,
            sl=0.0,
            spread=8,
            close_slip=0,
        )

    _add(db, fill)
    with sqlite3.connect(db) as conn:
        e = lr.exec_stats(conn, _scope(db, frm=T0, to=T0 + 4 * H))
    eur = e.per_symbol["EURUSDc"]
    assert eur.n == 2 and eur.slip_pts_avg == pytest.approx(25.0) and eur.slip_pts_max == 50
    assert eur.slip_r_avg == pytest.approx(0.1)  # trade dengan SL awal 0 dilewati
    assert eur.spread_avg == pytest.approx(10.0)
    assert e.close_slip["SL"] == pytest.approx(3.0) and e.close_slip["TP"] == pytest.approx(0.0)


def test_ts124_candidates(db: Path) -> None:
    def fill(conn):
        _signal(conn, 2, 1, "EURUSDc", T0 + 900)
        _signal(conn, 2, 2, "EURUSDc", T0 + 1800, "NO_PA_TRIGGER")
        _signal(conn, 4, 3, "GBPUSDc", T0 + 1800, "NO_PA_TRIGGER")
        _signal(conn, 2, 4, "EURUSDc", T0 + 5 * H, "SCORE_TOO_LOW")  # di luar periode
        _signal(conn, 9, 5, "EURUSDc", T0 + 900, "SCORE_TOO_LOW")  # sesi TESTER

    _add(db, fill)
    with sqlite3.connect(db) as conn:
        c = lr.candidate_counts(conn, _scope(db, frm=T0, to=T0 + 4 * H))
    assert c.total == {"ACCEPTED": 1, "NO_PA_TRIGGER": 2}
    assert c.per_symbol["GBPUSDc"] == {"NO_PA_TRIGGER": 1}


def test_ts125_alerts(db: Path) -> None:
    def fill(conn):
        _alert(conn, 2, T0 + 60, "HEARTBEAT", "INFO", "SENT")
        _alert(conn, 2, T0 + 120, "ORDER_FAILED", "HIGH", "FAILED", "x" * 120)
        _alert(conn, 3, T0 + 3 * H, "DD_STOP", "CRITICAL", "SENT")
        _alert(conn, 9, T0 + 60, "DD_STOP", "CRITICAL", "SENT")  # TESTER

    _add(db, fill)
    with sqlite3.connect(db) as conn:
        a = lr.alert_stats(conn, _scope(db, frm=T0, to=T0 + 4 * H))
    assert a.counts[("HEARTBEAT", "INFO", "SENT")] == 1
    assert a.counts[("DD_STOP", "CRITICAL", "SENT")] == 1
    assert [x[2] for x in a.important] == ["ORDER_FAILED", "DD_STOP"]
    assert len(a.important[0][3]) == lr.MSG_MAX


def test_ts126_session_health(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        h = lr.session_health(conn, _scope(db, frm=T0, to=T0 + 4 * H, version="1.25"))
    assert h.gaps["EURUSDc"] == [(T0 + H, T0 + 2 * H)]
    assert h.gaps["GBPUSDc"] == [(T0 + H, T0 + 4 * H)]
    assert h.inactive_at_end == ["GBPUSDc"]
    assert [s[0] for s in h.sessions] == [2, 3, 4]
    out = lr.render(_scope(db, frm=T0, to=T0 + 4 * H, version="1.25"), lr.TradeStats(), health=h)
    assert "GBPUSDc" in out and "tanpa sesi aktif" in out
