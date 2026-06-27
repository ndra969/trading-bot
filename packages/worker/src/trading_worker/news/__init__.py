"""News / economic-calendar integration.

Phase 0: pure, offline source + parser. No DB, no live network in tests.

The package is isolated behind the :class:`NewsSource` interface so the
concrete scraper (Investing.com HTML today) can be swapped without touching
consumers. Everything here is config-gated upstream (``news.enabled: false``)
and must degrade safely: a parse/layout failure yields an empty event list and
a warning, never a raised exception into the trading loop.
"""

from .models import NewsEvent, NewsImpact
from .repository import NewsRepository
from .service import NewsFetchResult, NewsFetchService
from .source import NewsParseError, NewsSource

__all__ = [
    "NewsEvent",
    "NewsImpact",
    "NewsSource",
    "NewsParseError",
    "NewsRepository",
    "NewsFetchService",
    "NewsFetchResult",
]
