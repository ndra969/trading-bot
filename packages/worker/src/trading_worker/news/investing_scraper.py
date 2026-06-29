"""Investing.com economic-calendar scraper (primary ``NewsSource``).

Two surfaces exist on investing.com; we use the more useful + more stable one:

* The public page renders only the CURRENT day, inside a Next.js
  ``__NEXT_DATA__`` JSON blob whose presentation classes are hashed per build.
* The XHR filter endpoint ``/economic-calendar/Service/getCalendarFilteredData``
  returns a date RANGE for ALL countries as classic, long-stable HTML rows
  (``tr.js-event-item`` with ``data-event-datetime``, ``td.flagCur`` /
  ``td.sentiment`` / ``td.event`` / ``td.act|fore|prev``). These selectors have
  been stable for ~a decade (the investpy era); the React redesign only touched
  the homepage table, not this fragment.

We therefore parse the filter-endpoint rows and pull the upcoming week
day-by-day (each request stays well under the endpoint's ~200-row cap, so no
pagination is needed). With ``timeZone=0`` the ``data-event-datetime`` is GMT,
which we treat as UTC. Schema verified live 2026-06-27 (see
scripts/fetch_investing_calendar.py).

A bare client is 403'd; the realistic browser headers below are required to
receive the standard public response (not evasion — just the documented request
shape).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag
from trading_core.utils.logger import get_logger

from .models import NewsEvent, NewsImpact
from .source import NewsParseError, NewsSource

logger = get_logger(__name__)

_FILTER_URL = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"
_DATETIME_ATTR = "data-event-datetime"
_DATETIME_FMT = "%Y/%m/%d %H:%M:%S"
_ROW_ID_PREFIX = "eventRowId_"
_DEFAULT_DAYS = 7
_REQUEST_SPACING_S = 1.5  # polite delay between per-day requests (anti-429)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.investing.com/economic-calendar/",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}

# Extra headers the XHR endpoint expects (it is an AJAX route, not a document).
_XHR_HEADERS = {
    **_HEADERS,
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
}


def _clean(text: str | None) -> str | None:
    """Normalize a cell value; Investing uses ``\xa0``/empty for "no value"."""
    if text is None:
        return None
    cleaned = text.replace("\xa0", "").strip()
    return cleaned or None


class InvestingScraper(NewsSource):
    """Parse Investing.com's filter-endpoint calendar rows into ``NewsEvent``s."""

    def __init__(self, timeout: float = 20.0, days: int = _DEFAULT_DAYS):
        self.timeout = timeout
        self.days = days

    def parse(self, html: str) -> list[NewsEvent]:
        """Parse a calendar HTML fragment → events. Never raises to the caller.

        Accepts either the bare ``<tr.js-event-item>`` fragment returned by the
        filter endpoint or a full page that contains such rows.
        """
        try:
            return self._parse(html)
        except NewsParseError as e:
            logger.warning(f"News calendar parse failed (Investing schema drift?): {e}")
            return []

    def _parse(self, html: str) -> list[NewsEvent]:
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr", class_="js-event-item")
        if not rows:
            # Distinguish "no events" from "structure changed": an empty/garbage
            # fragment with no recognizable calendar markup is drift.
            if soup.find("tr") is None and _DATETIME_ATTR not in html:
                raise NewsParseError("no js-event-item rows and no calendar markup")
            return []

        events: list[NewsEvent] = []
        skipped = 0
        for row in rows:
            try:
                event = self._parse_row(row)
            except Exception as e:  # one bad row must not lose the rest
                skipped += 1
                logger.debug(f"Skipping unparseable calendar row: {e}")
                continue
            if event is not None:
                events.append(event)

        if skipped:
            logger.warning(f"News calendar: skipped {skipped} unparseable row(s)")
        return events

    def _parse_row(self, row: Tag) -> NewsEvent | None:
        raw_dt = row.get(_DATETIME_ATTR)
        if not raw_dt:
            return None  # "All Day"/holiday rows carry no datetime
        try:
            naive = datetime.strptime(str(raw_dt).strip(), _DATETIME_FMT)
        except ValueError:
            return None
        event_time_utc = naive.replace(tzinfo=UTC)  # timeZone=0 ⇒ GMT ⇒ UTC

        currency = _clean(self._cell_text(row, "flagCur"))
        name = _clean(self._cell_text(row, "event"))
        if not currency or not name:
            return None

        return NewsEvent(
            event_time_utc=event_time_utc,
            currency=currency.upper(),
            impact=self._parse_impact(row),
            name=name,
            forecast=_clean(self._cell_text(row, "fore")),
            previous=_clean(self._cell_text(row, "prev")),
            actual=_clean(self._cell_text(row, "act")),
            source_id=self._parse_source_id(row),
        )

    @staticmethod
    def _cell_text(row: Tag, css_class: str) -> str | None:
        cell = row.find("td", class_=css_class)
        if not isinstance(cell, Tag):
            return None
        # Join across child nodes with a space, then collapse runs of
        # whitespace — Investing splits the period across elements (event name
        # in <a>, "(May)" outside) and pads live text with double spaces.
        return " ".join(cell.get_text(" ", strip=True).split())

    @staticmethod
    def _parse_source_id(row: Tag) -> str | None:
        """Stable per-release key from ``id="eventRowId_<occurrenceId>"``."""
        row_id = str(row.get("id", ""))
        if row_id.startswith(_ROW_ID_PREFIX):
            return row_id[len(_ROW_ID_PREFIX) :] or None
        return None

    @staticmethod
    def _parse_impact(row: Tag) -> NewsImpact:
        """Impact from the sentiment cell.

        Prefer the explicit ``data-img_key`` ("bull1/2/3"); fall back to
        counting filled icons; default LOW if absent (never raise).
        """
        cell = row.find("td", class_="sentiment")
        if not isinstance(cell, Tag):
            return NewsImpact.LOW

        img_key = str(cell.get("data-img_key", ""))
        if img_key.startswith("bull"):
            return NewsImpact.from_importance(img_key[-1])

        filled = len(cell.find_all("i", class_="grayFullBullishIcon"))
        return NewsImpact.from_importance(filled)

    async def fetch(self) -> list[NewsEvent]:
        """Fetch the upcoming ``days`` of calendar events. Errors propagate.

        Pulls day-by-day (each well under the endpoint's row cap) and dedups by
        ``source_id``. The Phase 1 scheduler wraps this in bounded retry/backoff
        (tenacity) and failure alerting; the retry policy lives there, not here.
        """
        start = datetime.now(UTC).date()
        seen: dict[str, NewsEvent] = {}
        ordered: list[NewsEvent] = []

        async with httpx.AsyncClient(timeout=self.timeout, headers=_XHR_HEADERS) as client:
            for offset in range(self.days):
                if offset:
                    # Polite spacing between day requests — "not a hammer" (spec),
                    # and avoids the 429 seen on rapid back-to-back pulls.
                    await asyncio.sleep(_REQUEST_SPACING_S)
                day = start + timedelta(days=offset)
                for event in await self._fetch_day(client, day):
                    key = event.source_id or f"{event.event_time_utc}|{event.name}"
                    if key not in seen:
                        seen[key] = event
                        ordered.append(event)

        ordered.sort(key=lambda e: e.event_time_utc)
        return ordered

    async def _fetch_day(self, client: httpx.AsyncClient, day: date) -> list[NewsEvent]:
        # timeZone=0 → GMT; no country[] filter → all countries.
        payload = {
            "timeZone": "0",
            "timeFilter": "timeRemain",
            "currentTab": "custom",
            "dateFrom": day.isoformat(),
            "dateTo": day.isoformat(),
            "limit_from": "0",
        }
        response = await client.post(_FILTER_URL, data=payload)
        response.raise_for_status()
        body = response.json()
        return self.parse(body.get("data", ""))
