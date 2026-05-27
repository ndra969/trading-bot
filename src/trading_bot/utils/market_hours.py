"""Market hours utility — weekend/weekday + UTC session filtering."""

from datetime import UTC, datetime

from trading_bot.utils.market_session import derive_market_session


def is_market_open(
    asset_class: str,
    allowed_sessions: list[str] | None = None,
    now: datetime | None = None,
) -> bool:
    """Check if market is open for the given asset class and allowed sessions.

    Two layers of filtering:
      1. Weekend closure (forex/commodities only; crypto is 24/7).
      2. Session filter — if ``allowed_sessions`` is provided, the symbol
         only trades when the current UTC hour falls inside one of those
         sessions (per :func:`derive_market_session` buckets):
           - "tokyo"            00:00-07:59 UTC
           - "london"           08:00-12:59 UTC
           - "london_ny_overlap"  13:00-16:59 UTC  (matches BOTH "london" and "new_york")
           - "new_york"         17:00-21:59 UTC
           - "off_hours"        22:00-23:59 UTC  (rollover/illiquid)

         "24/7" in allowed_sessions overrides session filtering entirely.
         An empty/None list also means "no session filter" (always open
         within weekday hours).

    Args:
        asset_class: One of "crypto", "forex_major", "forex_jpy",
                     "commodities", "index".
        allowed_sessions: Optional list of session names this symbol can
                          trade in (from active_symbols.yaml per-symbol
                          ``trading_sessions``). When omitted, only the
                          weekend rule applies.
        now: Override "current time" (UTC) for testing. Defaults to
             ``datetime.now(UTC)``.

    Returns:
        True if market is open AND a permitted session is active.
    """
    current = now or datetime.now(UTC)

    if not _passes_weekend_filter(asset_class, current):
        return False

    if not _passes_session_filter(allowed_sessions, current):
        return False

    return True


def _passes_weekend_filter(asset_class: str, now: datetime) -> bool:
    """Apply the basic weekend rule (crypto is exempt)."""
    if asset_class == "crypto":
        return True

    weekday = now.weekday()  # 0=Monday … 5=Saturday, 6=Sunday
    hour = now.hour

    if weekday == 5:  # Saturday
        return False
    if weekday == 6 and hour < 21:  # Sunday before market open
        return False
    if weekday == 4 and hour >= 22:  # Friday after market close
        return False
    return True


def _passes_session_filter(allowed_sessions: list[str] | None, now: datetime) -> bool:
    """Apply per-symbol session filter using derive_market_session buckets."""
    if not allowed_sessions:
        return True  # No filter configured → always pass

    # 24/7 short-circuit (crypto and similar always-open instruments)
    if "24/7" in allowed_sessions:
        return True

    bucket = derive_market_session(now)
    if bucket == "off_hours":
        return False

    # london_ny_overlap is the high-liquidity window — admit it for any
    # symbol that allows either London or New York.
    if bucket == "london_ny_overlap":
        return "london" in allowed_sessions or "new_york" in allowed_sessions

    # Direct bucket match (sydney is mapped to "tokyo" bucket here since
    # they share the 00-08 UTC window in our coarse classification).
    if bucket in allowed_sessions:
        return True
    if bucket == "tokyo" and "sydney" in allowed_sessions:
        return True
    return False
