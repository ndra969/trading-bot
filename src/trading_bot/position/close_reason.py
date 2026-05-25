"""Close reason classification for positions.

Resolves a canonical CloseReason from MT5 deal history + position state flags.
This is the single source of truth for *why* a position closed.

Determination logic relies on two invariants enforced by config validation
(see config_validator.py):
  1. Trailing always activates at a HIGHER profit threshold than breakeven,
     so breakeven_activated=True is reached before trailing_activated=True.
  2. Trailing SL never moves backward, so trailing_activated=True + SL hit
     ⟹ position closed in profit (TRAILING_STOP).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from trading_bot.position.position_models import Position


# MT5 deal reason codes (from MetaTrader5.DEAL_REASON_*)
# See: https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties
MT5_DEAL_REASON_CLIENT = 0
MT5_DEAL_REASON_EXPERT = 3
MT5_DEAL_REASON_SL = 4
MT5_DEAL_REASON_TP = 5
MT5_DEAL_REASON_SO = 6  # Stop-out (margin call)
MT5_DEAL_REASON_ROLLOVER = 7


class CloseReason(str, Enum):
    """Canonical close reasons. Stored in positions.close_reason."""

    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    BREAKEVEN_STOP = "BREAKEVEN_STOP"
    TRAILING_STOP = "TRAILING_STOP"
    MAX_DURATION = "MAX_DURATION"
    MANUAL = "MANUAL"
    MARGIN_STOPOUT = "MARGIN_STOPOUT"
    ROLLOVER = "ROLLOVER"
    ORPHANED = "ORPHANED"
    MT5_MISSING = "MT5_MISSING"
    UNKNOWN = "UNKNOWN"


def resolve_close_reason(
    position: Position,
    mt5_deal_reason: int | None,
    bot_initiated_reason: CloseReason | None = None,
) -> CloseReason:
    """Resolve canonical CloseReason from MT5 deal + position state.

    Priority:
      1. MT5 server-side close (SL/TP/SO/ROLLOVER) — authoritative
      2. Bot-initiated close (MAX_DURATION, MANUAL) — caller provides
      3. UNKNOWN fallback

    SL disambiguation uses position flags:
      - trailing_activated → TRAILING_STOP (guaranteed profit by invariant)
      - breakeven_activated → BREAKEVEN_STOP (near-zero, intended profit)
      - else → STOP_LOSS (original SL, loss)

    Args:
        position: Position being closed (flags inspected).
        mt5_deal_reason: MT5 deal.reason code, or None if unavailable.
        bot_initiated_reason: Explicit reason set by bot code path (e.g.,
            MAX_DURATION when bot force-closed on timeout). Used only when
            mt5_deal_reason is CLIENT/EXPERT (i.e., we triggered the close).

    Returns:
        CloseReason enum value.
    """
    # Server-side closes — MT5 is authoritative
    if mt5_deal_reason == MT5_DEAL_REASON_TP:
        return CloseReason.TAKE_PROFIT

    if mt5_deal_reason == MT5_DEAL_REASON_SL:
        if position.trailing_activated:
            return CloseReason.TRAILING_STOP
        if position.breakeven_activated:
            return CloseReason.BREAKEVEN_STOP
        return CloseReason.STOP_LOSS

    if mt5_deal_reason == MT5_DEAL_REASON_SO:
        return CloseReason.MARGIN_STOPOUT

    if mt5_deal_reason == MT5_DEAL_REASON_ROLLOVER:
        return CloseReason.ROLLOVER

    # Bot-initiated close (CLIENT/EXPERT) — trust the caller's intent
    if mt5_deal_reason in (MT5_DEAL_REASON_CLIENT, MT5_DEAL_REASON_EXPERT):
        if bot_initiated_reason is not None:
            return bot_initiated_reason
        return CloseReason.MANUAL

    # No MT5 deal info available — fall back to caller's hint
    if bot_initiated_reason is not None:
        return bot_initiated_reason

    return CloseReason.UNKNOWN
