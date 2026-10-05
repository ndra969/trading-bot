"""Periode in-sample / out-of-sample dan kedalaman histori tick (spec 17): TS-60, TS-61, TS-70."""

from datetime import UTC, datetime
from pathlib import Path

import periods
import tick_history

INI = """; contoh
[IS]
FromDate=2025.10.01
ToDate=2026.07.01
Model=4
[OOS]
FromDate=2026.07.01
ToDate=2026.10.01
Model=4
[ShortHistory]
Symbols=BTCUSDc, XAGUSDc
"""


def _epoch(y: int, m: int, d: int, hh: int = 0, mm: int = 0, ss: int = 0) -> int:
    return int(datetime(y, m, d, hh, mm, ss, tzinfo=UTC).timestamp())


def _load(tmp_path: Path):
    p = tmp_path / "periods.ini"
    p.write_text(INI, encoding="utf-8")
    return periods.load_periods(p)


def test_ts60_load_periods(tmp_path: Path) -> None:
    ps, short = _load(tmp_path)
    by = {p.name: p for p in ps}
    assert set(by) == {"IS", "OOS"}
    assert by["IS"].start == _epoch(2025, 10, 1) and by["IS"].end == _epoch(2026, 7, 1)
    assert by["OOS"].start == _epoch(2026, 7, 1) and by["OOS"].end == _epoch(2026, 10, 1)
    assert by["IS"].model == 4
    assert short == {"BTCUSDc", "XAGUSDc"}


def test_ts61_classify(tmp_path: Path) -> None:
    ps, _ = _load(tmp_path)
    assert periods.classify(_epoch(2025, 10, 1), _epoch(2026, 7, 1), 4, ps) == "IS"
    # tester mencatat akhir hari terakhir sebelum ToDate
    assert periods.classify(_epoch(2026, 7, 1), _epoch(2026, 9, 30, 23, 59, 59), 4, ps) == "OOS"
    # real ticks: tester_to = tick terakhir, bisa beberapa hari sebelum ToDate (akhir pekan / libur)
    assert periods.classify(_epoch(2026, 7, 1), _epoch(2026, 9, 27, 22, 39, 51), None, ps) == "OOS"
    assert periods.classify(_epoch(2026, 7, 1), _epoch(2026, 9, 20), None, ps) == "CUSTOM"
    assert periods.classify(_epoch(2025, 10, 1), _epoch(2026, 7, 1), 1, ps) == "CUSTOM"
    assert periods.classify(_epoch(2026, 7, 5), _epoch(2026, 10, 5), 4, ps) == "CUSTOM"
    # EA tidak mengisi tester_model (NULL): dicocokkan dari tanggal saja
    assert periods.classify(_epoch(2025, 10, 1), _epoch(2026, 7, 1), None, ps) == "IS"


def test_ts70_short_history() -> None:
    now = datetime(2026, 10, 5, tzinfo=UTC)
    assert tick_history.months_between(datetime(2025, 10, 5, tzinfo=UTC), now) == 12
    assert tick_history.months_between(datetime(2026, 1, 20, tzinfo=UTC), now) == 8
    first = {
        "EURUSDc": datetime(2023, 1, 2, tzinfo=UTC),
        "BTCUSDc": datetime(2026, 2, 1, tzinfo=UTC),
        "XAGUSDc": None,
    }
    assert tick_history.short_history(first, now) == ["BTCUSDc", "XAGUSDc"]


def test_ts70_parse_probe_journal() -> None:
    lines = [
        "EURUSDc	EURUSDc: found history data from 2024.03.26 00:00 to 2026.10.05 00:00, specified period is out of this range",
        "EURUSDc	EURUSDc: no history data from 2015.01.01 00:00 to 2015.01.08 00:00",
        "BTCUSDc	BTCUSDc: found history data from 2025.02.10 00:00 to 2026.10.05 00:00, specified period is out of this range",
        "XAGUSDc	no history data, stop testing",
    ]
    got = tick_history.parse_probe(lines)
    assert got["EURUSDc"] == (
        datetime(2024, 3, 26, tzinfo=UTC),
        datetime(2026, 10, 5, tzinfo=UTC),
    )
    assert got["BTCUSDc"][0] == datetime(2025, 2, 10, tzinfo=UTC)
    assert got["XAGUSDc"] is None
    lines = [
        "EURUSDc: no history data from 2023.06.01 00:00 to 2023.06.15 00:00",
        "EURUSDc : real ticks begin from 2026.01.05 00:00:00",
        "XAUUSDc : real ticks begin from 2026.08.14 00:00:00, every tick generation used",
        "Test passed",
    ]
    assert tick_history.journal_problems(lines) == [lines[0], lines[2]]
