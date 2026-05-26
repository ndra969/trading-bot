"""Derive market session bucket from a UTC timestamp.

Used to label positions with the session they were opened in for
time-of-day performance analytics (e.g., "are we losing in Asian
session?"). Buckets cover the four canonical FX sessions plus the
high-liquidity London/NY overlap.

Boundaries are UTC. Times outside any open session fall back to "off_hours"
(weekend or early Sunday).
"""

from __future__ import annotations

from datetime import datetime


def derive_market_session(ts: datetime) -> str:
    """Map a timestamp to a market session bucket.

    Buckets (UTC):
        tokyo               00:00–07:59
        london              08:00–12:59
        london_ny_overlap   13:00–16:59  (highest liquidity)
        new_york            17:00–21:59
        off_hours           22:00–23:59  (rollover/illiquid)

    Args:
        ts: Timestamp to classify (naive UTC or timezone-aware).

    Returns:
        Session name as a lowercase string.
    """
    hour = ts.hour

    if 0 <= hour < 8:
        return "tokyo"
    if 8 <= hour < 13:
        return "london"
    if 13 <= hour < 17:
        return "london_ny_overlap"
    if 17 <= hour < 22:
        return "new_york"
    return "off_hours"
