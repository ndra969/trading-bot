"""
Dry-Run Wrapper for MT5 Operations

Wraps real MT5 operations to prevent actual order execution in dry-run mode.
"""

from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class DryRunOrderManager:
    """
    Wrapper for OrderManager that simulates orders in dry-run mode.
    """

    def __init__(self, real_order_manager, dry_run: bool = False):
        """
        Initialize dry-run wrapper.

        Args:
            real_order_manager: Real OrderManager instance
            dry_run: Whether to run in dry-run mode
        """
        self.real_manager = real_order_manager
        self.dry_run = dry_run
        self._simulated_orders = []
        self._order_counter = 1000

    def send_market_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        sl: float | None = None,
        tp: float | None = None,
        deviation: int = 10,
        comment: str = "",
    ) -> dict[str, Any]:
        """
        Send market order (simulated in dry-run mode).
        """
        if self.dry_run:
            # Simulate order
            logger.info(f"[DRY-RUN] Simulated market order: {order_type} {volume} {symbol}")

            simulated_result = {
                "retcode": 10009,  # TRADE_RETCODE_DONE
                "deal": self._order_counter,
                "order": self._order_counter,
                "volume": volume,
                "price": 1.10000,  # Simulated price
                "comment": f"DRY-RUN: {comment}",
                "request_id": self._order_counter,
            }

            self._simulated_orders.append(
                {
                    "type": "market",
                    "symbol": symbol,
                    "order_type": order_type,
                    "volume": volume,
                    "sl": sl,
                    "tp": tp,
                    "result": simulated_result,
                }
            )

            self._order_counter += 1
            logger.info(f"[DRY-RUN] Order simulated successfully: {simulated_result}")

            return simulated_result
        else:
            # Execute real order
            return self.real_manager.send_market_order(
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                sl=sl,
                tp=tp,
                deviation=deviation,
                comment=comment,
            )

    def send_pending_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        price: float,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "",
    ) -> dict[str, Any]:
        """
        Send pending order (simulated in dry-run mode).
        """
        if self.dry_run:
            # Simulate order
            logger.info(
                f"[DRY-RUN] Simulated pending order: {order_type} {volume} {symbol} @ {price}"
            )

            simulated_result = {
                "retcode": 10009,
                "deal": 0,
                "order": self._order_counter,
                "volume": volume,
                "price": price,
                "comment": f"DRY-RUN: {comment}",
            }

            self._simulated_orders.append(
                {
                    "type": "pending",
                    "symbol": symbol,
                    "order_type": order_type,
                    "volume": volume,
                    "price": price,
                    "sl": sl,
                    "tp": tp,
                    "result": simulated_result,
                }
            )

            self._order_counter += 1
            logger.info(f"[DRY-RUN] Pending order simulated: {simulated_result}")

            return simulated_result
        else:
            # Execute real order
            return self.real_manager.send_pending_order(
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                price=price,
                sl=sl,
                tp=tp,
                comment=comment,
            )

    def modify_position(
        self,
        ticket: int,
        sl: float | None = None,
        tp: float | None = None,
    ) -> dict[str, Any]:
        """
        Modify position (simulated in dry-run mode).
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Simulated position modification: {ticket} SL={sl} TP={tp}")

            simulated_result = {
                "retcode": 10009,
                "comment": "DRY-RUN: Position modified",
            }

            logger.info(f"[DRY-RUN] Modification simulated: {simulated_result}")
            return simulated_result
        else:
            return self.real_manager.modify_position(ticket=ticket, sl=sl, tp=tp)

    def close_position(
        self,
        ticket: int,
        volume: float | None = None,
        deviation: int = 10,
    ) -> dict[str, Any]:
        """
        Close position (simulated in dry-run mode).
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Simulated position close: {ticket} volume={volume}")

            simulated_result = {
                "retcode": 10009,
                "deal": self._order_counter,
                "comment": "DRY-RUN: Position closed",
            }

            self._order_counter += 1
            logger.info(f"[DRY-RUN] Close simulated: {simulated_result}")

            return simulated_result
        else:
            return self.real_manager.close_position(
                ticket=ticket,
                volume=volume,
                deviation=deviation,
            )

    def get_simulated_orders(self) -> list:
        """
        Get list of simulated orders (dry-run only).

        Returns:
            List of simulated orders
        """
        return self._simulated_orders.copy()

    def clear_simulated_orders(self) -> None:
        """Clear simulated orders history."""
        self._simulated_orders.clear()
        logger.info("[DRY-RUN] Cleared simulated orders history")
