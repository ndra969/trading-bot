"""
Position Tracker - Real-time position tracking and updates.

Tracks position status and calculates real-time P&L.
"""

from datetime import datetime
from typing import Any

from trading_core.utils.logger import get_logger

from trading_worker.position.pip_calculator import PipCalculator
from trading_worker.position.position_models import Position, PositionStatus

logger = get_logger(__name__)


def classify_exit_type(pnl_usd: float) -> str:
    """Classify a closed position's outcome from its realized P&L.

    Single source of truth for the DB ``exit_type`` column
    (constraint: WIN / LOSS / BREAKEVEN). This is an *outcome* bucket and is
    orthogonal to *how* the position closed (SL / TP / trailing / breakeven),
    which is captured separately in ``close_reason``.
    """
    if pnl_usd > 0:
        return "WIN"
    if pnl_usd < 0:
        return "LOSS"
    return "BREAKEVEN"


class PositionTracker:
    """
    Tracks and updates positions in real-time.

    Responsibilities:
    - Update position with current market price
    - Calculate real-time profit in pips and USD
    - Track position age and duration
    - Update position status
    """

    def __init__(self) -> None:
        """Initialize position tracker."""
        self.pip_calculator = PipCalculator()
        logger.debug("PositionTracker initialized")

    def update_position_price(self, position: Position, current_price: float) -> None:
        """
        Update position with current market price.

        Args:
            position: Position to update
            current_price: Current market price

        Updates position in-place with:
        - current_price
        - current_profit_pips
        - current_pnl_usd
        - mae_pips (maximum adverse excursion)
        - mfe_pips (maximum favorable excursion)
        - max_profit_pips
        - max_drawdown_pips
        """
        if not position.is_open:
            logger.warning(
                f"Cannot update price for {position.status.value} position {position.position_id}"
            )
            return

        # Update current price
        position.current_price = current_price

        # Calculate current profit in pips
        position.current_profit_pips = self.pip_calculator.calculate_pips(
            symbol=position.symbol,
            entry_price=position.entry_price,
            current_price=current_price,
            position_type=position.position_type.value,
        )

        # Calculate current P&L in USD
        pip_value = position.pip_value_per_lot
        position.current_pnl_usd = position.current_profit_pips * pip_value

        # Update MAE/MFE tracking
        # MFE: Maximum favorable excursion (highest profit)
        if position.current_profit_pips > position.mfe_pips:
            position.mfe_pips = position.current_profit_pips
            position.max_profit_pips = position.current_profit_pips

        # MAE: Maximum adverse excursion (lowest profit / highest drawdown)
        if position.current_profit_pips < position.mae_pips:
            position.mae_pips = position.current_profit_pips
            # Track max drawdown as negative value
            if position.current_profit_pips < 0:
                drawdown = abs(position.current_profit_pips)
                if drawdown > position.max_drawdown_pips:
                    position.max_drawdown_pips = drawdown

        logger.debug(
            f"Updated {position.position_id}: "
            f"{position.current_profit_pips:.1f} pips, "
            f"${position.current_pnl_usd:.2f}, "
            f"MAE: {position.mae_pips:.1f}, MFE: {position.mfe_pips:.1f}"
        )

    def open_position(self, position: Position) -> None:
        """
        Mark position as open.

        Args:
            position: Position to open

        Updates position in-place with:
        - status = OPEN
        - open_time = now
        - Initialize P&L tracking
        """
        if position.status != PositionStatus.PENDING:
            logger.warning(
                f"Cannot open position {position.position_id} with status {position.status.value}"
            )
            return

        position.status = PositionStatus.OPEN
        position.open_time = datetime.now()
        position.current_price = position.entry_price
        position.current_profit_pips = 0.0
        position.current_pnl_usd = 0.0

        # Calculate distance to SL and TP in pips
        position.entry_to_sl_pips = abs(
            self.pip_calculator.calculate_pips(
                symbol=position.symbol,
                entry_price=position.entry_price,
                current_price=position.stop_loss,
                position_type=position.position_type.value,
            )
        )
        position.entry_to_tp_pips = abs(
            self.pip_calculator.calculate_pips(
                symbol=position.symbol,
                entry_price=position.entry_price,
                current_price=position.take_profit,
                position_type=position.position_type.value,
            )
        )

        # Calculate risk and potential profit amounts
        position.risk_amount_usd = self.pip_calculator.calculate_usd_amount(
            symbol=position.symbol,
            entry_price=position.entry_price,
            target_price=position.stop_loss,
            volume=position.volume,
        )

        position.potential_profit_usd = self.pip_calculator.calculate_usd_amount(
            symbol=position.symbol,
            entry_price=position.entry_price,
            target_price=position.take_profit,
            volume=position.volume,
        )

        # Initialize MAE/MFE tracking
        position.mae_pips = 0.0
        position.mfe_pips = 0.0
        position.max_profit_pips = 0.0
        position.max_drawdown_pips = 0.0

        # Calculate R:R ratio based on USD (for verification)
        rr_ratio_usd = (
            position.potential_profit_usd / position.risk_amount_usd
            if position.risk_amount_usd > 0
            else 0.0
        )

        logger.info(
            f"Opened position {position.position_id}: {position.position_type.value} "
            f"{position.symbol} @ {position.entry_price:.5f}, "
            f"Risk: ${position.risk_amount_usd:.2f}, "
            f"Potential: ${position.potential_profit_usd:.2f}, "
            f"R:R (USD): {rr_ratio_usd:.2f}, "
            f"R:R (Price): {position.risk_reward_ratio:.2f}"
        )

    def close_position(self, position: Position, close_price: float) -> None:
        """
        Close a position.

        Args:
            position: Position to close
            close_price: Price at which position was closed

        Updates position in-place with:
        - status = CLOSED
        - close_time = now
        - close_price
        - Final P&L
        - is_winner (True if profit, False if loss)
        - exit_type (WIN / LOSS / BREAKEVEN, from realized P&L)
        """
        if position.status != PositionStatus.OPEN:
            logger.warning(
                f"Cannot close position {position.position_id} with status {position.status.value}"
            )
            return

        position.status = PositionStatus.CLOSED
        position.close_time = datetime.now()
        position.close_price = close_price

        # Calculate final P&L
        position.current_profit_pips = self.pip_calculator.calculate_pips(
            symbol=position.symbol,
            entry_price=position.entry_price,
            current_price=close_price,
            position_type=position.position_type.value,
        )

        pip_value = position.pip_value_per_lot
        position.current_pnl_usd = position.current_profit_pips * pip_value

        # Freeze realized result at close (current_* keeps mutating on later
        # price updates / reconciliation; realized_* is the immutable outcome
        # used by analytics and reporting).
        position.realized_profit_pips = position.current_profit_pips
        position.realized_pnl_usd = position.current_pnl_usd

        # Set is_winner + exit_type from the (pip-recomputed) realized P&L.
        # Reconciled MT5 closes refine these from the broker's authoritative
        # P&L (incl. swap/commission) in _finalize_closed_position.
        position.is_winner = position.current_pnl_usd > 0
        position.exit_type = classify_exit_type(position.current_pnl_usd)

        # Calculate holding time in seconds
        if position.open_time:
            position.holding_time_seconds = int(
                (position.close_time - position.open_time).total_seconds()
            )

        logger.info(
            f"Closed position {position.position_id}: "
            f"{position.current_profit_pips:.1f} pips, "
            f"${position.current_pnl_usd:.2f} P&L, "
            f"Winner: {position.is_winner}, "
            f"Held: {position.holding_time_seconds}s"
        )

    def check_stop_loss(self, position: Position) -> bool:
        """
        Check if stop loss was hit.

        Args:
            position: Position to check

        Returns:
            True if stop loss was hit
        """
        if not position.is_open or position.current_price is None:
            return False

        if position.position_type.value == "BUY":
            return position.current_price <= position.stop_loss
        else:  # SELL
            return position.current_price >= position.stop_loss

    def check_take_profit(self, position: Position) -> bool:
        """
        Check if take profit was hit.

        Args:
            position: Position to check

        Returns:
            True if take profit was hit
        """
        if not position.is_open or position.current_price is None:
            return False

        if position.position_type.value == "BUY":
            return position.current_price >= position.take_profit
        else:  # SELL
            return position.current_price <= position.take_profit

    def get_position_summary(self, position: Position) -> dict[str, Any]:
        """
        Get position summary.

        Args:
            position: Position to summarize

        Returns:
            Dictionary with position summary
        """
        return {
            "position_id": position.position_id,
            "symbol": position.symbol,
            "type": position.position_type.value,
            "status": position.status.value,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "stop_loss": position.stop_loss,
            "take_profit": position.take_profit,
            "profit_pips": position.current_profit_pips,
            "pnl_usd": position.current_pnl_usd,
            "risk_usd": position.risk_amount_usd,
            "potential_usd": position.potential_profit_usd,
            "duration_seconds": position.duration_seconds,
            "risk_reward_ratio": position.risk_reward_ratio,
        }
