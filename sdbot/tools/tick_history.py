"""Kedalaman histori tester per simbol (spec 17 Req 5, design §3.7).

Histori real ticks tester tidak bisa dibaca lewat paket MetaTrader5 (`copy_ticks_range` mengembalikan 0 tick
untuk bulan yang di tester justru ada). Karena itu runner `-ProbeHistory` menjalankan tester per simbol pada
periode 2015 yang pasti kosong; tester lalu menulis "found history data from A to B" ke jurnal. Alat ini
mengurai baris itu, mencetak rentang histori per simbol, dan menandai simbol dengan histori < 12 bulan
untuk `[ShortHistory]` di `ea/tests/baseline/periods.ini`.

Pemakaian:
    uv run python sdbot/tools/tick_history.py --journal <history-probe.txt>   (dipanggil runner)
Baris masukan: "<simbol>\t<pesan jurnal tester>".
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

FOUND = re.compile(
    r"found history data from (\d{4}\.\d{2}\.\d{2}) \d{2}:\d{2} to (\d{4}\.\d{2}\.\d{2}) \d{2}:\d{2}"
)
# Pesan tester yang berarti periode tidak (seluruhnya) punya data; dipakai runner untuk Req 1.5.
PROBLEM = re.compile(r"no history data|out of this range|every tick generation used", re.I)
# contoh: "XAUUSDc : real ticks begin from 2026.08.14 00:00:00, every tick generation used" = tick buatan sebelum tanggal itu


def months_between(first: datetime, now: datetime) -> int:
    """Bulan penuh dari `first` sampai `now`."""
    months = (now.year - first.year) * 12 + now.month - first.month
    return months - 1 if now.day < first.day else months


def short_history(
    first_tick: dict[str, datetime | None], now: datetime, min_months: int = 12
) -> list[str]:
    """Simbol tanpa data atau dengan histori kurang dari `min_months` bulan, urut nama."""
    return sorted(
        s for s, t in first_tick.items() if t is None or months_between(t, now) < min_months
    )


def _day(text: str) -> datetime:
    return datetime.strptime(text, "%Y.%m.%d").replace(tzinfo=UTC)


def parse_probe(lines: list[str]) -> dict[str, tuple[datetime, datetime] | None]:
    """Rentang histori per simbol dari baris "<simbol>\t<pesan>"; None bila tester tidak menemukan data."""
    out: dict[str, tuple[datetime, datetime] | None] = {}
    for line in lines:
        sym, _, msg = line.partition("\t")
        out.setdefault(sym, None)
        m = FOUND.search(msg)
        if m:
            out[sym] = (_day(m.group(1)), _day(m.group(2)))
    return out


def journal_problems(lines: list[str]) -> list[str]:
    """Baris jurnal tester yang menandakan periode tanpa (sebagian) data."""
    return [line for line in lines if PROBLEM.search(line)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--journal", type=Path, required=True)
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ranges = parse_probe(args.journal.read_text(encoding="utf-8-sig").splitlines())
    now = datetime.now(UTC)
    first: dict[str, datetime | None] = {}
    for sym, r in sorted(ranges.items()):
        first[sym] = r[0] if r else None
        span = (
            f"{r[0]:%Y-%m-%d} .. {r[1]:%Y-%m-%d}  {months_between(r[0], now):3d} bulan"
            if r
            else "tidak ada data"
        )
        print(f"{sym:10} {span}")
    print(f"[tick_history] histori < 12 bulan: {', '.join(short_history(first, now)) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
