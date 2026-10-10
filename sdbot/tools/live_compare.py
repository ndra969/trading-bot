"""Replay tester periode live dan perbandingan live vs tester (spec 29, Fase 6).

Subperintah:
    inputs SIMBOL --from --to     cetak Kunci=nilai untuk run-ea-tests.ps1 -SetInput dari inputs_json sesi live
    compare --replay A-B --from --to [--no-news] [--out FILE]
                                  pasangkan kandidat dan trade live dengan replay, nilai ambang tahap 4
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
TYPES_MQH = TOOLS.parent / "ea" / "src" / "Include" / "SDBot" / "Core" / "Types.mqh"
DROP_KEYS = ("InpAllowLiveTrading", "InpRiskPerTradePct", "InpTelegramConfigured")
# Input yang ditambahkan sesudah versi live tertentu, dengan nilai yang meniru perilaku sebelum input itu ada.
# Replay memakai EA hasil build terbaru; tanpa ini kunci yang tidak ada di inputs_json live memakai default baru.
LEGACY_INPUTS = {
    "InpAllowTestedZones": "true",  # 1.25 (spec 23); sebelumnya zona Tested boleh
    "InpSessionEndHourUtc": "22",  # 1.26 (spec 25); 22 = tanpa pemotongan
    "InpBiasMode": "0",  # 1.27 (spec 27); SDB_BIAS_AND_EMA
    "InpBiasEmaPeriod": "0",  # 1.27/1.28 (spec 27); 0 = ikut InpEmaPeriod (EMA 50)
}
ENUM_RE = re.compile(r"\b(SDB_[A-Z0-9_]+)\s*=\s*(-?\d+)")


class ReplayInputError(Exception):
    """Input sesi live tidak bisa dipakai untuk satu replay (tidak ada sesi, atau berubah di tengah periode)."""


def enum_values(types_path: Path) -> dict[str, int]:
    return {name: int(v) for name, v in ENUM_RE.findall(types_path.read_text(encoding="utf-8"))}


def _ts(t: int | None) -> str:
    return "-" if t is None else datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%d %H:%M")


def _value(v: object, enums: dict[str, int]) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return str(enums[v]) if v in enums else v
    return str(v)


def replay_inputs(
    conn: sqlite3.Connection,
    symbol: str,
    start: int,
    end: int,
    enums: dict[str, int],
    version: str | None = None,
) -> list[str]:
    sql = (
        "SELECT input_hash, inputs_json, started_at FROM sessions WHERE mode = 'LIVE' AND symbol = ? "
        "AND started_at < ? AND (ended_at IS NULL OR ended_at > ?)"
    )
    params: list[object] = [symbol, end, start]
    if version:
        sql += " AND ea_version = ?"
        params.append(version)
    rows = conn.execute(sql + " ORDER BY started_at", params).fetchall()
    if not rows:
        raise ReplayInputError(f"{symbol}: tidak ada sesi LIVE di {_ts(start)} .. {_ts(end)}")
    first: dict[str, int] = {}
    for h, _js, st in rows:
        first.setdefault(h, st)
    if len(first) > 1:
        parts = ", ".join(f"hash {h[:8]} mulai {_ts(t)}" for h, t in first.items())
        raise ReplayInputError(
            f"{symbol}: input berubah di tengah periode ({parts}); pecah periodenya"
        )
    data = json.loads(rows[0][1])
    values = {k: _value(v, enums) for k, v in data.items() if k not in DROP_KEYS}
    for k, v in LEGACY_INPUTS.items():
        values.setdefault(k, v)
    return [f"{k}={v}" for k, v in sorted(values.items())]


KNOWN_DIFF = ("SPREAD_TOO_WIDE", "NEWS_BLACKOUT")
TRADE_PAIR_SEC = 900
MIN_TRADE_PAIRS = 10
THRESHOLDS = {
    "kandidat live cocok": (0.95, ">="),
    "kandidat replay cocok": (0.95, ">="),
    "trade live berpasangan": (0.90, ">="),
    "alasan tutup sama": (0.90, ">="),
    "selisih R rata-rata": (0.10, "<="),
}


@dataclass(frozen=True)
class Cand:
    symbol: str
    time: int
    direction: str
    stage: str
    score: float


@dataclass(frozen=True)
class Trade:
    symbol: str
    direction: str
    opened_at: int
    reason: str | None
    r: float | None
    price_open: float
    sl_initial: float


@dataclass
class CandidatePairs:
    n_live: int = 0
    n_replay: int = 0
    same: int = 0
    diff_known: list[tuple[Cand, Cand]] = field(default_factory=list)
    diff_unknown: list[tuple[Cand, Cand]] = field(default_factory=list)
    only_live: list[Cand] = field(default_factory=list)
    only_replay: list[Cand] = field(default_factory=list)

    def _ratio(self, n: int) -> float | None:
        base = n - len(self.diff_known)
        return self.same / base if base > 0 else None

    @property
    def match_live(self) -> float | None:
        return self._ratio(self.n_live)

    @property
    def match_replay(self) -> float | None:
        return self._ratio(self.n_replay)


@dataclass
class TradePairs:
    n_live: int = 0
    excluded: int = 0
    pairs: list[tuple[Trade, Trade]] = field(default_factory=list)
    only_live: list[Trade] = field(default_factory=list)
    only_replay: list[Trade] = field(default_factory=list)
    reason_same: float | None = None
    r_diff_avg: float | None = None
    r_diff_max: float | None = None
    open_diff_r_avg: float | None = None


def _in_windows(t: int, iv: list[tuple[int, int]]) -> bool:
    return any(lo <= t < hi for lo, hi in iv)


def pair_candidates(
    live: list[Cand],
    replay: list[Cand],
    windows: dict[str, list[tuple[int, int]]],
    no_news: bool = False,
) -> CandidatePairs:
    def key(c: Cand) -> tuple[str, int, str]:
        return (c.symbol, c.time, c.direction)

    lmap = {key(c): c for c in live if _in_windows(c.time, windows.get(c.symbol, []))}
    rmap = {key(c): c for c in replay if _in_windows(c.time, windows.get(c.symbol, []))}
    if no_news:  # CSV kalender tidak mencakup periode: tahap berita tidak dinilai di kedua sisi
        drop = {k for k, c in (*lmap.items(), *rmap.items()) if c.stage == "NEWS_BLACKOUT"}
        lmap = {k: c for k, c in lmap.items() if k not in drop}
        rmap = {k: c for k, c in rmap.items() if k not in drop}
    p = CandidatePairs(n_live=len(lmap), n_replay=len(rmap))
    for k in sorted(lmap):
        lc_, rc = lmap[k], rmap.get(k)
        if rc is None:
            p.only_live.append(lc_)
        elif lc_.stage == rc.stage:
            p.same += 1
        elif lc_.stage in KNOWN_DIFF or rc.stage in KNOWN_DIFF:
            p.diff_known.append((lc_, rc))
        else:
            p.diff_unknown.append((lc_, rc))
    p.only_replay = [rmap[k] for k in sorted(rmap) if k not in lmap]
    return p


def _risk(t: Trade) -> float:
    return abs(t.price_open - t.sl_initial)


def pair_trades(live: list[Trade], replay: list[Trade], start: int) -> TradePairs:
    p = TradePairs()
    eligible = [t for t in live if t.opened_at >= start]
    p.excluded = len(live) - len(eligible)
    p.n_live = len(eligible)
    free = sorted(replay, key=lambda t: t.opened_at)
    for lt in sorted(eligible, key=lambda t: t.opened_at):
        cands = [
            rt
            for rt in free
            if rt.symbol == lt.symbol
            and rt.direction == lt.direction
            and abs(rt.opened_at - lt.opened_at) <= TRADE_PAIR_SEC
        ]
        if not cands:
            p.only_live.append(lt)
            continue
        best = min(cands, key=lambda rt: abs(rt.opened_at - lt.opened_at))
        free.remove(best)
        p.pairs.append((lt, best))
    p.only_replay = free
    if p.pairs:
        p.reason_same = sum(a.reason == b.reason for a, b in p.pairs) / len(p.pairs)
        diffs = [abs(a.r - b.r) for a, b in p.pairs if a.r is not None and b.r is not None]
        if diffs:
            p.r_diff_avg = sum(diffs) / len(diffs)
            p.r_diff_max = max(diffs)
        opens = [abs(a.price_open - b.price_open) / _risk(a) for a, b in p.pairs if _risk(a) > 0]
        if opens:
            p.open_diff_r_avg = sum(opens) / len(opens)
    return p


def assess(cands: CandidatePairs, trades: TradePairs) -> list[tuple[str, float | None, float, str]]:
    few = len(trades.pairs) < MIN_TRADE_PAIRS
    values = {
        "kandidat live cocok": (cands.match_live, cands.match_live is None),
        "kandidat replay cocok": (cands.match_replay, cands.match_replay is None),
        "trade live berpasangan": (
            len(trades.pairs) / trades.n_live if trades.n_live else None,
            few,
        ),
        "alasan tutup sama": (trades.reason_same, few),
        "selisih R rata-rata": (trades.r_diff_avg, few),
    }
    out = []
    for name, (thr, op) in THRESHOLDS.items():
        value, short = values[name]
        if short or value is None:
            status = "SAMPEL KURANG"
        else:
            ok = value >= thr if op == ">=" else value <= thr
            status = "LOLOS" if ok else "TIDAK"
        out.append((name, value, thr, status))
    return out


def extra_inputs(live_json: dict, replay_json: dict) -> dict:
    return {k: v for k, v in sorted(replay_json.items()) if k not in live_json}


def _parse_date(text: str) -> int:
    return int(datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=UTC).timestamp())


def _open_ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _default_live_db() -> Path:
    import live_report

    return live_report.default_db()


def _cmd_inputs(args: argparse.Namespace) -> int:
    db = args.db or _default_live_db()
    if not db.is_file():
        print(f"[live_compare] DB tidak ditemukan: {db}")
        return 1
    conn = _open_ro(db)
    try:
        items = replay_inputs(
            conn, args.symbol, args.frm, args.to, enum_values(args.types), args.version
        )
    except ReplayInputError as exc:
        print(f"[live_compare] {exc}")
        return 3
    finally:
        conn.close()
    print("\n".join(items))
    return 0


def live_windows(
    conn: sqlite3.Connection, session_ids: list[int], start: int, end: int
) -> dict[str, list]:
    """Interval sesi live aktif per simbol, dipotong ke periode."""
    out: dict[str, list[tuple[int, int]]] = {}
    if not session_ids:
        return out
    ids = ",".join(str(int(i)) for i in session_ids)
    for symbol, st, en in conn.execute(
        f"SELECT symbol, started_at, ended_at FROM sessions WHERE id IN ({ids})"
    ):
        lo, hi = max(st, start), min(en if en is not None else end, end)
        if lo < hi:
            out.setdefault(symbol, []).append((lo, hi))
    return out


def _load_cands(conn: sqlite3.Connection, where: str, params: tuple) -> list[Cand]:
    return [
        Cand(s, int(t), d, st, float(sc or 0))
        for s, t, d, st, sc in conn.execute(
            "SELECT symbol, time, direction, COALESCE(reject_stage, status), score_total FROM signals "
            + where,
            params,
        )
    ]


def _load_trades(conn: sqlite3.Connection, where: str, params: tuple) -> list[Trade]:
    return [
        Trade(s, d, int(o), rs, r, float(po), float(sl or 0))
        for s, d, o, rs, r, po, sl in conn.execute(
            "SELECT t.symbol, t.direction, t.opened_at, c.reason, c.r_result, t.price_open, t.sl_initial FROM trades t "
            "LEFT JOIN closures c ON c.login = t.login AND c.run_key = t.run_key AND c.position_id = t.position_id "
            "WHERE t.source = 'EA' AND " + where,
            params,
        )
    ]


def _pct(v: float | None) -> str:
    return "-" if v is None else f"{100 * v:.1f}%"


def _cand_text(c: Cand) -> str:
    return f"{c.symbol} {_ts(c.time)} {c.direction} {c.stage} skor={c.score:g}"


def render(
    cands: CandidatePairs,
    trades: TradePairs,
    verdict: list,
    extras: dict,
    versions: tuple[set, set],
) -> str:
    lines = []
    live_v, rep_v = versions
    if live_v != rep_v:
        lines.append(f"PERINGATAN versi: live {sorted(live_v)} vs replay {sorted(rep_v)}")
        for k, v in extras.items():
            how = (
                "diisi nilai lama (meniru versi live)"
                if k in LEGACY_INPUTS
                else "DEFAULT VERSI REPLAY, cek"
            )
            lines.append(f"  input hanya di replay, {how}: {k}={v}")
    lines.append(
        f"== Kandidat: live {cands.n_live}, replay {cands.n_replay}, tahap sama {cands.same}"
    )
    lines.append(f"cocok live {_pct(cands.match_live)}, cocok replay {_pct(cands.match_replay)}")
    lines.append(
        f"beda dikenal (spread/berita): {len(cands.diff_known)}; beda tidak dikenal: {len(cands.diff_unknown)}"
    )
    lines += [
        f"  BEDA live: {_cand_text(a)} | replay: {b.stage} skor={b.score:g}"
        for a, b in cands.diff_unknown
    ]
    lines += [f"  HANYA LIVE: {_cand_text(c)}" for c in cands.only_live]
    lines += [f"  HANYA REPLAY: {_cand_text(c)}" for c in cands.only_replay]
    lines.append(
        f"== Trade: live {trades.n_live} (dikecualikan {trades.excluded}), berpasangan {len(trades.pairs)}, "
        f"hanya live {len(trades.only_live)}, hanya replay {len(trades.only_replay)}"
    )
    r_avg = "-" if trades.r_diff_avg is None else f"{trades.r_diff_avg:.3f}"
    r_max = "-" if trades.r_diff_max is None else f"{trades.r_diff_max:.3f}"
    o_avg = "-" if trades.open_diff_r_avg is None else f"{trades.open_diff_r_avg:.3f}"
    lines.append(
        f"alasan tutup sama {_pct(trades.reason_same)}; selisih R rata-rata {r_avg}, maks {r_max}; "
        f"selisih harga buka {o_avg} R"
    )
    lines.append("== Ambang tahap 4")
    for name, value, thr, status in verdict:
        shown = (
            "-"
            if value is None
            else (f"{value:.3f}" if name.startswith("selisih") else _pct(value))
        )
        lines.append(f"  {name:<24} {shown:>8}  ambang {thr:g}  {status}")
    return "\n".join(lines)


def _cmd_compare(args: argparse.Namespace) -> int:
    import live_report

    live_db = args.db or live_report.default_db()
    tester_db = args.tester or live_db.with_name("sdbot_tester.sqlite")
    for db in (live_db, tester_db):
        if not db.is_file():
            print(f"[live_compare] DB tidak ditemukan: {db}")
            return 1
    lo, hi = args.replay
    lconn, tconn = _open_ro(live_db), _open_ro(tester_db)
    try:
        scope = live_report.resolve_scope(lconn, args.frm, args.to, args.version)
        ids = ",".join(str(i) for i in scope.session_ids) or "NULL"
        windows = live_windows(lconn, scope.session_ids, args.frm, args.to)
        period = (args.frm, args.to)
        live_c = _load_cands(
            lconn, f"WHERE session_id IN ({ids}) AND time >= ? AND time < ?", period
        )
        rep_c = _load_cands(
            tconn, "WHERE session_id BETWEEN ? AND ? AND time >= ? AND time < ?", (lo, hi, *period)
        )
        live_t = _load_trades(lconn, f"t.session_id IN ({ids}) AND t.opened_at < ?", (args.to,))
        rep_t = _load_trades(
            tconn,
            "t.session_id BETWEEN ? AND ? AND t.opened_at >= ? AND t.opened_at < ?",
            (lo, hi, *period),
        )
        cands = pair_candidates(live_c, rep_c, windows, args.no_news)
        trades = pair_trades(live_t, rep_t, args.frm)
        lv = {
            r[0]
            for r in lconn.execute(f"SELECT DISTINCT ea_version FROM sessions WHERE id IN ({ids})")
        }
        rv = {
            r[0]
            for r in tconn.execute(
                "SELECT DISTINCT ea_version FROM sessions WHERE id BETWEEN ? AND ?", (lo, hi)
            )
        }
        lj = lconn.execute(
            f"SELECT inputs_json FROM sessions WHERE id IN ({ids}) LIMIT 1"
        ).fetchone()
        rj = tconn.execute(
            "SELECT inputs_json FROM sessions WHERE id BETWEEN ? AND ? LIMIT 1", (lo, hi)
        ).fetchone()
        extras = extra_inputs(json.loads(lj[0]), json.loads(rj[0])) if lj and rj else {}
    except sqlite3.DatabaseError as exc:
        print(f"[live_compare] DB tidak bisa dibaca: {exc}")
        return 1
    finally:
        lconn.close()
        tconn.close()
    text = render(cands, trades, assess(cands, trades), extras, (lv, rv))
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


def _parse_range(text: str) -> tuple[int, int]:
    lo, dash, hi = text.partition("-")
    if not dash or not lo.isdigit() or not hi.isdigit() or int(lo) > int(hi):
        raise ValueError(f"--replay harus A-B dengan A <= B: {text!r}")
    return int(lo), int(hi)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_in = sub.add_parser("inputs", help="Kunci=nilai untuk -SetInput dari sesi live")
    p_in.add_argument("symbol")
    p_in.add_argument("--types", type=Path, default=TYPES_MQH)
    p_cmp = sub.add_parser("compare", help="bandingkan kandidat dan trade live dengan replay")
    p_cmp.add_argument("--tester", type=Path, help="default: sdbot_tester.sqlite di folder DB live")
    p_cmp.add_argument("--replay", required=True, help="rentang id sesi replay di DB tester, A-B")
    p_cmp.add_argument("--no-news", action="store_true", help="CSV kalender tidak mencakup periode")
    p_cmp.add_argument("--out", type=Path)
    for p in (p_in, p_cmp):
        p.add_argument("--db", type=Path, help="DB live (default: Common\\Files\\sdbot.sqlite)")
        p.add_argument("--version", help="hanya sesi live dengan ea_version ini")
        p.add_argument("--from", dest="frm_text", required=True)
        p.add_argument("--to", dest="to_text", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        args.frm = _parse_date(args.frm_text)
        args.to = _parse_date(args.to_text)
        if args.cmd == "compare":
            args.replay = _parse_range(args.replay)
    except ValueError as exc:
        print(f"[live_compare] argumen salah: {exc}")
        return 2
    if args.frm >= args.to:
        print("[live_compare] --from harus sebelum --to")
        return 2
    return _cmd_inputs(args) if args.cmd == "inputs" else _cmd_compare(args)


if __name__ == "__main__":
    sys.exit(main())
