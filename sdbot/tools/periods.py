"""Periode backtest bernama (spec 17 design §3.3, PC-25).

`ea/tests/baseline/periods.ini` memuat periode in-sample (IS) dan out-of-sample (OOS) beserta simbol yang
histori real ticks-nya pendek. Label periode tidak disimpan di DB: sesi tester dicocokkan lewat
`sessions.tester_from`, `tester_to`, dan `tester_model`.
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

CUSTOM = "CUSTOM"
DAY = 86400
END_SLACK_DAYS = 4  # tick terakhir bisa jatuh sebelum akhir pekan / libur sebelum ToDate


@dataclass(frozen=True)
class Period:
    name: str
    start: int  # epoch UTC 00:00 FromDate
    end: int  # epoch UTC 00:00 ToDate
    model: int


def _date(text: str) -> int:
    return int(datetime.strptime(text.strip(), "%Y.%m.%d").replace(tzinfo=UTC).timestamp())


def load_periods(path: Path) -> tuple[list[Period], set[str]]:
    cp = configparser.ConfigParser(comment_prefixes=(";", "#"), inline_comment_prefixes=(";",))
    cp.optionxform = str  # type: ignore[assignment,method-assign]
    cp.read(path, encoding="utf-8")
    out = [
        Period(name, _date(cp[name]["FromDate"]), _date(cp[name]["ToDate"]), int(cp[name]["Model"]))
        for name in cp.sections()
        if name != "ShortHistory"
    ]
    short: set[str] = set()
    if cp.has_section("ShortHistory"):
        short = {s.strip() for s in cp["ShortHistory"].get("Symbols", "").split(",") if s.strip()}
    return out, short


def classify(
    tester_from: int | None, tester_to: int | None, tester_model: int | None, periods: list[Period]
) -> str:
    """Nama periode yang cocok dengan run tester, atau CUSTOM.

    `tester_from` = 00:00 FromDate. `tester_to` = waktu tick terakhir run (OHLC: akhir hari terakhir; real
    ticks: tick terakhir sebelum akhir pekan), jadi boleh sampai END_SLACK_DAYS hari sebelum ToDate.
    EA tidak bisa membaca model tick sehingga `sessions.tester_model` NULL; model hanya dibandingkan bila ada.
    Runner yang menjamin model periode bernama (`periods.ini`).
    """
    if tester_from is None or tester_to is None:
        return CUSTOM
    for p in periods:
        if tester_from != p.start or not p.end - END_SLACK_DAYS * DAY <= tester_to < p.end + DAY:
            continue
        if tester_model is None or int(tester_model) == p.model:
            return p.name
    return CUSTOM
