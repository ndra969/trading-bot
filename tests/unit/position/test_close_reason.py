"""Tests for CloseReason enum + resolve_close_reason helper.

Verifies the close-reason classification logic that maps MT5 deal reasons
+ position state flags to canonical CloseReason values.
"""

from datetime import datetime

import pytest

from trading_bot.position.close_reason import (
    MT5_DEAL_REASON_CLIENT,
    MT5_DEAL_REASON_EXPERT,
    MT5_DEAL_REASON_ROLLOVER,
    MT5_DEAL_REASON_SL,
    MT5_DEAL_REASON_SO,
    MT5_DEAL_REASON_TP,
    CloseReason,
    resolve_close_reason,
)
from trading_bot.position.position_models import Position, PositionStatus, PositionType


def _make_position(
    *,
    breakeven_activated: bool = False,
    trailing_activated: bool = False,
) -> Position:
    """Build a minimal Position with the flags we care about."""
    return Position(
        position_id="pos_test",
        symbol="EURUSD",
        position_type=PositionType.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        volume=0.01,
        pip_size=0.0001,
        pip_value_per_lot=10.0,
        status=PositionStatus.OPEN,
        open_time=datetime.now(),
        breakeven_activated=breakeven_activated,
        trailing_activated=trailing_activated,
    )


class TestServerSideCloses:
    """MT5 server-side close reasons take priority."""

    def test_tp_always_returns_take_profit(self):
        pos = _make_position(breakeven_activated=True, trailing_activated=True)
        assert (
            resolve_close_reason(pos, MT5_DEAL_REASON_TP) == CloseReason.TAKE_PROFIT
        )

    def test_so_returns_margin_stopout(self):
        pos = _make_position()
        assert (
            resolve_close_reason(pos, MT5_DEAL_REASON_SO) == CloseReason.MARGIN_STOPOUT
        )

    def test_rollover_returns_rollover(self):
        pos = _make_position()
        assert (
            resolve_close_reason(pos, MT5_DEAL_REASON_ROLLOVER) == CloseReason.ROLLOVER
        )


class TestSLDisambiguation:
    """SL close disambiguates via trailing/breakeven flags."""

    def test_sl_with_no_flags_is_stop_loss(self):
        pos = _make_position()
        assert resolve_close_reason(pos, MT5_DEAL_REASON_SL) == CloseReason.STOP_LOSS

    def test_sl_with_breakeven_only_is_breakeven_stop(self):
        pos = _make_position(breakeven_activated=True)
        assert (
            resolve_close_reason(pos, MT5_DEAL_REASON_SL) == CloseReason.BREAKEVEN_STOP
        )

    def test_sl_with_trailing_is_trailing_stop(self):
        pos = _make_position(trailing_activated=True)
        assert (
            resolve_close_reason(pos, MT5_DEAL_REASON_SL) == CloseReason.TRAILING_STOP
        )

    def test_sl_with_both_flags_prefers_trailing(self):
        # Trailing only activates AFTER breakeven, and SL never moves backward,
        # so trailing is the more informative classification.
        pos = _make_position(breakeven_activated=True, trailing_activated=True)
        assert (
            resolve_close_reason(pos, MT5_DEAL_REASON_SL) == CloseReason.TRAILING_STOP
        )


class TestBotInitiatedCloses:
    """CLIENT/EXPERT deals are bot-initiated; caller's hint wins."""

    def test_client_with_hint_uses_hint(self):
        pos = _make_position()
        assert (
            resolve_close_reason(
                pos, MT5_DEAL_REASON_CLIENT, CloseReason.MAX_DURATION
            )
            == CloseReason.MAX_DURATION
        )

    def test_expert_with_hint_uses_hint(self):
        pos = _make_position()
        assert (
            resolve_close_reason(
                pos, MT5_DEAL_REASON_EXPERT, CloseReason.MANUAL
            )
            == CloseReason.MANUAL
        )

    def test_client_without_hint_defaults_to_manual(self):
        pos = _make_position()
        assert resolve_close_reason(pos, MT5_DEAL_REASON_CLIENT) == CloseReason.MANUAL


class TestMissingDealInfo:
    """No MT5 deal info → fall back to caller hint or UNKNOWN."""

    def test_no_deal_no_hint_is_unknown(self):
        pos = _make_position()
        assert resolve_close_reason(pos, None) == CloseReason.UNKNOWN

    def test_no_deal_with_hint_uses_hint(self):
        pos = _make_position()
        assert (
            resolve_close_reason(pos, None, CloseReason.ORPHANED)
            == CloseReason.ORPHANED
        )

    def test_no_deal_with_mt5_missing_hint(self):
        pos = _make_position()
        assert (
            resolve_close_reason(pos, None, CloseReason.MT5_MISSING)
            == CloseReason.MT5_MISSING
        )


class TestEnumValues:
    """Enum values must be stable — they're persisted to DB."""

    @pytest.mark.parametrize(
        "reason,expected",
        [
            (CloseReason.TAKE_PROFIT, "TAKE_PROFIT"),
            (CloseReason.STOP_LOSS, "STOP_LOSS"),
            (CloseReason.BREAKEVEN_STOP, "BREAKEVEN_STOP"),
            (CloseReason.TRAILING_STOP, "TRAILING_STOP"),
            (CloseReason.MAX_DURATION, "MAX_DURATION"),
            (CloseReason.MANUAL, "MANUAL"),
            (CloseReason.MARGIN_STOPOUT, "MARGIN_STOPOUT"),
            (CloseReason.ROLLOVER, "ROLLOVER"),
            (CloseReason.ORPHANED, "ORPHANED"),
            (CloseReason.MT5_MISSING, "MT5_MISSING"),
            (CloseReason.UNKNOWN, "UNKNOWN"),
        ],
    )
    def test_enum_string_value(self, reason, expected):
        assert reason.value == expected
