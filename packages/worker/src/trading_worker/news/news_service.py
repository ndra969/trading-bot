"""NewsService — the only thing the strategy talks to (Phase 2).

Maps a trading symbol to its affected calendar currencies and answers three
questions over the persisted calendar:

* ``nearest_event(symbol, now)`` — closest high-impact event either side of now.
* ``in_blackout(symbol, now)``   — are we inside a high/medium-impact window?
* ``confidence_adjustment(symbol, direction, now)`` — bounded multiplier on the
  confluence score.

Pure orchestration over :class:`NewsRepository`; no scraping, no DB DDL. Both
consumers (blackout gate Phase 3, confidence modifier Phase 4) are still gated
off in config — this layer just makes the answers available and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from trading_core.utils.logger import get_logger

from .models import NewsEvent, NewsImpact
from .repository import NewsRepository

logger = get_logger(__name__)

# Fiat currencies that have an economic calendar. A symbol's non-fiat leg
# (XAU, XAG, BTC, ETH, …) has no events, so it drops out and only the fiat
# side drives news (XAUUSD → USD, BTCUSD → USD).
_CALENDAR_CURRENCIES = frozenset(
    {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "CNY", "HKD", "SGD", "MXN", "ZAR"}
)

_DEFAULT_HIGH_WINDOW_MIN = 30
_DEFAULT_MEDIUM_WINDOW_MIN = 10
# How far ahead/behind nearest_event looks (minutes). Coarse — just for context.
_DEFAULT_NEAREST_LOOKAHEAD_MIN = 240
_DEFAULT_PRE_EVENT_DAMPEN = 0.85


@dataclass(frozen=True)
class BlackoutStatus:
    """Result of an ``in_blackout`` check."""

    blocked: bool
    event: NewsEvent | None = None
    minutes_to_event: float | None = None


def symbol_currencies(symbol: str) -> list[str]:
    """Split a symbol into its calendar currencies.

    ``EURUSD → [EUR, USD]``, ``USDJPY → [USD, JPY]``, ``XAUUSD → [USD]``,
    ``BTCUSD → [USD]``. Broker suffixes (``EURUSDc``) are tolerated — only the
    first six letters are considered.
    """
    s = "".join(ch for ch in symbol.upper() if ch.isalnum())
    if len(s) < 6:
        return [s] if s in _CALENDAR_CURRENCIES else []
    legs = [s[:3], s[3:6]]
    return [leg for leg in legs if leg in _CALENDAR_CURRENCIES]


class NewsService:
    """Answer news questions for a symbol over the persisted calendar."""

    def __init__(self, repository: NewsRepository, news_config: dict[str, Any] | None = None):
        self.repository = repository
        cfg = news_config or {}
        blackout = cfg.get("blackout") or {}
        confidence = cfg.get("confidence") or {}
        self.high_window_min = int(
            (blackout.get("high") or {}).get("window_min", _DEFAULT_HIGH_WINDOW_MIN)
        )
        self.medium_window_min = int(
            (blackout.get("medium") or {}).get("window_min", _DEFAULT_MEDIUM_WINDOW_MIN)
        )
        self.nearest_lookahead_min = int(
            cfg.get("nearest_lookahead_min", _DEFAULT_NEAREST_LOOKAHEAD_MIN)
        )
        self.pre_event_dampen = float(confidence.get("pre_event_dampen", _DEFAULT_PRE_EVENT_DAMPEN))

    async def nearest_event(self, symbol: str, now: datetime) -> NewsEvent | None:
        """Closest HIGH-impact event within the lookahead window, or None."""
        currencies = symbol_currencies(symbol)
        if not currencies:
            return None
        events = await self.repository.get_in_window(
            currencies, now, self.nearest_lookahead_min, min_impact=NewsImpact.HIGH
        )
        if not events:
            return None
        return min(events, key=lambda e: abs((e.event_time_utc - now).total_seconds()))

    async def in_blackout(self, symbol: str, now: datetime) -> BlackoutStatus:
        """Whether ``now`` is inside a high/medium-impact window for ``symbol``.

        Tier-aware: HIGH events use the (wider) high window, MEDIUM the medium
        window. Returns the triggering event and signed minutes-to-event
        (negative = already released).
        """
        currencies = symbol_currencies(symbol)
        if not currencies:
            return BlackoutStatus(blocked=False)

        widest = max(self.high_window_min, self.medium_window_min)
        candidates = await self.repository.get_in_window(
            currencies, now, widest, min_impact=NewsImpact.MEDIUM
        )

        triggered: BlackoutStatus | None = None
        for event in candidates:
            window = self.high_window_min if event.is_high_impact else self.medium_window_min
            delta_min = (event.event_time_utc - now).total_seconds() / 60.0
            if abs(delta_min) <= window:
                status = BlackoutStatus(blocked=True, event=event, minutes_to_event=delta_min)
                # Prefer the event closest to now if several overlap.
                if triggered is None or abs(delta_min) < abs(triggered.minutes_to_event or 1e9):
                    triggered = status
        return triggered or BlackoutStatus(blocked=False)

    async def confidence_adjustment(self, symbol: str, direction: str, now: datetime) -> float:
        """Bounded multiplier on the confluence score (neutral = 1.0).

        Phase 2 implements the safe, direction-agnostic half: when a HIGH-impact
        event is PENDING within the pre-event window, dampen (elevated
        uncertainty). The post-event surprise boost/dampen — which needs
        reliable per-indicator surprise-direction mapping — is deferred to
        Phase 4 to avoid over-fitting; it returns neutral here.
        """
        currencies = symbol_currencies(symbol)
        if not currencies:
            return 1.0

        events = await self.repository.get_in_window(
            currencies, now, self.high_window_min, min_impact=NewsImpact.HIGH
        )
        for event in events:
            # Pending (not yet printed) high-impact event just ahead → dampen.
            if event.event_time_utc >= now and not event.has_actual:
                return self.pre_event_dampen
        return 1.0
