"""
Position Orchestrator — reconciliation + per-position automation.

Extracted from TradingBot (back-reference pattern): holds a reference to the
parent bot and operates on its dependencies via ``self.bot``. The only public
entry point is :meth:`manage_positions`, called from ``TradingBot._trading_loop``.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from trading_core.enums.close_reason import CloseReason, resolve_close_reason
from trading_core.utils.logger import get_logger

from trading_worker.position.pip_calculator import PipCalculator
from trading_worker.position.position_models import Position, PositionStatus, PositionType
from trading_worker.position.position_tracker import classify_exit_type
from trading_worker.utils.notification_manager import NotificationLevel

if TYPE_CHECKING:
    from trading_worker.main import TradingBot

logger = get_logger(__name__)


class PositionOrchestrator:
    def __init__(self, bot: "TradingBot"):
        self.bot = bot

    async def _update_session_on_position_close(self, position: Position, result: dict | None):
        """Update session aggregations when a position closes.

        Attributes the close to the session the position was OPENED in
        (position.session_id), not the bot's currently-active session.
        Without this, a position opened in session A but closed in session
        B (after a bot restart) would inflate B's stats and leave A's at 0.

        Args:
            position: Closed position
            result: Close result dict with pnl_usd and pips
        """
        if not self.bot.session_repository or not result:
            return

        target_session_id = position.session_id or (
            self.bot.current_session.session_id if self.bot.current_session else None
        )
        if not target_session_id:
            return

        try:
            pnl_usd = result.get("pnl_usd", 0.0)
            is_winner = pnl_usd > 0
            gross_profit = pnl_usd if is_winner else 0.0
            gross_loss = abs(pnl_usd) if not is_winner else 0.0

            await self.bot.session_repository.update_aggregations(
                session_id=target_session_id,
                pnl=pnl_usd,
                is_winner=is_winner,
                gross_profit=gross_profit,
                gross_loss=gross_loss,
            )
            logger.debug(
                f"  📊 Session aggregations updated ({target_session_id}): "
                f"P&L=${pnl_usd:.2f}, Winner={is_winner}"
            )
        except Exception as e:
            logger.warning(f"Error updating session aggregations: {e}")

    def _resolve_mt5_ticket(self, position, broker_symbol: str) -> int | None:
        """Resolve MT5 ticket for a position via 3-stage fallback chain.

        Lookup order (mutates position to cache discovered ticket):
            1. position.ticket attribute (set during creation)
            2. position.metadata["ticket"] (loaded from DB)
            3. MT5 query by symbol + entry_price match (recovery from sync loss)

        Args:
            position: Position object (may be mutated to cache ticket)
            broker_symbol: Broker-formatted symbol for MT5 query

        Returns:
            Ticket number if found, None if all fallbacks fail.
        """
        # 1. From position object (fast path)
        ticket = getattr(position, "ticket", None)
        if ticket:
            return int(ticket)

        # 2. From metadata (cache from DB load)
        if position.metadata and position.metadata.get("ticket"):
            ticket = int(position.metadata["ticket"])
            position.ticket = ticket  # Cache on object
            logger.debug(f"  🎫 Found ticket {ticket} from metadata for {position.position_id}")
            return ticket

        # 3. MT5 lookup by symbol + entry_price (recovery)
        if not self.bot.mt5:
            return None

        logger.debug(f"  🔍 Looking up ticket for {broker_symbol} from MT5...")
        open_positions = self.bot.mt5.get_positions(symbol=broker_symbol)
        if not open_positions:
            return None

        # Match by entry price (most accurate)
        for mt5_pos in open_positions:
            mt5_entry = mt5_pos.get("price_open", 0.0)
            if abs(mt5_entry - position.entry_price) < 0.0001:
                ticket = mt5_pos.get("ticket")
                self._cache_ticket(position, ticket)
                logger.info(
                    f"  🎫 Found ticket {ticket} for {position.position_id} "
                    f"via MT5 lookup (entry: {mt5_entry:.5f})"
                )
                return ticket

        # Last resort: single MT5 position for this symbol
        if len(open_positions) == 1:
            ticket = open_positions[0].get("ticket")
            self._cache_ticket(position, ticket)
            logger.warning(
                f"  ⚠️ Using first position ticket {ticket} for {position.position_id} "
                f"(no entry price match)"
            )
            return ticket

        return None

    def _cache_ticket(self, position, ticket: int) -> None:
        """Store ticket on position object + metadata for future lookups."""
        position.ticket = ticket
        if not position.metadata:
            position.metadata = {}
        position.metadata["ticket"] = ticket

    def _automation_preflight_passed(self, position, is_dry_run: bool) -> bool:
        """Verify position is eligible for automation (open, in MT5, has price data).

        Returns:
            True if all checks pass and automation should proceed.
            False if any check fails (orphan, closed externally, missing data).
        """
        # 1. Position must still be open (may have been closed during sync)
        if not position.is_open:
            logger.debug(
                f"Skipping automation for {position.position_id} ({position.symbol}): "
                f"Position is {position.status.value}, not OPEN"
            )
            return False

        # 2. Live trading: verify ticket still exists in MT5
        if not is_dry_run and self.bot.mt5 and self.bot.mt5.is_connected():
            ticket = getattr(position, "ticket", None)
            if not ticket and position.metadata:
                ticket = position.metadata.get("ticket")

            if ticket:
                mt5_tickets = {
                    p.get("ticket") for p in self.bot.mt5.get_positions() if p.get("ticket")
                }
                if ticket not in mt5_tickets:
                    logger.warning(
                        f"  ⚠️ SKIPPING AUTOMATION: Position {position.position_id} "
                        f"(Ticket {ticket}) not found in MT5 - position was closed. "
                        f"Should have been caught during sync reconciliation."
                    )
                    return False
            else:
                logger.error(
                    f"  ❌ SKIPPING AUTOMATION: Position {position.position_id} has NO TICKET! "
                    f"This is an ORPHANED position. Check manage_positions sync logic."
                )
                return False

        # 3. Position must have current price for automation calculations
        if position.current_price is None:
            logger.warning(
                f"  ⚠️ Cannot check automation for {position.position_id}: current_price is None"
            )
            return False

        return True

    async def _update_position_and_run_automation(self, position, is_dry_run: bool) -> None:
        """Update price + run automation checks for a single open position.

        Steps (each with safety re-check that position is still OPEN):
            1. Skip if position is already closed (raced with sync)
            2. (Live only) Verify ticket still exists in MT5; close if not found
            3. Fetch current price; skip if unavailable
            4. Update position with new price + save to DB
            5. Run automation checks (breakeven / trailing / partial close)
        """
        # 1. Skip if already closed
        if not position.is_open:
            logger.debug(
                f"  ⚠️ Position {position.position_id} is no longer open - skipping update"
            )
            return

        # 2. Live trading: verify position still exists in MT5
        if not is_dry_run and self.bot.mt5 and self.bot.mt5.is_connected():
            if await self._close_if_missing_from_mt5(position, is_dry_run):
                return  # Position was closed (no longer in MT5)

        # Re-check after MT5 verification
        if not position.is_open:
            logger.debug(f"  ⚠️ Position {position.position_id} closed during MT5 check - skipping")
            return

        # 3. Get current price
        current_price = await self.bot._get_current_price(position.symbol)
        if current_price is None:
            logger.debug(
                f"  ⚠️ Could not get current price for {position.symbol} - skipping update"
            )
            return

        # 4. Update + persist
        self.bot.position_manager.update_position(position.position_id, current_price)
        logger.debug(
            f"  ✅ Updated {position.position_id} ({position.symbol}): "
            f"price={current_price:.5f}, profit={position.current_profit_pips:.1f} pips"
        )
        await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)

        # 5. Final check before automation
        if not position.is_open:
            logger.debug(
                f"  ⚠️ Position {position.position_id} closed during update - skipping automation"
            )
            return

        await self._check_position_automation(position)

    async def _close_if_missing_from_mt5(self, position, is_dry_run: bool) -> bool:
        """If position's ticket is no longer in MT5, close it in our DB.

        Returns:
            True if position was closed (caller should stop processing this position),
            False if position is still valid in MT5 or has no ticket to verify.
        """
        ticket = getattr(position, "ticket", None)
        if not ticket and position.metadata:
            ticket = position.metadata.get("ticket")
        if not ticket:
            return False  # Can't verify without ticket

        mt5_positions = self.bot.mt5.get_positions()
        mt5_tickets = {p.get("ticket") for p in mt5_positions if p.get("ticket")}
        if ticket in mt5_tickets:
            return False  # Still exists in MT5

        # Ticket missing → was closed externally
        logger.warning(
            f"  ⚠️ Position {position.position_id} (Ticket {ticket}) "
            f"not found in MT5 during update - closing position"
        )
        close_price, pnl, comment, mt5_reason = self._resolve_mt5_deal_details(
            ticket, position.current_price or position.entry_price
        )
        reason = resolve_close_reason(position, mt5_reason)
        await self._finalize_closed_position(
            position,
            close_price=close_price,
            pnl=pnl,
            reason=reason,
            is_dry_run=is_dry_run,
            log_comment=comment,
        )
        logger.info(
            f"  ✅ Closed position {position.position_id} during update check | P&L: ${pnl:.2f}"
        )
        return True

    async def _sync_mt5_only_positions_to_db(
        self, db_open_positions: list, mt5_positions: list, is_dry_run: bool
    ) -> None:
        """Import positions that exist in MT5 but not in our database.

        Handles cases where positions exist in MT5 but were skipped during
        bot startup (e.g., invalid data, schema migration issues). Only syncs
        positions for symbols enabled in self.bot.symbols.
        """
        # Collect tickets already tracked in DB
        db_tickets = {
            getattr(p, "ticket", None) or (p.metadata or {}).get("ticket")
            for p in db_open_positions
        }
        db_tickets.discard(None)
        db_tickets.discard(0)

        for mt5_pos in mt5_positions:
            mt5_ticket = mt5_pos.get("ticket")
            if not mt5_ticket or mt5_ticket in db_tickets:
                continue

            broker_symbol = mt5_pos.get("symbol", "")
            universal_symbol = self.bot._broker_to_universal_symbol(broker_symbol)

            # Skip if symbol is not in our watchlist
            if universal_symbol not in self.bot.symbols:
                continue

            logger.info(f"  🔄 Syncing MT5 position {mt5_ticket} ({broker_symbol}) to database...")
            try:
                position = self._build_position_from_mt5(universal_symbol, mt5_pos)
                self.bot.position_manager.update_position(
                    position.position_id, position.current_price
                )
                await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)
                logger.info(
                    f"  ✅ Synced MT5 position {mt5_ticket} ({universal_symbol}) to database"
                )
            except Exception as e:
                logger.error(f"  ❌ Failed to sync MT5 position {mt5_ticket}: {e}", exc_info=True)

    def _build_position_from_mt5(self, universal_symbol: str, mt5_pos: dict) -> "Position":
        """Construct a Position from MT5 position dict for DB sync."""
        from trading_worker.position.position_models import Position

        position_type = PositionType.BUY if mt5_pos.get("type", 0) == 0 else PositionType.SELL
        entry_price = mt5_pos.get("price_open", 0)
        current_price = mt5_pos.get("price_current", entry_price)
        sl = mt5_pos.get("sl", 0)
        tp = mt5_pos.get("tp", 0)
        volume = mt5_pos.get("volume", 0)
        mt5_ticket = mt5_pos.get("ticket")

        pip_calc = PipCalculator()
        pip_size = pip_calc.get_pip_size(universal_symbol)
        pip_value_per_lot = (
            pip_calc.calculate_pip_value(universal_symbol, 1.0) / pip_size if pip_size > 0 else 10.0
        )

        # Provide safe SL/TP defaults if MT5 returns 0 (rare but possible)
        safe_sl = (
            sl
            if sl > 0
            else (entry_price - 0.001 if position_type == PositionType.BUY else entry_price + 0.001)
        )
        safe_tp = (
            tp
            if tp > 0
            else (entry_price + 0.002 if position_type == PositionType.BUY else entry_price - 0.002)
        )

        position = Position(
            position_id=f"pos_{mt5_ticket}",
            symbol=universal_symbol,
            position_type=position_type,
            entry_price=entry_price,
            stop_loss=safe_sl,
            take_profit=safe_tp,
            volume=volume,
            pip_size=pip_size,
            pip_value_per_lot=pip_value_per_lot,
            status=PositionStatus.OPEN,
            open_time=(
                datetime.fromtimestamp(mt5_pos.get("time", 0))
                if mt5_pos.get("time")
                else datetime.now()
            ),
            current_price=current_price,
            metadata={"ticket": mt5_ticket, "synced_from_mt5": True},
        )
        position.ticket = mt5_ticket
        return position

    async def _estimate_close_pnl(self, position) -> tuple[float, float]:
        """Estimate close price + P&L for a position when MT5 deal history unavailable.

        Used when we know the position was closed (e.g., not in MT5) but have no
        ticket to look up the actual deal. Uses current market price as best estimate.

        Returns:
            (close_price, estimated_pnl) tuple.
        """
        current_price = await self.bot._get_current_price(position.symbol)
        close_price = current_price or position.current_price or position.entry_price

        pip_calc = PipCalculator()
        pips = pip_calc.calculate_pips(
            symbol=position.symbol,
            entry_price=position.entry_price,
            current_price=close_price,
            position_type=position.position_type.value,
        )
        pnl = pips * position.pip_value_per_lot * position.volume
        return close_price, pnl

    def _resolve_mt5_deal_details(
        self, ticket: int, fallback_price: float
    ) -> tuple[float, float, str, int | None]:
        """Fetch close price + P&L + MT5 reason from MT5 deal history.

        Returns:
            (close_price, pnl, comment, mt5_deal_reason) tuple.
            mt5_deal_reason is the MT5 DEAL_REASON_* code (int) or None if
            deal history is unavailable.
        """
        deal = self.bot.mt5.get_history_deal(ticket)
        if not deal:
            logger.warning(
                f"  ⚠️ No deal history found for ticket {ticket} - using estimated close"
            )
            return fallback_price, 0.0, "Closed in MT5", None

        close_price = deal.get("price", fallback_price)
        pnl = deal.get("profit", 0.0) + deal.get("swap", 0.0) + deal.get("commission", 0.0)
        comment = f"MT5 History: {deal.get('comment', '')}"
        mt5_reason = deal.get("reason")
        logger.debug(
            f"  📝 Deal found: Price {close_price:.5f}, P&L ${pnl:.2f}, " f"MT5 reason={mt5_reason}"
        )
        return close_price, pnl, comment, mt5_reason

    async def _finalize_closed_position(
        self,
        position,
        close_price: float,
        pnl: float,
        reason: CloseReason,
        is_dry_run: bool,
        log_comment: str | None = None,
        authoritative_pnl: bool = False,
    ) -> None:
        """Common cleanup after closing a position: save, update balance, unregister exposure.

        Used by all position-close paths (orphaned, MT5-closed-with-ticket,
        MT5-closed-no-ticket, closed-during-update) to ensure consistent state updates.

        Args:
            position: Position that was just closed
            close_price: Price at which position was closed
            pnl: Realized P&L in USD (0 if unknown)
            reason: Canonical CloseReason enum value (recorded to DB)
            is_dry_run: Skip DB saves when True
            log_comment: Optional extra context for logging (e.g., MT5 deal comment)
            authoritative_pnl: True when ``pnl`` is the broker's actual realized
                P&L (from MT5 deal history, incl. swap/commission). When set, it
                overrides the pip-recomputed P&L from PositionTracker so the
                persisted realized_pnl_usd / is_winner / exit_type reflect the
                broker result rather than a price-based approximation.
        """
        # Close in position_manager state (PositionTracker computes a pip-based
        # P&L + exit_type from close_price).
        result = self.bot.position_manager.close_position(
            position.position_id, close_price, reason.value
        )
        if result:
            result["pnl_usd"] = pnl

        # Prefer the broker's authoritative realized P&L for the persisted
        # outcome. close_position mutates the same Position instance, so this
        # override lands in the row saved below.
        if authoritative_pnl:
            position.realized_pnl_usd = pnl
            position.is_winner = pnl > 0
            position.exit_type = classify_exit_type(pnl)

        # Persist to DB
        await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)

        # Update session aggregations
        await self._update_session_on_position_close(position, result)

        if log_comment:
            logger.debug(f"  📝 Close context for {position.position_id}: {log_comment}")

        # Update portfolio balance with realized P&L
        if self.bot.portfolio_risk and pnl:
            self.bot.portfolio_risk.update_balance(self.bot.portfolio_risk.current_balance + pnl)

        # Release exposure slot
        if self.bot.exposure_manager:
            asset_class = self.bot._get_asset_class(position.symbol)
            self.bot.exposure_manager.unregister_position(
                position.symbol, asset_class, position.volume
            )

    async def manage_positions(self):
        """Update and manage all open positions."""
        try:
            if not self.bot.position_manager:
                return

            # Get current prices for all symbols with open positions
            open_positions = self.bot.position_manager.get_open_positions()
            if not open_positions:
                return

            # --- POSITION RECONCILIATION ---
            # Check if positions still exist in MT5 (only for live trading)
            is_dry_run = self.bot.config.get("trading", {}).get(
                "dry_run", False
            )  # Default to False for live trading
            if not is_dry_run and self.bot.mt5 and self.bot.mt5.is_connected():
                logger.debug(f"  🔍 Reconciliating {len(open_positions)} positions with MT5...")
                mt5_positions = self.bot.mt5.get_positions()
                mt5_tickets = {p["ticket"] for p in mt5_positions}
                logger.debug(f"  📊 MT5 has {len(mt5_tickets)} open positions")

                for position in open_positions:
                    # Get ticket from position object or metadata
                    ticket = getattr(position, "ticket", None)
                    if not ticket and position.metadata:
                        ticket = position.metadata.get("ticket")
                        if ticket:
                            position.ticket = int(ticket)  # Set to object for future use

                    # Fallback: Try to find ticket from MT5 by symbol (last resort)
                    if not ticket:
                        logger.debug(
                            f"  ⚠️ Position {position.position_id} has no ticket - trying MT5 lookup"
                        )
                        # Convert to broker symbol
                        broker_symbol = position.symbol
                        if self.bot.symbol_mapper:
                            try:
                                broker_symbol = self.bot.symbol_mapper.convert_to_broker_symbol(
                                    position.symbol, self.bot.active_broker
                                )
                            except Exception:
                                pass

                        # Find position in MT5 by symbol and entry price (rough match)
                        mt5_positions_by_symbol = [
                            p for p in mt5_positions if p.get("symbol") == broker_symbol
                        ]
                        if mt5_positions_by_symbol:
                            # Try to match by entry price (within 0.1% tolerance)
                            for mt5_pos in mt5_positions_by_symbol:
                                mt5_entry = mt5_pos.get("price_open", 0)
                                if (
                                    abs(mt5_entry - position.entry_price) / position.entry_price
                                    < 0.001
                                ):
                                    ticket = mt5_pos.get("ticket")
                                    position.ticket = ticket
                                    # Save ticket to metadata for future
                                    if not position.metadata:
                                        position.metadata = {}
                                    position.metadata["ticket"] = ticket
                                    logger.info(
                                        f"  🎫 Found ticket {ticket} for {position.position_id} via MT5 lookup"
                                    )
                                    break

                    # CRITICAL: If no ticket after all lookups, position is ORPHANED → close it
                    if not ticket:
                        logger.error(
                            f"  ❌ Position {position.position_id} ({position.symbol}) has NO TICKET "
                            f"after all lookup attempts - CLOSING as ORPHANED position."
                        )
                        # Resolve close price (current market, fallback to entry)
                        current_price = await self.bot._get_current_price(position.symbol)
                        close_price = current_price if current_price else position.entry_price
                        if not current_price:
                            logger.warning(
                                f"  ⚠️ Could not get current price for {position.symbol}, "
                                f"using entry price {close_price:.5f} for closing"
                            )
                        await self._finalize_closed_position(
                            position,
                            close_price=close_price,
                            pnl=0.0,
                            reason=CloseReason.ORPHANED,
                            is_dry_run=is_dry_run,
                            log_comment="Orphaned: no ticket found after all lookups",
                        )
                        logger.info(
                            f"  🚫 Closed orphaned position {position.position_id} at {close_price:.5f}"
                        )
                        continue

                    # Case 1: Position has ticket - check if ticket still exists in MT5
                    if ticket:
                        if ticket in mt5_tickets:
                            continue  # Still open in MT5

                        # Ticket no longer in MT5 → was closed externally
                        logger.info(
                            f"  👻 Position {position.position_id} (Ticket {ticket}) "
                            f"not found in MT5 - Assuming CLOSED"
                        )
                        close_price, pnl, comment, mt5_reason = self._resolve_mt5_deal_details(
                            ticket, position.entry_price
                        )
                        reason = resolve_close_reason(position, mt5_reason)
                        await self._finalize_closed_position(
                            position,
                            close_price=close_price,
                            pnl=pnl,
                            reason=reason,
                            is_dry_run=is_dry_run,
                            log_comment=comment,
                            # MT5 deal P&L is the broker's actual result.
                            authoritative_pnl=mt5_reason is not None,
                        )
                        logger.info(f"  ✅ Synced Close: {position.position_id} | P&L: ${pnl:.2f}")
                        continue
                    # Case 2: Position has NO ticket - check if symbol exists in MT5
                    broker_symbol = self.bot._convert_to_broker_symbol_safe(position.symbol)
                    mt5_positions_by_symbol = [
                        p for p in mt5_positions if p.get("symbol") == broker_symbol
                    ]

                    if mt5_positions_by_symbol:
                        # Symbol has MT5 position(s) but we couldn't link by ticket - manual review needed
                        logger.warning(
                            f"  ⚠️ Position {position.position_id} has no ticket but symbol "
                            f"{broker_symbol} exists in MT5 - cannot reconcile. "
                            f"Please check manually or add ticket to metadata."
                        )
                        continue

                    # No position in MT5 for this symbol - assume closed externally
                    logger.info(
                        f"  👻 Position {position.position_id} ({position.symbol}) not found in MT5 "
                        f"(no ticket, no matching symbol) - Assuming CLOSED"
                    )
                    close_price, pnl = await self._estimate_close_pnl(position)
                    await self._finalize_closed_position(
                        position,
                        close_price=close_price,
                        pnl=pnl,
                        reason=CloseReason.MT5_MISSING,
                        is_dry_run=is_dry_run,
                        log_comment="No ticket and symbol absent from MT5",
                    )
                    logger.info(
                        f"  ✅ Synced Close (no ticket): {position.position_id} | "
                        f"P&L: ${pnl:.2f} | Close Price: {close_price:.5f}"
                    )
                    continue
                else:
                    logger.debug(f"  ✅ All {len(open_positions)} positions still open in MT5")

                # Sync MT5 positions that aren't in our DB (e.g., skipped during load)
                await self._sync_mt5_only_positions_to_db(open_positions, mt5_positions, is_dry_run)

            # Update positions with current prices
            # CRITICAL: Re-fetch open positions after reconciliation to exclude closed ones
            # This ensures positions closed during sync are not processed in the update loop
            open_positions = self.bot.position_manager.get_open_positions()
            logger.debug(
                f"  📊 Updating {len(open_positions)} open positions with current prices "
                f"(after sync reconciliation)..."
            )

            for position in open_positions:
                try:
                    await self._update_position_and_run_automation(position, is_dry_run)
                except Exception as e:
                    logger.error(
                        f"Error updating position {position.position_id}: {e}", exc_info=True
                    )

            # Check for SL/TP hits and close positions
            await self._check_position_closure()

        except Exception as e:
            logger.error(f"Error managing positions: {e}")

    async def _check_position_automation(self, position):
        """Check and apply automation features (breakeven, trailing, partial close) for a position."""
        try:
            is_dry_run = self.bot.config.get("trading", {}).get("dry_run", False)

            # Pre-flight checks (open status, MT5 verification, required data)
            if not self._automation_preflight_passed(position, is_dry_run):
                return

            logger.debug(
                f"Checking automation for {position.position_id} ({position.symbol}): "
                f"profit={position.current_profit_pips:.1f} pips, "
                f"price={position.current_price}, "
                f"status={position.status.value}, "
                f"entry={position.entry_price:.5f}, "
                f"sl={position.stop_loss:.5f}"
            )

            await self._handle_breakeven_automation(position, is_dry_run)

            # Trailing stop (activation + update). Returns True if caller should skip
            # remaining automation (preserves original early-return behavior on edge cases)
            if await self._handle_trailing_automation(position, is_dry_run):
                return

            await self._handle_partial_close_automation(position, is_dry_run)

        except Exception as e:
            logger.error(f"Error checking automation for position {position.position_id}: {e}")

    async def _handle_trailing_automation(self, position, is_dry_run: bool) -> bool:
        """Activate trailing stop on threshold, then update SL as price moves.

        Returns:
            True if caller should skip remaining automation (preserves original
            early-return semantics on bad pip_size, suspicious movement, or
            dry-run after update). False to continue normal flow.
        """
        # 1. Activation check (first time trailing reaches threshold)
        await self._activate_trailing_if_needed(position, is_dry_run)

        # 2. Update check (after activation, SL trails price)
        if not self.bot.trailing_manager.should_update_trailing_stop(position):
            return False

        old_sl = position.stop_loss
        new_sl = self.bot.trailing_manager.update_trailing_stop(position)
        logger.debug(
            f"  Trailing update check for {position.position_id}: "
            f"should_update=True, profit={position.current_profit_pips:.1f} pips, "
            f"current_price={position.current_price:.5f}, current_sl={old_sl:.5f}"
        )

        if not (new_sl and new_sl != old_sl):
            logger.debug(
                f"  ℹ️ Trailing stop unchanged for {position.position_id} (SL: {old_sl:.5f})"
            )
            return False

        # Sanity check: invalid pip_size makes movement calculation impossible
        if position.pip_size <= 0:
            logger.error(
                f"  ❌ Invalid pip_size {position.pip_size} for {position.position_id} "
                f"({position.symbol}) - cannot calculate movement"
            )
            return True  # Skip partial close too (orig early-return semantics)

        # Sanity check: movement should be within reasonable bounds
        sl_movement_pips = abs(new_sl - old_sl) / position.pip_size
        asset_class = self.bot._get_asset_class(position.symbol)
        max_allowed = self.bot._MAX_TRAILING_MOVEMENT_PIPS.get(asset_class, 1000.0)

        if sl_movement_pips > max_allowed:
            logger.error(
                f"  ❌ SUSPICIOUS TRAILING MOVEMENT: {position.position_id} "
                f"({position.symbol})\n"
                f"     SL: {old_sl:.5f} → {new_sl:.5f}\n"
                f"     Movement: {sl_movement_pips:.1f} pips (max allowed: {max_allowed:.1f})\n"
                f"     pip_size: {position.pip_size}, current_price: {position.current_price}\n"
                f"     This suggests incorrect old_sl or pip_size - skipping notification"
            )
            await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)
            return True  # Skip partial close too (orig early-return semantics)

        # Sync new SL with MT5 (live only)
        mt5_modified = False
        if not is_dry_run and self.bot.mt5 and self.bot.mt5.is_connected():
            broker_symbol = self.bot._convert_to_broker_symbol_safe(position.symbol)
            ticket = self._resolve_mt5_ticket(position, broker_symbol)

            if ticket:
                res = self.bot.mt5.modify_position(
                    ticket=ticket, sl=new_sl, tp=position.take_profit
                )
                if res.get("success") and res.get("modified"):
                    mt5_modified = True
                    logger.info(f"  ✅ MT5 Trailing SL Updated: Ticket {ticket} -> {new_sl:.5f}")
                elif res.get("success"):
                    logger.debug(
                        f"  ℹ️ MT5 Trailing SL already at {new_sl:.5f} (no changes needed)"
                    )
                else:
                    logger.warning(f"  ⚠️ MT5 Trailing SL Update Failed: {res.get('message')}")
            else:
                logger.warning(
                    f"  ⚠️ No ticket found for {position.position_id} - cannot update MT5"
                )

        # Always save to DB even if MT5 didn't modify (keeps local state consistent)
        logger.info(f"  🔄 TRAILING: {position.position_id} SL moved to {new_sl:.5f}")
        await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)
        logger.info(f"  💾 Trailing SL saved to database: {new_sl:.5f}")

        # Dry-run: skip notifications + skip partial close (preserves original behavior)
        if is_dry_run:
            logger.debug(
                f"  🧪 Dry-run mode: Skipping trailing stop notification for "
                f"{position.position_id}"
            )
            return True  # Skip partial close (orig early-return semantics)

        # Live trading: notify only if MT5 actually modified
        await self._notify_trailing_update(position, old_sl, new_sl, sl_movement_pips, mt5_modified)
        return False

    async def _activate_trailing_if_needed(self, position, is_dry_run: bool) -> None:
        """Activate trailing stop tracking once profit threshold reached (once per position)."""
        ts_should_activate = self.bot.trailing_manager.should_activate_trailing(position)
        logger.debug(
            f"  Trailing activation check for {position.position_id}: "
            f"should_activate={ts_should_activate}, "
            f"profit={position.current_profit_pips:.1f} pips, "
            f"already_active={position.position_id in self.bot.trailing_manager.trailing_active}"
        )
        if not ts_should_activate:
            return

        self.bot.trailing_manager.activate_trailing(position)
        logger.info(
            f"  🎯 TRAILING ACTIVATED: {position.position_id} at "
            f"{position.current_profit_pips:.1f} pips"
        )
        await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)

        if not is_dry_run and self.bot.notification_manager:
            await self.bot.notification_manager.send_message(
                f"🎯 **TRAILING STOP ACTIVATED**\n"
                f"📊 Symbol: `{position.symbol}`\n"
                f"🆔 Position: `{position.position_id}`\n"
                f"💰 Profit: `{position.current_profit_pips:.1f} pips`\n"
                f"🛑 SL: `{position.stop_loss:.5f}`",
                level=NotificationLevel.INFO,
                sound=False,
            )

    async def _notify_trailing_update(
        self,
        position,
        old_sl: float,
        new_sl: float,
        sl_movement_pips: float,
        mt5_modified: bool,
    ) -> None:
        """Send trailing-stop-updated notification (live mode only).

        Only notifies if MT5 modification succeeded - prevents false "updated"
        alerts when MT5 sync actually failed.
        """
        if not mt5_modified:
            if self.bot.mt5 and self.bot.mt5.is_connected():
                logger.warning(
                    f"  ⚠️ Not sending notification for {position.position_id}: "
                    f"MT5 update failed or no ticket found"
                )
            return

        if not self.bot.notification_manager:
            return

        try:
            await self.bot.notification_manager.send_message(
                f"🔄 **TRAILING STOP UPDATED**\n"
                f"📊 Symbol: `{position.symbol}`\n"
                f"🆔 Position: `{position.position_id}`\n"
                f"🛑 SL: `{old_sl:.5f}` → `{new_sl:.5f}`\n"
                f"📈 Movement: `{sl_movement_pips:.1f} pips`\n"
                f"💰 Profit: `{position.current_profit_pips:.1f} pips`\n"
                f"💵 P&L: `{position.current_pnl_usd:.2f} {self.bot.account_currency_unit}`\n"
                f"🔧 Status: ✅ MT5 Updated",
                level=NotificationLevel.INFO,
                sound=False,
            )
            logger.debug(f"  📱 Trailing stop notification sent for {position.position_id}")
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to send trailing stop notification: {e}")

    async def _handle_partial_close_automation(self, position, is_dry_run: bool) -> None:
        """Take partial profit at predefined volume levels (e.g., 25% at TP1, 50% at TP2).

        Side effects:
            - Closes partial volume on MT5 (live trading only)
            - Saves updated position state to DB
            - Sends Telegram notification (live only)

        Silently skips if volume is too small for partial close (expected
        edge case for small positions, not an error).
        """
        if not self.bot.partial_manager.should_close_partial(position):
            return

        current_price = await self.bot._get_current_price(position.symbol)

        try:
            result = self.bot.partial_manager.execute_partial_close(position, current_price)
        except ValueError as e:
            # Volume too small for partial close - expected for small positions
            logger.debug(f"  ⏭️ Skipping partial close for {position.position_id}: {e}")
            return
        except Exception as e:
            logger.error(f"  ❌ Error executing partial close for {position.position_id}: {e}")
            return

        if not (result and result.get("closed_volume", 0) > 0):
            return

        closed_volume = result["closed_volume"]

        # Sync partial close with MT5 (live only)
        if not is_dry_run and self.bot.mt5 and self.bot.mt5.is_connected():
            broker_symbol = self.bot._convert_to_broker_symbol_safe(position.symbol)
            ticket = self._resolve_mt5_ticket(position, broker_symbol)

            if ticket:
                mt5_result = self.bot.mt5.close_position(
                    ticket=ticket,
                    volume=closed_volume,
                    comment=f"Partial Close {position.position_id}",
                )
                if mt5_result:
                    logger.info(
                        f"  ✅ MT5 Partial Close: Ticket {ticket}, " f"Volume {closed_volume:.3f}"
                    )
                else:
                    logger.error(
                        f"  ❌ MT5 Partial Close Failed: Ticket {ticket}, "
                        f"Volume {closed_volume:.3f}"
                    )
            else:
                logger.warning(
                    f"  ⚠️ Cannot partial close: No ticket found for {position.position_id}"
                )

        logger.info(
            f"  🔄 PARTIAL CLOSE: {position.position_id} "
            f"Closed {closed_volume:.3f} at {current_price:.5f} "
            f"P&L: {result['profit_usd']:.2f} {self.bot.account_currency_unit}"
        )
        await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)

        # Send notification (live only)
        if not is_dry_run and self.bot.notification_manager:
            await self.bot.notification_manager.send_message(
                f"💰 **PARTIAL PROFIT TAKEN**\n"
                f"🆔 `{position.position_id}`\n"
                f"📊 Closed: `{closed_volume:.3f}` lots\n"
                f"💵 Profit: **{result['profit_usd']:.2f} {self.bot.account_currency_unit}**",
                level=NotificationLevel.SUCCESS,
            )

    async def _handle_breakeven_automation(self, position, is_dry_run: bool) -> None:
        """Move SL to breakeven once profit threshold reached.

        Side effects:
            - Modifies SL via MT5 modify_position (live trading)
            - Saves position to DB
            - Sends Telegram notification (live only, once - deduplicates re-triggers)
        """
        be_should_move = self.bot.breakeven_manager.should_move_to_breakeven(position)
        logger.debug(
            f"  Breakeven check for {position.position_id}: should_move={be_should_move}, "
            f"profit={position.current_profit_pips:.1f} pips"
        )

        if not be_should_move:
            return

        new_sl = self.bot.breakeven_manager.move_to_breakeven(position)
        if not new_sl:
            return

        # MT5 modification only for live trading
        if not is_dry_run and self.bot.mt5 and self.bot.mt5.is_connected():
            broker_symbol = self.bot._convert_to_broker_symbol_safe(position.symbol)
            ticket = self._resolve_mt5_ticket(position, broker_symbol)
            mt5_modified = False
            res: dict = {}
            if ticket:
                logger.debug(
                    f"  🔧 Modifying MT5 position {ticket}: "
                    f"SL={new_sl:.5f}, TP={position.take_profit:.5f}"
                )
                res = self.bot.mt5.modify_position(
                    ticket=ticket, sl=new_sl, tp=position.take_profit
                )
                if res.get("success"):
                    if res.get("modified"):
                        mt5_modified = True
                        logger.info(f"  ✅ MT5 SL Modified: Ticket {ticket} -> {new_sl:.5f}")
                    else:
                        logger.debug(f"  ℹ️ MT5 SL already at {new_sl:.5f} (no changes needed)")
                else:
                    logger.warning(
                        f"  ⚠️ MT5 SL Modification Failed for ticket {ticket} "
                        f"({broker_symbol}): {res.get('message')}"
                    )
            else:
                logger.error(
                    f"  ❌ Cannot modify MT5 position: No ticket found for "
                    f"{position.position_id} ({broker_symbol})"
                )

            # Check if already at breakeven (avoid duplicate notifications)
            is_already_at_breakeven = self.bot.breakeven_manager.is_at_breakeven(
                position.position_id
            )

            # Save + notify based on state
            if mt5_modified and not is_already_at_breakeven:
                logger.info(f"  🔄 BREAKEVEN: {position.position_id} SL moved to {new_sl:.5f}")
                await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)
                logger.info(f"  💾 Breakeven SL saved to database: {new_sl:.5f}")
                if self.bot.notification_manager:
                    await self.bot.notification_manager.send_message(
                        f"🛡️ **BREAKEVEN SECURED**\n"
                        f"📊 Symbol: `{position.symbol}`\n"
                        f"🆔 Position: `{position.position_id}`\n"
                        f"🛑 SL Moved: `{new_sl:.5f}`\n"
                        f"🔒 Risk Free",
                        level=NotificationLevel.INFO,
                        sound=False,
                    )
            elif mt5_modified:
                # Already at breakeven (duplicate check)
                logger.debug(
                    f"  ℹ️ Breakeven already set for {position.position_id}, skipping notification"
                )
                await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)
                logger.debug("  💾 Position saved to database (already at breakeven)")
            else:
                # MT5 not modified (failed or already set)
                await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)
                logger.debug(
                    f"  💾 Position saved (MT5 not modified: "
                    f"{res.get('message') if ticket else 'no ticket'})"
                )
        elif is_dry_run:
            # Dry-run: save to DB but skip MT5 + notification
            logger.info(
                f"  🔄 BREAKEVEN (DRY-RUN): {position.position_id} " f"SL moved to {new_sl:.5f}"
            )
            await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)
            logger.info("  💾 Breakeven SL saved to database (dry-run, no notification)")

    async def _check_position_closure(self):
        """Check for stop loss and take profit hits."""
        try:
            if not self.bot.data_manager:
                return

            # Get dry-run mode
            is_dry_run = self.bot.config.get("trading", {}).get("dry_run", False)

            open_positions = self.bot.position_manager.get_open_positions()
            for position in open_positions:
                try:
                    # Get current price
                    current_price = await self.bot._get_current_price(position.symbol)
                    if current_price is None:
                        continue

                    # Update position price + tracker state so duration / P&L
                    # are fresh before the max-duration check below.
                    self.bot.position_manager.update_position(position.position_id, current_price)

                    # Max-duration auto-close (only if position is in profit;
                    # losing positions ride until SL/TP per design — see
                    # position_manager._check_max_duration).
                    if self.bot.position_manager._check_max_duration(position, current_price):
                        await self.bot._finalize_max_duration_close(position, is_dry_run)
                        continue  # Done with this position this tick

                    # Check if SL or TP is hit (price-based fallback; MT5 is authoritative)
                    should_close = False
                    tp_hit = False

                    if position.position_type == "BUY":
                        if current_price <= position.stop_loss:
                            should_close = True
                        elif current_price >= position.take_profit:
                            should_close, tp_hit = True, True
                    else:  # SELL
                        if current_price >= position.stop_loss:
                            should_close = True
                        elif current_price <= position.take_profit:
                            should_close, tp_hit = True, True

                    if should_close:
                        # Disambiguate SL hit via position flags (same logic as resolver)
                        if tp_hit:
                            close_reason = CloseReason.TAKE_PROFIT
                        elif position.trailing_activated:
                            close_reason = CloseReason.TRAILING_STOP
                        elif position.breakeven_activated:
                            close_reason = CloseReason.BREAKEVEN_STOP
                        else:
                            close_reason = CloseReason.STOP_LOSS

                        # Close position
                        result = self.bot.position_manager.close_position(
                            position.position_id, current_price, close_reason.value
                        )

                        if result:
                            # Unregister from exposure manager
                            asset_class = self.bot._get_asset_class(position.symbol)
                            self.bot.exposure_manager.unregister_position(
                                position.symbol, asset_class, position.volume
                            )

                            # Update portfolio risk
                            self.bot.portfolio_risk.update_balance(
                                self.bot.portfolio_risk.current_balance + result["pnl_usd"]
                            )

                            # Save closed state to database
                            await self.bot.position_manager.save_position(
                                position, is_dry_run=is_dry_run
                            )

                            # Update session aggregations
                            await self._update_session_on_position_close(position, result)

                            logger.info(
                                f"  ✅ POSITION CLOSED: {position.position_id} | "
                                f"{close_reason.value} | "
                                f"P&L: {result['pnl_usd']:.2f} {self.bot.account_currency_unit} | "
                                f"Pips: {result['pips']:.1f}"
                            )

                            # Determine emoji based on profit
                            pnl_emoji = "💰" if result["pnl_usd"] > 0 else "💸"

                            await self.bot.notification_manager.send_message(
                                f"{pnl_emoji} **POSITION CLOSED**\n"
                                f"🆔 `{position.position_id}`\n"
                                f"📝 Reason: `{close_reason.value}`\n"
                                f"💵 P&L: **{result['pnl_usd']:.2f} {self.bot.account_currency_unit}**\n"
                                f"📏 Pips: `{result['pips']:.1f}`",
                                level=(
                                    NotificationLevel.SUCCESS
                                    if result["pnl_usd"] > 0
                                    else NotificationLevel.WARNING
                                ),
                            )

                except Exception as e:
                    logger.error(f"Error checking closure for position {position.position_id}: {e}")

        except Exception as e:
            logger.error(f"Error checking position closures: {e}")
