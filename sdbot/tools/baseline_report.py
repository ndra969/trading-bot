"""Laporan backtest dasar Fase 3 (spec 13 Req 8.2, design §3.4).

Membaca sdbot_tester.sqlite untuk sesi TESTER sesudah penanda (id sesi terbesar sebelum backtest dimulai),
mengelompokkan per run (run_key), lalu memeriksa kriteria PC-19:
- total trade >= --min-total dan setiap simbol >= --min-symbol;
- setiap trade EA punya signal_id ke baris signals ACCEPTED;
- setiap kandidat punya 3 komponen skor (ZONE, TREND, PA);
- tidak ada baris log [SDB][ERROR] / [SDB][CRITICAL] (dikumpulkan runner dari jurnal tester).
Profit dicetak tetapi bukan syarat (PC-15).

Spec 17 (Fase 5): run dikelompokkan per periode (`--periods ea/tests/baseline/periods.ini`: IS, OOS, CUSTOM),
dengan profit factor (uang, net_profit) dan drawdown maks (% balance tertutup per run; R untuk total), serta
status kriteria PRD tahap 2-3 sebagai informasi (tidak memengaruhi kode keluar).

Pemakaian:
    python baseline_report.py --db <sdbot_tester.sqlite> --after-session N [--errors file] [--min-total 300] [--min-symbol 15]
    python baseline_report.py --db <sdbot_tester.sqlite> --max-session      (cetak penanda untuk runner)
Kode keluar: 0 lolos, 1 gagal, 2 DB tidak terbaca.
"""

from __future__ import annotations

import argparse
import math
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from periods import CUSTOM, Period, classify, load_periods
from tick_history import journal_problems

ERROR_LINE = re.compile(r"\[SDB\]\[(ERROR|CRITICAL)\]")
COMPONENTS = ("ZONE", "TREND", "PA")
# Kriteria backtest dasar dengan filter Fase 4 (PC-22); Fase 3 tanpa filter memakai 300/15 (PC-19).
DEFAULT_MIN_TOTAL = 200
DEFAULT_MIN_SYMBOL = 10
DEFAULT_DEPOSIT = 10000.0  # deposit tester; tester tidak mencatat operasi saldo awal di balance_ops
PRD_MIN_PF = 1.3  # PRD tahap 2
PRD_MAX_DD_PCT = 15.0  # PRD tahap 2
PRD_MAX_WORSEN_PCT = 30.0  # PRD tahap 3: OOS tidak memburuk > 30% dibanding IS
SHORT_PERIODS = ("OOS", "REAL")  # tanpa kriteria jumlah trade


def profit_factor(gross_win: float, gross_loss: float, trades: int) -> float | None:
    """Uang untung / |uang rugi|; None tanpa trade, inf tanpa trade rugi."""
    if trades == 0:
        return None
    return math.inf if gross_loss == 0 else gross_win / gross_loss


def fmt_pf(pf: float | None) -> str:
    if pf is None:
        return "-"
    return "∞" if math.isinf(pf) else f"{pf:.2f}"


def max_drawdown_pct(deposit: float, pnl_seq: list[float]) -> float | None:
    """Penurunan terbesar balance tertutup dari puncak ke lembah sesudahnya, persen dari puncak."""
    if not pnl_seq:
        return None
    bal = peak = deposit
    worst = 0.0
    for pnl in pnl_seq:
        bal += pnl
        peak = max(peak, bal)
        worst = max(worst, (peak - bal) / peak * 100.0 if peak > 0 else 0.0)
    return worst


def max_drawdown_r(r_seq: list[float]) -> float | None:
    """Penurunan terbesar kurva R kumulatif (mulai 0)."""
    if not r_seq:
        return None
    cum = peak = worst = 0.0
    for r in r_seq:
        cum += r
        peak = max(peak, cum)
        worst = max(worst, peak - cum)
    return worst


@dataclass
class Summary:
    pf: float | None
    dd_pct: float | None  # DD terburuk antar simbol (setiap simbol run sendiri dengan depositnya)


def prd_status(is_: Summary, oos: Summary | None) -> list[str]:
    """Kriteria PRD tahap 2 (IS) dan tahap 3 (OOS vs IS), sebagai teks informasi."""
    out: list[str] = []

    def stage2(name: str, s: Summary) -> None:
        if s.pf is not None:
            ok = s.pf >= PRD_MIN_PF
            out.append(f"PF {name} {fmt_pf(s.pf)} {'>=' if ok else '<'} {PRD_MIN_PF}")
        if s.dd_pct is not None:
            ok = s.dd_pct <= PRD_MAX_DD_PCT
            out.append(f"DD {name} {s.dd_pct:.1f}% {'<=' if ok else '>'} {PRD_MAX_DD_PCT:.0f}%")

    stage2("IS", is_)
    if oos is not None:
        stage2("OOS", oos)
        if is_.pf and oos.pf is not None and not math.isinf(is_.pf) and not math.isinf(oos.pf):
            out.append(
                f"PF OOS vs IS {(oos.pf - is_.pf) / is_.pf * 100:+.0f}% (batas -{PRD_MAX_WORSEN_PCT:.0f}%)"
            )
        if is_.dd_pct and oos.dd_pct is not None:
            out.append(
                f"DD OOS vs IS {(oos.dd_pct - is_.dd_pct) / is_.dd_pct * 100:+.0f}% (batas +{PRD_MAX_WORSEN_PCT:.0f}%)"
            )
    return out


def load_period_file(path: Path | None) -> tuple[list[Period], set[str]]:
    return load_periods(path) if path and path.exists() else ([], set())


@dataclass
class RunRow:
    run_key: int
    symbol: str
    candidates: int = 0
    stages: Counter = field(default_factory=Counter)
    trades: int = 0
    closed: int = 0
    wins: int = 0
    total_r: float = 0.0
    no_signal: int = 0
    bad_scores: int = 0
    period: str = CUSTOM
    gross_win: float = 0.0
    gross_loss: float = 0.0
    deposit: float = DEFAULT_DEPOSIT
    pnl_seq: list[float] = field(default_factory=list)
    r_seq: list[tuple[int, float]] = field(
        default_factory=list
    )  # (closed_at, r) untuk kurva R total

    @property
    def profit_factor(self) -> float | None:
        return profit_factor(self.gross_win, self.gross_loss, self.closed)

    @property
    def max_dd_pct(self) -> float | None:
        return max_drawdown_pct(self.deposit, self.pnl_seq)

    @property
    def expectancy(self) -> float:
        return self.total_r / self.closed if self.closed else 0.0


@dataclass
class Report:
    rows: list[RunRow]
    errors: list[str]
    problems: list[str]

    @property
    def ok(self) -> bool:
        return not self.problems


def max_session(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COALESCE(MAX(id), 0) FROM sessions").fetchone()[0]


def _has_active(conn: sqlite3.Connection) -> bool:
    return any(r[1] == "active" for r in conn.execute("PRAGMA table_info(signal_scores)"))


def _run_rows(
    conn: sqlite3.Connection,
    after_session: int,
    upto_session: int | None = None,
    periods: list[Period] | None = None,
    deposit: float = DEFAULT_DEPOSIT,
) -> list[RunRow]:
    upto = upto_session if upto_session is not None else 2**62
    runs = conn.execute(
        "SELECT run_key, MIN(symbol), MIN(tester_from), MAX(tester_to), MAX(tester_model) FROM sessions "
        "WHERE mode = 'TESTER' AND id > ? AND id <= ? GROUP BY run_key ORDER BY run_key",
        (after_session, upto),
    ).fetchall()
    # Skema v4 (spec 17): hanya komponen yang ikut skor gerbang yang wajib lengkap; DB v3 tidak punya kolom active.
    active = "AND c.active = 1" if _has_active(conn) else ""
    rows = []
    for run_key, symbol, t_from, t_to, t_model in runs:
        row = RunRow(
            run_key, symbol, period=classify(t_from, t_to, t_model, periods or []), deposit=deposit
        )
        ses = "SELECT id FROM sessions WHERE run_key = ? AND mode = 'TESTER'"
        for stage, n in conn.execute(
            f"SELECT COALESCE(reject_stage, 'ACCEPTED'), COUNT(*) FROM signals WHERE session_id IN ({ses}) GROUP BY 1",
            (run_key,),
        ):
            row.stages[stage] = n
            row.candidates += n
        row.trades = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE run_key = ? AND source = 'EA'", (run_key,)
        ).fetchone()[0]
        row.no_signal = conn.execute(
            "SELECT COUNT(*) FROM trades t WHERE t.run_key = ? AND t.source = 'EA' AND NOT EXISTS "
            "(SELECT 1 FROM signals s WHERE s.id = t.signal_id AND s.status = 'ACCEPTED')",
            (run_key,),
        ).fetchone()[0]
        row.bad_scores = conn.execute(
            f"SELECT COUNT(*) FROM signals s WHERE s.session_id IN ({ses}) AND "
            f"(SELECT COUNT(*) FROM signal_scores c WHERE c.signal_id = s.id AND c.component IN ('ZONE','TREND','PA') {active}) <> 3",
            (run_key,),
        ).fetchone()[0]
        closed, wins, total = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(CASE WHEN c.r_result > 0 THEN 1 ELSE 0 END), 0), COALESCE(SUM(c.r_result), 0) "
            "FROM closures c JOIN trades t ON t.login = c.login AND t.run_key = c.run_key AND t.position_id = c.position_id "
            "WHERE t.run_key = ? AND t.source = 'EA' AND c.r_result IS NOT NULL",
            (run_key,),
        ).fetchone()
        row.closed, row.wins, row.total_r = closed, wins, float(total)
        for closed_at, net, r in conn.execute(
            "SELECT c.closed_at, c.net_profit, c.r_result FROM closures c JOIN trades t ON t.login = c.login "
            "AND t.run_key = c.run_key AND t.position_id = c.position_id "
            "WHERE t.run_key = ? AND t.source = 'EA' AND c.r_result IS NOT NULL ORDER BY c.closed_at, c.id",
            (run_key,),
        ):
            row.pnl_seq.append(float(net))
            row.r_seq.append((int(closed_at), float(r)))
            if net > 0:
                row.gross_win += net
            else:
                row.gross_loss -= net
        rows.append(row)
    return rows


def evaluate(
    conn: sqlite3.Connection,
    *,
    after_session: int,
    error_lines: list[str],
    min_total: int,
    min_symbol: int,
    upto_session: int | None = None,
    periods: list[Period] | None = None,
    deposit: float = DEFAULT_DEPOSIT,
) -> Report:
    rows = _run_rows(conn, after_session, upto_session, periods, deposit)
    errors = [line.strip() for line in error_lines if ERROR_LINE.search(line)]
    problems: list[str] = []
    if not rows:
        problems.append("tidak ada run TESTER sesudah penanda")
    # Kriteria jumlah trade (PC-22) dibuat untuk periode panjang; OOS dan REAL hanya beberapa bulan (spec 17).
    counted = [r for r in rows if r.period not in SHORT_PERIODS]
    total = sum(r.trades for r in counted)
    if counted and total < min_total:
        problems.append(f"total trade {total} < {min_total}")
    for r in rows:
        if r in counted and r.trades < min_symbol:
            problems.append(f"{r.symbol} (run {r.run_key}): {r.trades} trade < {min_symbol}")
        if r.no_signal:
            problems.append(
                f"{r.symbol} (run {r.run_key}): {r.no_signal} trade tanpa signal_id ACCEPTED"
            )
        if r.bad_scores:
            problems.append(
                f"{r.symbol} (run {r.run_key}): {r.bad_scores} kandidat dengan skor tidak lengkap"
            )
    if errors:
        problems.append(f"{len(errors)} baris log ERROR/CRITICAL, pertama: {errors[0]}")
    return Report(rows, errors, problems)


PERIOD_ORDER = {"IS": 0, "OOS": 1, "REAL": 2, CUSTOM: 3}


def _summary(rows: list[RunRow]) -> Summary:
    closed = sum(r.closed for r in rows)
    dds = [r.max_dd_pct for r in rows if r.max_dd_pct is not None]
    return Summary(
        profit_factor(sum(r.gross_win for r in rows), sum(r.gross_loss for r in rows), closed),
        max(dds) if dds else None,
    )


def render(
    rep: Report,
    ref: Report | None = None,
    ticks: dict[str, list[str]] | None = None,
    short: set[str] | None = None,
) -> str:
    """Satu tabel per periode; ref = backtest pembanding, dicocokkan per (periode, simbol).

    `ticks`: simbol dengan pesan tester tentang histori/tick bermasalah; `short`: simbol ShortHistory.
    Keduanya ditandai `*` dengan keterangan di bawah tabel.
    """
    ticks = ticks or {}
    short = short or set()
    by_ref = {(r.period, r.symbol): r for r in ref.rows} if ref else {}
    extra = f" {'ref trade':>9} {'ref R/tr':>8} {'ref PF':>6}" if ref else ""
    head = (
        f"{'simbol':<9} {'run':>5} {'kandidat':>8} {'trade':>5} {'win%':>5} {'R total':>8} {'R/trade':>7}"
        f" {'PF':>5} {'DD%':>5}{extra}  tahap tolak teratas"
    )
    lines: list[str] = []
    periods = sorted({r.period for r in rep.rows}, key=lambda p: PERIOD_ORDER.get(p, 9))
    summaries: dict[str, Summary] = {}
    for period in periods:
        rows = [r for r in rep.rows if r.period == period]
        if len(periods) > 1 or period != CUSTOM:
            lines.append(f"== {period} ==")
        lines += [head, "-" * len(head)]
        for r in rows:
            win = 100.0 * r.wins / r.closed if r.closed else 0.0
            top = ", ".join(f"{s} {n}" for s, n in r.stages.most_common(4) if s != "ACCEPTED")
            cmp = ""
            if ref:
                o = by_ref.get((r.period, r.symbol))
                cmp = (
                    f" {o.trades:>9} {o.expectancy:>8.3f} {fmt_pf(o.profit_factor):>6}"
                    if o
                    else f" {'-':>9} {'-':>8} {'-':>6}"
                )
            mark = "*" if r.symbol in ticks or r.symbol in short else ""
            dd = f"{r.max_dd_pct:.1f}" if r.max_dd_pct is not None else "-"
            lines.append(
                f"{r.symbol + mark:<9} {r.run_key:>5} {r.candidates:>8} {r.trades:>5} {win:>5.1f} {r.total_r:>8.2f} "
                f"{r.expectancy:>7.3f} {fmt_pf(r.profit_factor):>5} {dd:>5}{cmp}  {top}"
            )
        closed = sum(r.closed for r in rows)
        total_r = sum(r.total_r for r in rows)
        summ = summaries[period] = _summary(rows)
        dd_r = max_drawdown_r([x for _, x in sorted(sum((r.r_seq for r in rows), []))])
        lines.append(
            f"{'TOTAL':<9} {'':>5} {sum(r.candidates for r in rows):>8} {sum(r.trades for r in rows):>5} "
            f"{'':>5} {total_r:>8.2f} {(total_r / closed if closed else 0.0):>7.3f} {fmt_pf(summ.pf):>5} "
            f"{'':>5}  DD total {'-' if dd_r is None else f'{dd_r:.2f}R'}"
        )
        lines.append("")
    in_report = {r.symbol for r in rep.rows}
    for sym in sorted((set(ticks) | short) & in_report):
        why = (
            ["real ticks pendek, periode real ticks memakai tick buatan (ShortHistory)"]
            if sym in short
            else []
        )
        why += ticks.get(sym, [])[:2]
        lines.append(f"* {sym}: {'; '.join(why)}")
    if "IS" in summaries:
        lines.append(
            "Kriteria PRD (informasi): "
            + "; ".join(prd_status(summaries["IS"], summaries.get("OOS")))
        )
    lines.append("")
    lines.append("LOLOS" if rep.ok else "GAGAL:\n  - " + "\n  - ".join(rep.problems))
    return "\n".join(lines)


def read_ticks(path: Path | None) -> dict[str, list[str]]:
    """Pesan tester bermasalah (tick buatan, tanpa data) per simbol dari baris "<simbol>\\t<pesan>" runner (Req 1.5)."""
    out: dict[str, list[str]] = {}
    if path and path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            sym, _, msg = line.partition("\t")
            if sym and journal_problems([msg]):
                out.setdefault(sym, []).append(msg)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--after-session", type=int, default=0)
    ap.add_argument("--max-session", action="store_true")
    ap.add_argument("--errors", type=Path, help="file baris log ERROR/CRITICAL dari jurnal tester")
    ap.add_argument("--min-total", type=int, default=DEFAULT_MIN_TOTAL)
    ap.add_argument("--min-symbol", type=int, default=DEFAULT_MIN_SYMBOL)
    ap.add_argument("--compare-from", type=int, help="pembanding: sesi > N")
    ap.add_argument(
        "--compare-to", type=int, help="pembanding: sampai sesi <= M (backtest dasar sebelumnya)"
    )
    ap.add_argument("--periods", type=Path, help="periods.ini (IS/OOS, ShortHistory)")
    ap.add_argument(
        "--ticks", type=Path, help="baris pesan tester histori/tick per simbol dari runner"
    )
    ap.add_argument("--deposit", type=float, default=DEFAULT_DEPOSIT)
    args = ap.parse_args(argv)
    periods, short = load_period_file(args.periods)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # konsol Windows cp1252
    try:
        conn = sqlite3.connect(f"file:{args.db.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        print(f"[baseline] DB tidak terbaca: {exc}")
        return 2
    try:
        if args.max_session:
            print(max_session(conn))
            return 0
        # PowerShell menulis UTF-8 dengan BOM; utf-8-sig membuangnya.
        lines = (
            args.errors.read_text(encoding="utf-8-sig").splitlines()
            if args.errors and args.errors.exists()
            else []
        )
        rep = evaluate(
            conn,
            after_session=args.after_session,
            error_lines=lines,
            min_total=args.min_total,
            min_symbol=args.min_symbol,
            periods=periods,
            deposit=args.deposit,
        )
        ref = None
        if args.compare_from is not None and args.compare_to is not None:
            ref = evaluate(
                conn,
                after_session=args.compare_from,
                upto_session=args.compare_to,
                error_lines=[],
                min_total=0,
                min_symbol=0,
                periods=periods,
                deposit=args.deposit,
            )
    finally:
        conn.close()
    print(render(rep, ref, read_ticks(args.ticks), short))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
