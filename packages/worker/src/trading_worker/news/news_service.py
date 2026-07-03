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
_DEFAULT_SURPRISE_BOOST = 1.15
_DEFAULT_SURPRISE_DAMPEN = 0.80
_MAGNITUDE_SUFFIXES = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def _parse_numeric(raw: str | None) -> float | None:
    """Parse a calendar value string to a float, or None if unparseable.

    Handles ``"200K"`` → 200000, ``"3.2%"`` → 3.2, ``"-2.5M"`` → -2_500_000,
    ``"1.5B"`` → 1.5e9, thousands commas, and empty/``"—"`` → None. Deliberately
    coarse — only the sign of (actual − forecast) is used downstream.
    """
    if raw is None:
        return None
    s = raw.strip().replace(",", "").replace("%", "").replace("$", "")
    if not s:
        return None
    mult = 1.0
    if s[-1].upper() in _MAGNITUDE_SUFFIXES:
        mult = _MAGNITUDE_SUFFIXES[s[-1].upper()]
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


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
        # Gate switches — consumers check these, so the engine needn't see the
        # news config at all (keeps the blackout gate flag-off byte-for-byte).
        self.blackout_enabled = bool(blackout.get("enabled", False))
        self.confidence_enabled = bool(confidence.get("enabled", False))
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
        self.surprise_boost = float(confidence.get("surprise_boost", _DEFAULT_SURPRISE_BOOST))
        self.surprise_dampen = float(confidence.get("surprise_dampen", _DEFAULT_SURPRISE_DAMPEN))

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

        Considers the nearest HIGH-impact event in the window:
          * PENDING (not yet printed) → ``pre_event_dampen`` (uncertainty).
          * PRINTED with a parseable surprise → ``surprise_boost`` when the
            surprise favours the trade ``direction``, else ``surprise_dampen``.

        Surprise direction uses a coarse, documented assumption (higher actual
        vs forecast = stronger currency). It is intentionally simple and gated
        off by default; validate/refine in backtest (Phase 5) before enabling.
        """
        currencies = symbol_currencies(symbol)
        if not currencies:
            return 1.0

        events = await self.repository.get_in_window(
            currencies, now, self.high_window_min, min_impact=NewsImpact.HIGH
        )
        # Nearest event to now takes precedence when several overlap.
        events.sort(key=lambda e: abs((e.event_time_utc - now).total_seconds()))
        for event in events:
            # LOOKAHEAD SAFETY (backtest replay): an event still in the future
            # relative to `now` is PENDING — never read its `actual`, even if the
            # stored row already has one (filled by a later live scrape). Dampen.
            if event.event_time_utc > now:
                return self.pre_event_dampen  # pre-event uncertainty
            # Released (event_time <= now): the surprise is legitimately known.
            if event.has_actual:
                favored = self._surprise_favored_direction(symbol, event)
                if favored is None:
                    continue  # unparseable surprise → ignore this event
                return self.surprise_boost if favored == direction.upper() else self.surprise_dampen
        return 1.0

    @staticmethod
    def _surprise_favored_direction(symbol: str, event: NewsEvent) -> str | None:
        """Which trade direction ('BUY'/'SELL') the surprise favours, or None.

        Coarse model: a positive surprise (actual > forecast) strengthens the
        event's currency. A stronger BASE currency favours BUY; a stronger QUOTE
        currency favours SELL (gold/crypto: USD is the quote, so a strong-USD
        surprise favours SELL). Returns None when the surprise can't be parsed
        or the event currency isn't a leg of the symbol.
        """
        actual = _parse_numeric(event.actual)
        forecast = _parse_numeric(event.forecast)
        if actual is None or forecast is None or actual == forecast:
            return None

        legs = symbol_currencies(symbol)
        if event.currency not in legs:
            return None

        s = "".join(ch for ch in symbol.upper() if ch.isalnum())
        is_base = s[:3] == event.currency
        currency_stronger = actual > forecast
        if is_base:
            return "BUY" if currency_stronger else "SELL"
        return "SELL" if currency_stronger else "BUY"
