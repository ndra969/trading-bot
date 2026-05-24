"""Market hours utility - check if market is open by asset class.

Simple weekend/weekday rules. For more sophisticated session-based validation
see config/market_hours.yaml (planned).
"""

from datetime import UTC, datetime


def is_market_open(asset_class: str) -> bool:
    """Check if market is open for the given asset class.

    Rules:
        - crypto: always open (24/7)
        - forex/commodities/other:
            - Saturday: closed
            - Sunday before 21:00 UTC: closed
            - Friday after 22:00 UTC: closed
            - Otherwise: open

    Args:
        asset_class: One of "crypto", "forex_major", "forex_jpy",
                     "commodities", "index"

    Returns:
        True if market likely open, False otherwise.
    """
    # Crypto is always open
    if asset_class == "crypto":
        return True

    now = datetime.now(UTC)
    weekday = now.weekday()  # 0=Monday, ..., 5=Saturday, 6=Sunday
    hour = now.hour

    # Saturday: closed
    if weekday == 5:
        return False

    # Sunday before market open (~21:00 UTC)
    if weekday == 6 and hour < 21:
        return False

    # Friday after market close (~22:00 UTC)
    if weekday == 4 and hour >= 22:
        return False

    return True
