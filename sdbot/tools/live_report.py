"""Laporan DB live SDBot per periode (spec 28, Fase 6).

Membaca `sdbot.sqlite` live secara read-only: hasil trade dalam R, eksekusi (slippage, spread), kandidat per
tahap, alert, dan kesehatan sesi. Trade masuk periode menurut waktu tutup.

Contoh:
    python live_report.py --from 2026-10-09 --version 1.25 [--to 2026-10-16] [--out laporan.txt]
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

REASONS = ("SL", "BE_STOP", "TRAIL_STOP", "TP")  # sama dengan exit_report.py
GAP_MIN_SEC = 1800
MSG_MAX = 80


@dataclass
class Scope:
    start: int
    end: int
    session_ids: list[int]


@dataclass
class Result:
    n: int = 0
    wins: int = 0
    total_r: float = 0.0
    r_pos: float = 0.0
    r_neg: float = 0.0
    money_win: float = 0.0
    money_loss: float = 0.0
    dd_r: float = 0.0

    @property
    def r_per_trade(self) -> float | None:
        return self.total_r / self.n if self.n else None

    @property
    def win_pct(self) -> float | None:
        return 100.0 * self.wins / self.n if self.n else None

    @property
    def pf_r(self) -> float | None:
        return self.r_pos / self.r_neg if self.n and self.r_neg > 0 else None

    @property
    def pf_money(self) -> float | None:
        return self.money_win / self.money_loss if self.n and self.money_loss > 0 else None


@dataclass
class TradeStats:
    total: Result = field(default_factory=Result)
    per_symbol: dict[str, Result] = field(default_factory=dict)
    reasons: dict[str, tuple[int, float]] = field(default_factory=dict)
    open_positions: dict[str, int] = field(default_factory=dict)


@dataclass
class ExecSymbol:
    n: int = 0
    slip_pts_sum: float = 0.0
    slip_pts_max: int = 0
    slip_r: list[float] = field(default_factory=list)
    spread_sum: float = 0.0

    @property
    def slip_pts_avg(self) -> float | None:
        return self.slip_pts_sum / self.n if self.n else None

    @property
    def slip_r_avg(self) -> float | None:
        return sum(self.slip_r) / len(self.slip_r) if self.slip_r else None

    @property
    def spread_avg(self) -> float | None:
        return self.spread_sum / self.n if self.n else None


@dataclass
class ExecStats:
    total: ExecSymbol = field(default_factory=ExecSymbol)
    per_symbol: dict[str, ExecSymbol] = field(default_factory=dict)
    close_slip: dict[str, float] = field(default_factory=dict)


@dataclass
class Candidates:
    total: dict[str, int] = field(default_factory=dict)
    per_symbol: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass
class AlertStats:
    counts: dict[tuple[str, str, str], int] = field(default_factory=dict)
    important: list[tuple[int, str, str, str, str]] = field(
        default_factory=list
    )  # waktu, simbol, tipe, pesan, sev


@dataclass
class SessionHealth:
    sessions: list[tuple] = field(
        default_factory=list
    )  # id, simbol, magic, versi, mulai, akhir, alasan
    gaps: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    inactive_at_end: list[str] = field(default_factory=list)


def default_db() -> Path:
    return (
        Path(os.environ.get("APPDATA", ""))
        / "MetaQuotes"
        / "Terminal"
        / "Common"
        / "Files"
        / "sdbot.sqlite"
    )


def _in(ids: list[int]) -> str:
    return "(" + ",".join(str(int(i)) for i in ids) + ")" if ids else "(NULL)"


def resolve_scope(
    conn: sqlite3.Connection, frm: int | None, to: int | None, version: str | None
) -> Scope:
    sql = "SELECT id, started_at FROM sessions WHERE mode = 'LIVE'"
    params: list[object] = []
    if version:
        sql += " AND ea_version = ?"
        params.append(version)
    rows = conn.execute(sql + " ORDER BY id", params).fetchall()
    end = to if to is not None else int(time.time())
    first = min((r[1] for r in rows), default=end)
    start = frm if frm is not None else first
    ids = [r[0] for r in rows if r[1] < end]
    return Scope(start, end, ids)


def _add_result(res: Result, r: float, net: float) -> None:
    res.n += 1
    res.total_r += r
    if r > 0:
        res.wins += 1
        res.r_pos += r
    elif r < 0:
        res.r_neg -= r
    if net > 0:
        res.money_win += net
    elif net < 0:
        res.money_loss -= net


def _drawdown(rs: list[float]) -> float:
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return dd


def trade_stats(conn: sqlite3.Connection, scope: Scope) -> TradeStats:
    st = TradeStats()
    rows = conn.execute(
        "SELECT t.symbol, c.reason, c.r_result, c.net_profit FROM closures c JOIN trades t ON t.login = c.login "
        "AND t.run_key = c.run_key AND t.position_id = c.position_id "
        f"WHERE t.source = 'EA' AND c.r_result IS NOT NULL AND t.session_id IN {_in(scope.session_ids)} "
        "AND c.closed_at >= ? AND c.closed_at < ? ORDER BY c.closed_at, c.id",
        (scope.start, scope.end),
    ).fetchall()
    sums: dict[str, list[float]] = {}
    seq: dict[str, list[float]] = {}
    for symbol, reason, r, net in rows:
        r, net = float(r), float(net)
        _add_result(st.total, r, net)
        _add_result(st.per_symbol.setdefault(symbol, Result()), r, net)
        seq.setdefault(symbol, []).append(r)
        key = reason if reason in REASONS else "LAIN"
        acc = sums.setdefault(key, [0, 0.0])
        acc[0] += 1
        acc[1] += r
    st.total.dd_r = _drawdown([float(r[2]) for r in rows])
    for symbol, rs in seq.items():
        st.per_symbol[symbol].dd_r = _drawdown(rs)
    st.reasons = {k: (int(n), total / n) for k, (n, total) in sums.items()}
    for symbol, n in conn.execute(
        "SELECT t.symbol, COUNT(*) FROM trades t WHERE t.source = 'EA' "
        f"AND t.session_id IN {_in(scope.session_ids)} AND t.opened_at < ? AND NOT EXISTS "
        "(SELECT 1 FROM closures c WHERE c.login = t.login AND c.run_key = t.run_key AND c.position_id = t.position_id "
        "AND c.closed_at < ?) GROUP BY t.symbol",
        (scope.end, scope.end),
    ):
        st.open_positions[symbol] = int(n)
    return st


def _num(v: float | None, fmt: str) -> str:
    return "-" if v is None else format(v, fmt)


def _ts(t: int | None) -> str:
    return "-" if t is None else datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%d %H:%M")


def _result_line(name: str, res: Result) -> str:
    return (
        f"{name:<10} {res.n:>6} {_num(res.win_pct, '.1f'):>6} {res.total_r:>+8.2f} {_num(res.r_per_trade, '+.3f'):>8} "
        f"{_num(res.pf_money, '.2f'):>7} {_num(res.pf_r, '.2f'):>6} {res.dd_r:>6.2f}"
    )


def _add_exec(e: ExecSymbol, slip_pts: int, slip_r: float | None, spread: int) -> None:
    e.n += 1
    e.slip_pts_sum += slip_pts
    e.slip_pts_max = max(e.slip_pts_max, slip_pts)
    if slip_r is not None:
        e.slip_r.append(slip_r)
    e.spread_sum += spread


def exec_stats(conn: sqlite3.Connection, scope: Scope) -> ExecStats:
    ex = ExecStats()
    for symbol, req, price, sl, slip, spread in conn.execute(
        "SELECT symbol, price_requested, price_open, sl_initial, slippage_points, spread_points FROM trades "
        f"WHERE source = 'EA' AND session_id IN {_in(scope.session_ids)} AND opened_at >= ? AND opened_at < ?",
        (scope.start, scope.end),
    ):
        risk = abs(price - sl) if price and sl else 0.0
        slip_r = abs(price - req) / risk if req and risk > 0 else None
        slip_pts = int(slip or 0)
        _add_exec(ex.total, slip_pts, slip_r, int(spread or 0))
        _add_exec(
            ex.per_symbol.setdefault(symbol, ExecSymbol()), slip_pts, slip_r, int(spread or 0)
        )
    for reason, avg in conn.execute(
        "SELECT c.reason, AVG(c.slippage_points) FROM closures c JOIN trades t ON t.login = c.login "
        "AND t.run_key = c.run_key AND t.position_id = c.position_id "
        f"WHERE t.source = 'EA' AND t.session_id IN {_in(scope.session_ids)} "
        "AND c.closed_at >= ? AND c.closed_at < ? AND c.slippage_points IS NOT NULL GROUP BY c.reason",
        (scope.start, scope.end),
    ):
        ex.close_slip[reason] = float(avg)
    return ex


def candidate_counts(conn: sqlite3.Connection, scope: Scope) -> Candidates:
    c = Candidates()
    for symbol, stage, n in conn.execute(
        "SELECT symbol, COALESCE(reject_stage, status), COUNT(*) FROM signals "
        f"WHERE session_id IN {_in(scope.session_ids)} AND time >= ? AND time < ? GROUP BY 1, 2",
        (scope.start, scope.end),
    ):
        c.total[stage] = c.total.get(stage, 0) + int(n)
        c.per_symbol.setdefault(symbol, {})[stage] = int(n)
    return c


def alert_stats(conn: sqlite3.Connection, scope: Scope) -> AlertStats:
    a = AlertStats()
    rows = conn.execute(
        "SELECT time, symbol, type, severity, status, message FROM alerts "
        f"WHERE session_id IN {_in(scope.session_ids)} AND time >= ? AND time < ? ORDER BY time, id",
        (scope.start, scope.end),
    ).fetchall()
    for t, symbol, kind, sev, status, msg in rows:
        a.counts[(kind, sev, status)] = a.counts.get((kind, sev, status), 0) + 1
        if sev in ("HIGH", "CRITICAL"):
            a.important.append((int(t), symbol, kind, (msg or "")[:MSG_MAX], sev))
    return a


def session_health(conn: sqlite3.Connection, scope: Scope) -> SessionHealth:
    h = SessionHealth()
    h.sessions = conn.execute(
        "SELECT id, symbol, magic, ea_version, started_at, ended_at, end_reason FROM sessions "
        f"WHERE id IN {_in(scope.session_ids)} ORDER BY id"
    ).fetchall()
    spans: dict[str, list[tuple[int, int]]] = {}
    for _sid, symbol, _magic, _ver, start, end, _reason in h.sessions:
        lo = max(start, scope.start)
        hi = min(end if end is not None else scope.end, scope.end)
        spans.setdefault(symbol, [])
        if lo < hi:
            spans[symbol].append((lo, hi))
    for symbol, iv in spans.items():
        iv.sort()
        gaps: list[tuple[int, int]] = []
        cursor = scope.start
        for lo, hi in iv:
            if lo - cursor > GAP_MIN_SEC:
                gaps.append((cursor, lo))
            cursor = max(cursor, hi)
        if scope.end - cursor > GAP_MIN_SEC:
            gaps.append((cursor, scope.end))
        if gaps:
            h.gaps[symbol] = gaps
        if not iv or max(hi for _lo, hi in iv) < scope.end:
            h.inactive_at_end.append(symbol)
    h.inactive_at_end.sort()
    return h


def _exec_line(name: str, e: ExecSymbol) -> str:
    return (
        f"{name:<10} {e.n:>6} {_num(e.slip_pts_avg, '.1f'):>9} {e.slip_pts_max:>8} "
        f"{_num(e.slip_r_avg, '.3f'):>8} {_num(e.spread_avg, '.1f'):>10}"
    )


def _render_exec(ex: ExecStats) -> list[str]:
    head = f"{'simbol':<10} {'entry':>6} {'slip pt':>9} {'slip max':>8} {'slip R':>8} {'spread pt':>10}"
    out = ["== Eksekusi (entry dalam periode)", head, "-" * len(head)]
    out += [_exec_line(s, ex.per_symbol[s]) for s in sorted(ex.per_symbol)]
    out.append(_exec_line("TOTAL", ex.total))
    closes = "  ".join(f"{k} {v:.1f}" for k, v in sorted(ex.close_slip.items()))
    out.append("slippage tutup (pt rata-rata): " + (closes or "-"))
    return out


def _stage_text(stages: dict[str, int]) -> str:
    return "  ".join(f"{k} {n}" for k, n in sorted(stages.items(), key=lambda x: -x[1]))


def _render_candidates(c: Candidates) -> list[str]:
    out = [f"== Kandidat: {sum(c.total.values())}", _stage_text(c.total) or "-"]
    out += [f"  {s:<10} {_stage_text(c.per_symbol[s])}" for s in sorted(c.per_symbol)]
    return out


def _render_alerts(a: AlertStats) -> list[str]:
    out = [f"== Alert: {sum(a.counts.values())}"]
    for (kind, sev, status), n in sorted(a.counts.items()):
        out.append(f"  {kind:<18} {sev:<8} {status:<8} {n}")
    out.append("HIGH/CRITICAL:" if a.important else "HIGH/CRITICAL: tidak ada")
    out += [f"  {_ts(t)} {sym} {sev} {kind}: {msg}" for t, sym, kind, msg, sev in a.important]
    return out


def _render_health(h: SessionHealth) -> list[str]:
    out = ["== Sesi"]
    for sid, sym, magic, ver, start, end, reason in h.sessions:
        akhir = _ts(end) if end else "aktif"
        out.append(
            f"  #{sid} {sym} magic={magic} v{ver} {_ts(start)} .. {akhir} {reason or ''}".rstrip()
        )
    out.append("celah > 30 menit:" if h.gaps else "celah > 30 menit: tidak ada")
    for symbol in sorted(h.gaps):
        out += [f"  {symbol} {_ts(lo)} .. {_ts(hi)}" for lo, hi in h.gaps[symbol]]
    out.append(
        "tanpa sesi aktif di akhir periode: " + (", ".join(h.inactive_at_end) or "tidak ada")
    )
    return out


def render(
    scope: Scope,
    trades: TradeStats,
    ex: ExecStats | None = None,
    cands: Candidates | None = None,
    alerts: AlertStats | None = None,
    health: SessionHealth | None = None,
) -> str:
    lines = [
        f"== Periode {_ts(scope.start)} .. {_ts(scope.end)} UTC, {len(scope.session_ids)} sesi LIVE"
    ]
    if not scope.session_ids:
        lines.append("tidak ada sesi LIVE untuk pilihan ini")
        return "\n".join(lines)
    lines.append(f"== Hasil: {trades.total.n} trade tutup")
    head = f"{'simbol':<10} {'trade':>6} {'win%':>6} {'R total':>8} {'R/trade':>8} {'PF uang':>7} {'PF R':>6} {'DD R':>6}"
    lines += [head, "-" * len(head)]
    for symbol in sorted(trades.per_symbol):
        lines.append(_result_line(symbol, trades.per_symbol[symbol]))
    lines.append(_result_line("TOTAL", trades.total))
    lines.append("== Alasan tutup (n x R rata-rata)")
    lines.append(
        "  ".join(
            f"{k} {n} x {avg:+.2f}"
            for k in (*REASONS, "LAIN")
            if (n_avg := trades.reasons.get(k))
            for n, avg in [n_avg]
        )
        or "-"
    )
    lines.append("== Posisi terbuka di akhir periode")
    lines.append(
        ", ".join(f"{s} {n}" for s, n in sorted(trades.open_positions.items())) or "tidak ada"
    )
    if ex is not None:
        lines += _render_exec(ex)
    if cands is not None:
        lines += _render_candidates(cands)
    if alerts is not None:
        lines += _render_alerts(alerts)
    if health is not None:
        lines += _render_health(health)
    return "\n".join(lines)


def _parse_date(text: str) -> int:
    return int(datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=UTC).timestamp())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--db", type=Path, default=None, help="default: sdbot.sqlite di Common\\Files MT5"
    )
    ap.add_argument(
        "--from", dest="frm", help="tanggal UTC YYYY-MM-DD (default: sesi LIVE pertama)"
    )
    ap.add_argument("--to", help="tanggal UTC YYYY-MM-DD, eksklusif (default: sekarang)")
    ap.add_argument("--version", help="hanya sesi dengan ea_version ini, misalnya 1.25")
    ap.add_argument("--out", type=Path, help="tulis laporan yang sama ke file")
    args = ap.parse_args(argv)
    try:
        frm = _parse_date(args.frm) if args.frm else None
        to = _parse_date(args.to) if args.to else None
    except ValueError as exc:
        print(f"[live_report] tanggal salah: {exc}")
        return 2
    if frm is not None and to is not None and frm >= to:
        print("[live_report] --from harus sebelum --to")
        return 2
    db = args.db or default_db()
    if not db.is_file():
        print(f"[live_report] DB tidak ditemukan: {db}")
        return 1
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            scope = resolve_scope(conn, frm, to, args.version)
            text = render(
                scope,
                trade_stats(conn, scope),
                exec_stats(conn, scope),
                candidate_counts(conn, scope),
                alert_stats(conn, scope),
                session_health(conn, scope),
            )
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        print(f"[live_report] DB tidak bisa dibaca: {exc}")
        return 1
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
