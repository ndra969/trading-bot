"""The ``NewsSource`` interface — the only contract consumers depend on.

A source fetches and parses an economic calendar into ``NewsEvent[]``. The
concrete implementation (Investing.com scrape) is swappable; consumers
(NewsService, the scheduler) never import the scraper directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import NewsEvent


class NewsParseError(Exception):
    """Raised internally by a parser when the HTML structure is unrecognizable.

    This is caught at the source boundary and converted to an empty list +
    warning — it must never propagate into the trading loop. It exists so the
    parse layer can distinguish "layout changed" from "no events this week"
    (both yield ``[]`` to callers, but only the former logs a warning).
    """


class NewsSource(ABC):
    """Fetch + parse an economic calendar into normalized ``NewsEvent``s."""

    @abstractmethod
    def parse(self, html: str) -> list[NewsEvent]:
        """Parse raw calendar HTML into events. Pure; no network.

        MUST be total: on unrecognizable/empty markup return ``[]`` (logging a
        warning), never raise. This is what makes the source testable against
        saved HTML fixtures and what guarantees "degrade to no-news-data".
        """

    @abstractmethod
    async def fetch(self) -> list[NewsEvent]:
        """Fetch the live calendar and return parsed events.

        The networked counterpart to :meth:`parse`. Bounded retry/backoff and
        failure alerting live in the Phase 1 scheduler, not here.
        """
