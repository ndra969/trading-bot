"""Dry-Run MT5 Wrapper.

Wraps :class:`MT5Connector` so write operations (place_order, modify_position,
close_position) return realistic simulated results in dry-run mode while read
operations (get_positions, health_check, etc.) pass through to the real
connector unchanged.

This lets main bot code call ``self.mt5.place_order(...)`` without scattering
``if not is_dry_run`` checks at every callsite — the wrapper handles the gate.

Usage::

    real_mt5 = MT5Connector(...)
    real_mt5.initialize()
    mt5 = DryRunMT5Wrapper(real_mt5, dry_run=True)  # All writes simulated
    mt5.place_order(...)  # Returns simulated success result

Integration status: implementation complete with tests. main.py wiring is
left to a future PR (existing scattered ``if not is_dry_run`` checks still
work correctly).
"""

from __future__ import annotations

from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class DryRunMT5Wrapper:
    """Transparent dry-run wrapper around :class:`MT5Connector`.

    Write operations (place_order, modify_position, close_position) are
    short-circuited to simulated results when ``dry_run=True``. Read
    operations always pass through to the wrapped connector.

    The wrapper tracks simulated orders/modifications in memory so callers
    can inspect them via :meth:`get_simulated_orders`.

    Attributes:
        connector: Underlying real MT5Connector instance.
        dry_run: When True, write ops return simulated results without
            touching MT5. When False, the wrapper is a transparent pass-through.
    """

    # Starting ticket counter for simulated orders (offset to avoid clashing
    # with realistic MT5 ticket ranges in logs/DB).
    _DRY_RUN_TICKET_START = 90_000_000

    def __init__(self, connector: Any, dry_run: bool = False) -> None:
        """Initialize wrapper.

        Args:
            connector: Real MT5Connector instance to wrap.
            dry_run: When True, simulate write operations. When False, the
                wrapper is a transparent pass-through (useful for live mode
                with the same code path).
        """
        self.connector = connector
        self.dry_run = dry_run
        self._simulated_orders: list[dict[str, Any]] = []
        self._simulated_modifications: list[dict[str, Any]] = []
        self._simulated_closes: list[dict[str, Any]] = []
        self._ticket_counter = self._DRY_RUN_TICKET_START

    # ─────────────────────────────────────────────────────────────────────
    # Write operations (intercepted in dry-run mode)
    # ─────────────────────────────────────────────────────────────────────

    def place_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        price: float | None = None,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Place a market or pending order (simulated in dry-run mode).

        Returns the same dict shape as MT5Connector.place_order:
            {"success": True, "order": <ticket>, "price": <fill_price>, ...}
        """
        if not self.dry_run:
            return self.connector.place_order(
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                price=price,
                sl=sl,
                tp=tp,
                comment=comment,
                **kwargs,
            )

        ticket = self._next_ticket()
        fill_price = price if price is not None else 0.0  # Real fill comes from market
        result = {
            "success": True,
            "order": ticket,
            "deal": ticket,
            "volume": volume,
            "price": fill_price,
            "comment": f"DRY-RUN: {comment}" if comment else "DRY-RUN",
            "retcode": 10009,  # TRADE_RETCODE_DONE
        }

        self._simulated_orders.append(
            {
                "ticket": ticket,
                "symbol": symbol,
                "order_type": order_type,
                "volume": volume,
                "price": fill_price,
                "sl": sl,
                "tp": tp,
                "comment": comment,
            }
        )
        logger.info(
            f"[DRY-RUN] Simulated order: {order_type} {volume} {symbol} "
            f"@ {fill_price} (ticket {ticket})"
        )
        return result

    def modify_position(
        self,
        ticket: int,
        sl: float | None = None,
        tp: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Modify position SL/TP (simulated in dry-run mode).

        Returns the same dict shape as MT5Connector.modify_position:
            {"success": True, "modified": True, "message": "..."}
        """
        if not self.dry_run:
            return self.connector.modify_position(ticket=ticket, sl=sl, tp=tp, **kwargs)

        self._simulated_modifications.append({"ticket": ticket, "sl": sl, "tp": tp})
        logger.info(
            f"[DRY-RUN] Simulated modify: ticket {ticket} SL={sl} TP={tp}"
        )
        return {
            "success": True,
            "modified": True,
            "sl_changed": sl is not None,
            "tp_changed": tp is not None,
            "message": "DRY-RUN: Position modified",
        }

    def close_position(
        self,
        ticket: int,
        volume: float | None = None,
        comment: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Close a position fully or partially (simulated in dry-run mode).

        Returns the same dict shape as MT5Connector.close_position:
            {"success": True, "ticket": <ticket>, ...}
        """
        if not self.dry_run:
            return self.connector.close_position(
                ticket=ticket, volume=volume, comment=comment, **kwargs
            )

        self._simulated_closes.append(
            {"ticket": ticket, "volume": volume, "comment": comment}
        )
        logger.info(
            f"[DRY-RUN] Simulated close: ticket {ticket} volume={volume}"
        )
        return {
            "success": True,
            "ticket": ticket,
            "volume": volume,
            "comment": f"DRY-RUN: {comment}" if comment else "DRY-RUN: Position closed",
            "retcode": 10009,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Read operations (always pass through to real connector)
    # ─────────────────────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        """Pass through to wrapped connector."""
        return self.connector.is_connected()

    def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """Pass through to wrapped connector.

        Note: In dry-run mode this still queries the real MT5 — simulated
        orders are NOT included in the returned list (intentional, to avoid
        polluting real position tracking with simulations).
        """
        return self.connector.get_positions(symbol=symbol) if symbol else self.connector.get_positions()

    def get_history_deal(self, ticket: int) -> dict[str, Any] | None:
        """Pass through to wrapped connector."""
        return self.connector.get_history_deal(ticket)

    def health_check(self) -> dict[str, Any]:
        """Pass through to wrapped connector."""
        return self.connector.health_check()

    @property
    def account_info(self) -> dict[str, Any]:
        """Pass through to wrapped connector."""
        return self.connector.account_info

    @property
    def terminal_info(self) -> dict[str, Any]:
        """Pass through to wrapped connector."""
        return self.connector.terminal_info

    def __getattr__(self, name: str) -> Any:
        """Forward any unrecognized attribute access to the wrapped connector.

        Lets the wrapper substitute transparently for MT5Connector even when
        callers access methods/attributes not explicitly defined above.
        """
        # __getattr__ is only called when normal lookup fails, so we won't
        # accidentally shadow our own methods.
        return getattr(self.connector, name)

    # ─────────────────────────────────────────────────────────────────────
    # Inspection helpers (dry-run state)
    # ─────────────────────────────────────────────────────────────────────

    def get_simulated_orders(self) -> list[dict[str, Any]]:
        """Return a copy of all orders simulated since wrapper creation/last clear."""
        return self._simulated_orders.copy()

    def get_simulated_modifications(self) -> list[dict[str, Any]]:
        """Return a copy of all modifications simulated since creation/last clear."""
        return self._simulated_modifications.copy()

    def get_simulated_closes(self) -> list[dict[str, Any]]:
        """Return a copy of all closes simulated since creation/last clear."""
        return self._simulated_closes.copy()

    def clear_simulated_history(self) -> None:
        """Clear all simulated orders/modifications/closes from memory."""
        self._simulated_orders.clear()
        self._simulated_modifications.clear()
        self._simulated_closes.clear()
        self._ticket_counter = self._DRY_RUN_TICKET_START
        logger.info("[DRY-RUN] Cleared simulated history")

    # ─────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────

    def _next_ticket(self) -> int:
        """Generate the next simulated ticket ID (monotonically increasing)."""
        ticket = self._ticket_counter
        self._ticket_counter += 1
        return ticket
