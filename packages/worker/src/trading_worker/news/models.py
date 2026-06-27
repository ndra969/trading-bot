"""Domain value objects for the news/economic-calendar feature.

These are pure, framework-free types emitted by a :class:`NewsSource`. The
SQLAlchemy persistence model (Phase 1, ``news_events`` table) maps to/from
``NewsEvent`` so the parser stays decoupled from the DB.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class NewsImpact(str, Enum):
    """Calendar impact tier, normalized from the source's own labels.

    Investing.com renders impact as 1-3 filled "bull" icons; ForexFactory uses
    yellow/orange/red. Both normalize onto this stable enum so consumers and
    config (``news.blackout.{high,medium}``) never depend on the source.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def from_importance(cls, importance: int | str | None) -> NewsImpact:
        """Map Investing's ``importance`` (1/2/3) to an impact tier.

        Investing's ``__NEXT_DATA__`` carries importance as a string ("1".."3";
        sometimes "-1" for holidays). Out-of-range / unparseable values clamp to
        LOW rather than raising — the parser must never crash on schema drift.
        """
        try:
            value = int(importance)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return cls.LOW
        if value >= 3:
            return cls.HIGH
        if value == 2:
            return cls.MEDIUM
        return cls.LOW


@dataclass(frozen=True, slots=True)
class NewsEvent:
    """A single scheduled economic event, normalized to UTC.

    ``actual`` is ``None`` until the release prints (filled by the intraday
    refresh in Phase 1). ``forecast``/``previous``/``actual`` are kept as the
    raw source strings (e.g. ``"3.2%"``, ``"1.5M"``) — numeric surprise parsing
    is a Phase 4 concern and is deliberately not done here.
    """

    event_time_utc: datetime
    currency: str
    impact: NewsImpact
    name: str
    forecast: str | None = None
    previous: str | None = None
    actual: str | None = None
    # Source's stable per-release key (Investing ``occurrenceId``). Drives
    # idempotent upsert in Phase 1; ``None`` for sources that don't expose one.
    source_id: str | None = None

    def __post_init__(self) -> None:
        # UTC-awareness is a hard invariant: a naive datetime is the classic
        # scrape bug (local TZ leaking through). Fail loud here in construction,
        # not silently downstream in the blackout window math.
        if self.event_time_utc.tzinfo is None:
            raise ValueError(
                f"NewsEvent.event_time_utc must be timezone-aware (UTC); "
                f"got naive datetime for {self.currency} {self.name!r}"
            )

    @property
    def is_high_impact(self) -> bool:
        return self.impact is NewsImpact.HIGH

    @property
    def has_actual(self) -> bool:
        """True once the release has printed (drives surprise/boost logic)."""
        return self.actual is not None and self.actual.strip() != ""
