"""Persistence for news events.

Lives in the worker (not ``trading_core.data.repositories``) because it maps
the worker-side domain :class:`NewsEvent` to/from the core ORM
``NewsEventRecord``: worker→core is allowed, core→worker is not, so the mapping
must sit on the worker side.

Times: the domain object is tz-aware UTC; the column is naive UTC (the schema
convention). Conversion happens only here, at the boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from trading_core.data.database import get_session
from trading_core.data.models import NewsEventRecord
from trading_core.utils.logger import get_logger

from .models import NewsEvent, NewsImpact

logger = get_logger(__name__)

# Fields copied on upsert-update (everything the source can refresh; not id /
# source_id / fetched_at).
_REFRESHABLE = ("event_time_utc", "currency", "impact", "name", "forecast", "previous", "actual")


def _to_naive_utc(dt: datetime) -> datetime:
    """Domain tz-aware UTC → naive UTC for storage."""
    return dt.astimezone(UTC).replace(tzinfo=None)


def _record_to_event(record: NewsEventRecord) -> NewsEvent:
    return NewsEvent(
        event_time_utc=record.event_time_utc.replace(tzinfo=UTC),
        currency=record.currency,
        impact=NewsImpact(record.impact),
        name=record.name,
        forecast=record.forecast,
        previous=record.previous,
        actual=record.actual,
        source_id=record.source_id,
    )


def _event_columns(event: NewsEvent) -> dict[str, object]:
    return {
        "event_time_utc": _to_naive_utc(event.event_time_utc),
        "currency": event.currency,
        "impact": event.impact.value,
        "name": event.name,
        "forecast": event.forecast,
        "previous": event.previous,
        "actual": event.actual,
    }


class NewsRepository:
    """Upsert + query economic-calendar events."""

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

    async def upsert_events(self, events: list[NewsEvent]) -> int:
        """Insert new events / update existing ones keyed on ``source_id``.

        Idempotent: re-fetching the same calendar updates rows in place (e.g.
        once ``actual`` prints) rather than duplicating. Events without a
        ``source_id`` are always inserted (can't be deduped). Returns the number
        of rows written (inserted + updated).
        """
        if not events:
            return 0

        written = 0
        async with get_session() as session:
            # Preload existing rows for the incoming source_ids in one query.
            source_ids = [e.source_id for e in events if e.source_id]
            existing: dict[str, NewsEventRecord] = {}
            if source_ids:
                result = await session.execute(
                    select(NewsEventRecord).where(NewsEventRecord.source_id.in_(source_ids))
                )
                existing = {r.source_id: r for r in result.scalars() if r.source_id}

            for event in events:
                columns = _event_columns(event)
                record = existing.get(event.source_id) if event.source_id else None
                if record is not None:
                    for field in _REFRESHABLE:
                        setattr(record, field, columns[field])
                else:
                    session.add(NewsEventRecord(source_id=event.source_id, **columns))
                written += 1

            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Failed to upsert {len(events)} news events: {e}")
                raise

        self.logger.info(f"Upserted {written} news events ({len(existing)} updated)")
        return written

    async def get_in_window(
        self,
        currencies: list[str],
        at: datetime,
        window_min: int,
        min_impact: NewsImpact = NewsImpact.HIGH,
    ) -> list[NewsEvent]:
        """Events for ``currencies`` within ±``window_min`` of ``at``.

        ``min_impact`` filters to that tier and above (HIGH → just high;
        MEDIUM → medium+high). Powers the blackout gate (Phase 3).
        """
        if not currencies:
            return []

        at_utc = _to_naive_utc(at)
        lower = at_utc - timedelta(minutes=window_min)
        upper = at_utc + timedelta(minutes=window_min)
        allowed = _impacts_at_least(min_impact)

        async with get_session() as session:
            stmt = (
                select(NewsEventRecord)
                .where(
                    NewsEventRecord.currency.in_([c.upper() for c in currencies]),
                    NewsEventRecord.impact.in_(allowed),
                    NewsEventRecord.event_time_utc >= lower,
                    NewsEventRecord.event_time_utc <= upper,
                )
                .order_by(NewsEventRecord.event_time_utc)
            )
            result = await session.execute(stmt)
            return [_record_to_event(r) for r in result.scalars().all()]

    async def get_between(
        self, start: datetime, end: datetime, currencies: list[str] | None = None
    ) -> list[NewsEvent]:
        """All events in [start, end], optionally filtered by currency.

        Used by the backtest replay (no impact filter — the replayer decides).
        """
        async with get_session() as session:
            conditions = [
                NewsEventRecord.event_time_utc >= _to_naive_utc(start),
                NewsEventRecord.event_time_utc <= _to_naive_utc(end),
            ]
            if currencies:
                conditions.append(NewsEventRecord.currency.in_([c.upper() for c in currencies]))
            stmt = (
                select(NewsEventRecord).where(*conditions).order_by(NewsEventRecord.event_time_utc)
            )
            result = await session.execute(stmt)
            return [_record_to_event(r) for r in result.scalars().all()]


def _impacts_at_least(min_impact: NewsImpact) -> list[str]:
    order = [NewsImpact.LOW, NewsImpact.MEDIUM, NewsImpact.HIGH]
    return [i.value for i in order[order.index(min_impact) :]]
