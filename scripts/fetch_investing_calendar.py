"""Dev tool: hit Investing.com's calendar filter endpoint and inspect it.

Verifies the InvestingScraper assumptions against the live site (the XHR filter
endpoint returns the classic js-event-item rows we parse) and can refresh the
test fixture. Run:

    uv run python scripts/fetch_investing_calendar.py [--save]

--save writes one day's raw row fragment to
tests/fixtures/news/investing_calendar.html (replacing the hand-built fixture
with a real page). Without --save it only prints a structural summary.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# Reuse the parser's endpoint/headers so this diagnostic never drifts from the
# real request shape the scraper makes.
from trading_worker.news.investing_scraper import _FILTER_URL, _XHR_HEADERS

FIXTURE = Path("tests/fixtures/news/investing_calendar.html")


def fetch_day_fragment(day: str) -> str:
    payload = {
        "timeZone": "0",
        "timeFilter": "timeRemain",
        "currentTab": "custom",
        "dateFrom": day,
        "dateTo": day,
        "limit_from": "0",
    }
    resp = httpx.post(
        _FILTER_URL, headers=_XHR_HEADERS, data=payload, timeout=20.0, follow_redirects=True
    )
    resp.raise_for_status()
    print(f"POST {_FILTER_URL} ({day}) -> {resp.status_code}")
    return str(resp.json().get("data", ""))


def summarize(fragment: str) -> None:
    """Validate the live fragment against the parser's row assumptions."""
    print(f"fragment length: {len(fragment):,} bytes")
    soup = BeautifulSoup(fragment, "html.parser")
    rows = soup.find_all("tr", class_="js-event-item")
    print(f"js-event-item rows: {len(rows)}")
    if not rows:
        print("  NO ROWS — selectors may need updating")
        return
    first = rows[0]
    print(f"  sample data-event-datetime: {first.get('data-event-datetime')!r}")
    print(f"  sample id: {first.get('id')!r}")
    print("  cell classes in first row:")
    for td in first.find_all("td"):
        print(
            f"    class={td.get('class')!r} title={td.get('title')!r} "
            f"text={td.get_text(strip=True)[:25]!r}"
        )


def main() -> int:
    day = datetime.now(UTC).date().isoformat()
    try:
        fragment = fetch_day_fragment(day)
    except Exception as e:  # noqa: BLE001 - dev script, surface anything
        print(f"FETCH FAILED: {type(e).__name__}: {e}")
        return 1

    summarize(fragment)

    if "--save" in sys.argv:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(fragment, encoding="utf-8")
        print(f"Saved raw row fragment to {FIXTURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
