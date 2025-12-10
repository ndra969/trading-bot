"""
Position Tracker - Real-time position tracking and updates.

Tracks position status and calculates real-time P&L.
"""

from datetime import datetime

from trading_bot.position.pip_calculator import PipCalculator
from trading_bot.position.position_models import Position, PositionStatus
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class PositionTracker:
    """
    Tracks and updates positions in real-time.

    Responsibilities:
    - Update position with current market price
    - Calculate real-time profit in pips and USD
    - Track position age and duration
    - Update position status
    """

    def __init__(self):
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

        logger.debug(
            f"Updated {position.position_id}: "
            f"{position.current_profit_pips:.1f} pips, "
            f"${position.current_pnl_usd:.2f}"
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

        logger.info(
            f"Closed position {position.position_id}: "
            f"{position.current_profit_pips:.1f} pips, "
            f"${position.current_pnl_usd:.2f} P&L"
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

    def get_position_summary(self, position: Position) -> dict:
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
