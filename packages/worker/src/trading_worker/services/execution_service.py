"""Execution service — owns the signal → live order pipeline.

Extracted from TradingBot to keep main.py focused on orchestration.
Holds a back-reference to the bot for access to shared state (mt5,
position_manager, portfolio_risk, etc.).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from trading_core.utils.logger import get_logger
from trading_core.utils.market_session import derive_market_session

from trading_worker.position.pip_calculator import PipCalculator
from trading_worker.utils.notification_manager import NotificationLevel

if TYPE_CHECKING:  # pragma: no cover
    from trading_worker.main import TradingBot

logger = get_logger(__name__)


class ExecutionService:
    """Signal execution pipeline: validate → size → place order → open position."""

    # MT5 error codes that don't warrant user notification (expected/transient)
    _SILENT_MT5_ERROR_CODES: frozenset[int] = frozenset(
        {
            10018,  # Market is closed
            10035,  # Market is closed (alt code)
        }
    )

    def __init__(self, bot: TradingBot):
        self.bot = bot

    # ──────────────────────────────────────────────────────────────────
    # Entry point
    # ──────────────────────────────────────────────────────────────────

    async def execute_signal(self, signal) -> None:
        """Execute a trading signal by creating and managing a position."""
        try:
            logger.info(
                f"  📍 SIGNAL: {signal.direction.value} {signal.symbol} @ {signal.entry_price:.5f} | "
                f"SL: {signal.stop_loss:.5f} | TP: {signal.take_profit:.5f} | "
                f"R:R: {signal.risk_reward_ratio:.2f} | "
                f"Confluence: {signal.confluence_score:.1f}%"
            )

            for strategy_name, score in signal.strategy_scores.items():
                logger.debug(f"    └─ {strategy_name}: {score:.1f}")

            is_dry_run = self.bot.config.get("trading", {}).get("dry_run", False)

            # Step 1: Skip if duplicate position exists (database or MT5)
            if self.has_duplicate_position(signal, is_dry_run):
                return

            # Step 2: Exposure limits
            if not await self.check_exposure_limits(signal):
                logger.warning(f"  ❌ Signal {signal.symbol} failed exposure validation")
                return

            # Step 3: Risk validation
            if not await self.validate_signal_risk(signal):
                logger.warning(f"  ❌ Signal {signal.symbol} failed risk validation")
                await self.bot.notification_manager.send_message(
                    f"🛡️ **SIGNAL REJECTED (RISK)**\n"
                    f"💱 `{signal.symbol}`\n"
                    f"Reason: Risk Validation Failed\n"
                    f"(Check logs for details)",
                    level=NotificationLevel.WARNING,
                )
                return

            # Step 4: Calculate position size
            position_size = await self.calculate_position_size(signal)
            if position_size <= 0:
                logger.warning(f"  ❌ Invalid position size for {signal.symbol}")
                return

            # Step 5: Execute order on MT5 (if not dry-run)
            real_entry_price = signal.entry_price
            order_result = None
            if not is_dry_run:
                order_result = await self.execute_mt5_order(signal, position_size)
                if order_result is None:
                    return  # MT5 not connected or rejected (notifications already sent)

                if "price" in order_result:
                    real_entry_price = float(order_result["price"])
                    logger.info(
                        f"  📝 Execution Price Updated: "
                        f"{signal.entry_price:.5f} -> {real_entry_price:.5f}"
                    )

                await self.bot.notification_manager.send_message(
                    self._format_order_notification(
                        signal,
                        position_size,
                        real_entry_price,
                        ticket=order_result.get("order"),
                        is_dry_run=False,
                    ),
                    level=NotificationLevel.SUCCESS,
                )
            else:
                logger.info(f"  ⚠️ Dry-Run Mode: Skipping MT5 execution for {signal.symbol}")
                await self.bot.notification_manager.send_message(
                    self._format_order_notification(
                        signal,
                        position_size,
                        signal.entry_price,
                        ticket=None,
                        is_dry_run=True,
                    ),
                    level=NotificationLevel.INFO,
                    sound=False,
                )

            # Step 6: Create position (Update entry price with real one)
            original_signal_price = signal.entry_price
            signal.entry_price = real_entry_price
            position = self.bot.position_manager.create_position_from_signal(signal, position_size)
            signal.entry_price = original_signal_price

            # Confluence + metadata
            position.confluence_score = signal.confluence_score
            if not position.metadata:
                position.metadata = {}
            position.metadata["confluence_score"] = signal.confluence_score
            logger.debug(
                f"  📊 Confluence Score: {signal.confluence_score:.1f}% (saved to position)"
            )

            # Capture entry slippage: signal price vs actual fill price (live only)
            if not is_dry_run and original_signal_price and real_entry_price:
                pip_size = position.pip_size or 0.0001
                slippage = abs(real_entry_price - original_signal_price) / pip_size
                position.slippage_pips = slippage
                if slippage > 0.5:
                    logger.info(
                        f"  📏 Entry slippage: {slippage:.1f} pips "
                        f"(signal {original_signal_price:.5f} → fill {real_entry_price:.5f})"
                    )

            # Derive market session bucket from open_time (for time-of-day analytics)
            position.metadata["market_session"] = derive_market_session(
                position.open_time or datetime.now(UTC)
            )

            # Ticket
            if not is_dry_run and order_result:
                ticket_value = int(order_result.get("order"))
                position.ticket = ticket_value
                position.metadata["ticket"] = ticket_value
                logger.info(f"  🎫 Position Ticket: {ticket_value} (saved to position and metadata)")

            # Link to active account
            if self.bot.account_selector:
                active_account = await self.bot.account_selector.get_active_account()
                if active_account:
                    position.account_id = active_account.account_id
                    logger.debug(f"  🏦 Position linked to account: {active_account.account_id}")

            # Link to trading session
            if self.bot.current_session:
                position.session_id = self.bot.current_session.session_id
                logger.debug(
                    f"  📊 Position linked to session: {self.bot.current_session.session_id}"
                )

            # Register with exposure manager
            asset_class = self.bot._get_asset_class(signal.symbol)
            self.bot.exposure_manager.register_position(
                signal.symbol, asset_class, position_size, direction=signal.direction.value
            )

            # Open position
            self.bot.position_manager.open_position(position.position_id)
            await self.bot.position_manager.save_position(position, is_dry_run=is_dry_run)

            logger.info(
                f"  ✅ POSITION OPENED: {position.position_id} | "
                f"{position.position_type} {position.symbol} @ {position.entry_price:.5f} | "
                f"Volume: {position.volume:.2f} | "
                f"Risk: {position.risk_amount_usd:.2f} {self.bot.account_currency_unit}"
            )

        except Exception as e:
            logger.error(f"  ❌ Error executing signal {signal.symbol}: {e}")
            raise

    # ──────────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────────

    def has_duplicate_position(self, signal, is_dry_run: bool) -> bool:
        """Check if an open position already exists for this signal's symbol.

        Checks both in-memory position_manager state and live MT5 positions
        (in case DB is out of sync).
        """
        signal_symbol_norm = self.bot._normalize_symbol(signal.symbol)

        existing = [
            p
            for p in self.bot.position_manager.get_open_positions()
            if self.bot._normalize_position_symbol(p.symbol) == signal_symbol_norm
        ]
        if existing:
            logger.info(
                f"  ⏭️  Skipping signal for {signal.symbol} - already have {len(existing)} "
                f"open position(s): {[p.position_id for p in existing]} "
                f"(symbols: {[p.symbol for p in existing]})"
            )
            return True

        if not is_dry_run and self.bot.mt5 and self.bot.mt5.is_connected():
            try:
                broker_symbol = self.bot._convert_to_broker_symbol_safe(signal.symbol)
                mt5_positions = self.bot.mt5.get_positions(symbol=broker_symbol)
                if mt5_positions:
                    logger.info(
                        f"  ⏭️  Skipping signal for {signal.symbol} - found {len(mt5_positions)} "
                        f"open position(s) in MT5 (broker: {broker_symbol})"
                    )
                    return True
            except Exception as e:
                logger.debug(f"  Could not check MT5 positions for {signal.symbol}: {e}")

        return False

    async def validate_signal_risk(self, signal) -> bool:
        """Validate signal against risk management rules."""
        try:
            max_risk_amount = self.bot.portfolio_risk.calculate_max_risk_amount(
                self.bot.portfolio_risk.current_balance
            )
            can_trade, reason = self.bot.portfolio_risk.can_take_trade(max_risk_amount)
            if not can_trade:
                logger.warning(f"  Portfolio risk validation failed: {reason}")
                return False

            if self.bot.drawdown_protector.should_close_all_positions():
                logger.warning("  Drawdown protection triggered - no new positions allowed")
                return False

            return True
        except Exception as e:
            logger.error(f"  Risk validation error: {e}")
            return False

    async def check_exposure_limits(self, signal) -> bool:
        """Check if signal respects exposure limits (position limits per symbol/total)."""
        try:
            max_risk_amount = self.bot.portfolio_risk.calculate_max_risk_amount(
                self.bot.portfolio_risk.current_balance
            )
            asset_class = self.bot._get_asset_class(signal.symbol)
            can_open, reason = self.bot.exposure_manager.can_open_position(
                signal.symbol, asset_class, max_risk_amount, signal.direction.value
            )
            if not can_open:
                logger.warning(f"  Exposure validation failed: {reason}")
                return False
            return True
        except Exception as e:
            logger.error(f"  Exposure validation error: {e}")
            return False

    # ──────────────────────────────────────────────────────────────────
    # Position sizing
    # ──────────────────────────────────────────────────────────────────

    async def calculate_position_size(self, signal) -> float:
        """Calculate appropriate position size for the signal.

        Per-symbol config controls strategy:
        - use_dynamic_lot_size=false: fixed min_volume_lots
        - use_dynamic_lot_size=true (default): risk-based calculation
        """
        logger.info(f"  🔧 [LOT CALC] Starting position size calculation for {signal.symbol}...")

        try:
            # Sync balance from MT5 BEFORE calculating
            await self.bot._sync_balance_from_mt5()

            # Convert broker symbol to universal format for config lookup
            symbol_for_config = signal.symbol
            if self.bot.symbol_mapper:
                try:
                    symbol_for_config = self.bot.symbol_mapper.convert_to_universal_symbol(
                        signal.symbol
                    )
                except Exception:
                    symbol_for_config = signal.symbol.upper().strip()

            symbol_cfg = self.bot.config.get("symbols", {}).get(symbol_for_config, {})
            logger.debug(
                f"  🔍 Symbol lookup: signal.symbol={signal.symbol}, "
                f"symbol_for_config={symbol_for_config}"
            )
            logger.debug(
                f"  🔍 Symbol config found: {bool(symbol_cfg)}, "
                f"keys={list(symbol_cfg.keys()) if symbol_cfg else 'None'}"
            )

            use_dynamic = symbol_cfg.get("use_dynamic_lot_size", True)
            logger.debug(f"  🔍 use_dynamic_lot_size={use_dynamic} (from config or default True)")

            if not use_dynamic:
                fixed_lot_size = symbol_cfg.get("min_volume_lots", 0.01)
                logger.info(
                    f"  📊 {signal.symbol} FIXED lot size: {fixed_lot_size:.2f} lots (config-based)"
                )
                return fixed_lot_size

            # Dynamic mode
            logger.info(f"  📊 {signal.symbol} using DYNAMIC lot sizing mode...")
            max_risk_amount = self.bot.portfolio_risk.calculate_max_risk_amount(
                self.bot.portfolio_risk.current_balance
            )

            pip_calculator = PipCalculator()
            pip_size = pip_calculator.get_pip_size(signal.symbol)
            stop_distance_pips = signal.risk_pips / pip_size
            pip_value_per_lot = pip_calculator.calculate_pip_value(signal.symbol, 1.0)

            position_size = self.bot.portfolio_risk.calculate_position_size(
                account_balance=self.bot.portfolio_risk.current_balance,
                risk_amount_usd=max_risk_amount,
                stop_distance_pips=stop_distance_pips,
                pip_value_per_lot=pip_value_per_lot,
            )

            min_lot = symbol_cfg.get("min_volume_lots", 0.01)
            max_lot = symbol_cfg.get("max_volume_lots", 100.0)
            position_size = max(min_lot, min(position_size, max_lot))

            logger.info(
                f"  📊 Position sizing: {signal.symbol} | "
                f"Balance=${self.bot.portfolio_risk.current_balance:.2f}, "
                f"Risk=${max_risk_amount:.2f}, SL={stop_distance_pips:.1f} pips, "
                f"PipValue=${pip_value_per_lot:.2f}, Size={position_size:.2f} lots (dynamic)"
            )

            return position_size

        except Exception as e:
            logger.error(f"  Position size calculation error: {e}")
            logger.error(
                f"  Trace: symbol={signal.symbol}, "
                f"balance={self.bot.portfolio_risk.current_balance}"
            )
            symbol_cfg = self.bot.config.get("symbols", {}).get(signal.symbol, {})
            fallback_lot = symbol_cfg.get("min_volume_lots", 0.01)
            logger.info(f"  ⚠️  Using fallback lot size: {fallback_lot:.2f} lots")
            return fallback_lot

    # ──────────────────────────────────────────────────────────────────
    # MT5 order placement
    # ──────────────────────────────────────────────────────────────────

    async def execute_mt5_order(self, signal, position_size: float) -> dict | None:
        """Execute a live order on MT5 with connection check and error handling.

        Returns:
            order_result dict on success, None on connection failure or rejection.
            All failure paths log and notify before returning None.
        """
        if not self.is_mt5_ready_for_trading(signal):
            return None

        execute_symbol = self.bot._convert_to_broker_symbol_safe(signal.symbol)
        if execute_symbol != signal.symbol:
            logger.debug(f"  Converted {signal.symbol} to {execute_symbol} for execution")

        logger.info(f"  🚀 Executing LIVE order for {signal.symbol}...")

        order_result = self.bot.mt5.place_order(
            symbol=execute_symbol,
            order_type=signal.direction.value,
            volume=position_size,
            price=signal.entry_price,
            sl=signal.stop_loss,
            tp=signal.take_profit,
            comment=f"Signal {signal.signal_id}",
        )

        if order_result.get("success") is False:
            await self.notify_order_failed(signal, position_size, order_result)
            return None

        logger.info(f"  ✅ MT5 Order Executed: Ticket {order_result.get('order')}")
        return order_result

    def is_mt5_ready_for_trading(self, signal) -> bool:
        """Check MT5 is connected and ready. Sends notification + returns False on failure."""
        mt5_status = self.diagnose_mt5_connection()
        if self.bot.mt5 and self.bot.mt5.is_connected():
            logger.debug("  ✅ MT5 connection verified: ready for trade execution")
            return True

        logger.warning(f"  ⚠️ Cannot execute trade: MT5 not connected ({mt5_status})")
        if self.bot.notification_manager:
            try:
                asyncio.create_task(
                    self.bot.notification_manager.send_message(
                        f"❌ **MT5 Connection Error**\n"
                        f"📊 Symbol: `{signal.symbol}`\n"
                        f"📈 Direction: `{signal.direction.value}`\n"
                        f"💰 Entry: `{signal.entry_price:.5f}`\n"
                        f"🛑 SL: `{signal.stop_loss:.5f}`\n"
                        f"🎯 TP: `{signal.take_profit:.5f}`\n"
                        f"⚠️ **Error**: MT5 is not connected. Trade execution skipped.",
                        level=NotificationLevel.ERROR,
                    )
                )
            except Exception as e:
                logger.warning(f"  ⚠️ Failed to send MT5 connection error notification: {e}")
        return False

    def diagnose_mt5_connection(self) -> str:
        """Return a human-readable string describing current MT5 connection state."""
        if self.bot.mt5 is None:
            return "MT5 connector is None"
        if not hasattr(self.bot.mt5, "is_connected"):
            return "MT5 connector missing is_connected method"
        if not self.bot.mt5.is_connected():
            try:
                health = (
                    self.bot.mt5.health_check() if hasattr(self.bot.mt5, "health_check") else {}
                )
                return (
                    f"is_connected()=False, "
                    f"_is_connected={getattr(self.bot.mt5, '_is_connected', 'unknown')}, "
                    f"terminal_connected={health.get('connected', 'unknown')}, "
                    f"trade_allowed={health.get('trade_allowed', 'unknown')}"
                )
            except Exception as e:
                return f"Error checking connection: {e}"
        return "connected"

    async def notify_order_failed(self, signal, position_size: float, order_result: dict) -> None:
        """Log order failure and notify user (unless error code is silenced).

        Some errors (e.g. market closed) are expected and don't warrant
        notifications.
        """
        error_msg = order_result.get("error", "Unknown error")
        error_code = order_result.get("error_code", 0)
        error_description = order_result.get("error_description", "No description available")

        logger.error(
            f"  ❌ MT5 Order Execution Failed for {signal.symbol}: "
            f"{error_msg} (code: {error_code})"
        )

        if error_code in self._SILENT_MT5_ERROR_CODES:
            logger.debug(
                f"  🔕 Silent error code {error_code} ({error_description}) - "
                f"no notification sent"
            )
            return

        await self.bot.notification_manager.send_message(
            f"❌ **MT5 Order Failed**\n"
            f"Symbol: `{signal.symbol}`\n"
            f"Direction: `{signal.direction.value}`\n"
            f"Volume: `{position_size}`\n"
            f"Error: `{error_msg}`\n"
            f"Error Code: `{error_code}`\n"
            f"Description: `{error_description}`",
            level=NotificationLevel.ERROR,
        )

    # ──────────────────────────────────────────────────────────────────
    # Notification formatting
    # ──────────────────────────────────────────────────────────────────

    def _format_order_notification(
        self,
        signal,
        position_size: float,
        entry_price: float,
        ticket: int | None,
        is_dry_run: bool,
    ) -> str:
        """Build the Telegram message body for a placed order (live or dry-run)."""
        confluence_text = f"\n📊 Confluence: **{signal.confluence_score:.1f}%**"

        if signal.strategy_scores:
            layer_names = {
                "foundation": "S&D Zones",
                "rsi": "RSI",
                "ma": "MA",
                "trendline": "Trendline",
                "price_action": "Price Action",
                "fibonacci": "Fibonacci",
                "structure": "Structure",
                "breakout_retest": "Breakout",
            }
            active_layers = []
            for layer, score in sorted(
                signal.strategy_scores.items(), key=lambda x: x[1], reverse=True
            ):
                if score > 0:
                    layer_display = layer_names.get(layer, layer.title())
                    active_layers.append(f"{layer_display}: {score:.1f}%")
            if active_layers:
                confluence_text += f"\n   └─ {' | '.join(active_layers[:5])}"
                if len(active_layers) > 5:
                    confluence_text += f" (+{len(active_layers) - 5} more)"

        price_action_text = self._format_price_action(signal)

        if is_dry_run:
            return (
                f"⚠️ **Dry-Run Order**\n"
                f"💱 **{signal.symbol}** | **{signal.direction.value}**\n"
                f"📊 Size: `{position_size:.2f}` lots\n"
                f"📉 Price: `{entry_price:.5f}`"
                f"{confluence_text}"
                f"{price_action_text}"
            )

        return (
            f"✅ **LIVE ORDER EXECUTED**\n"
            f"🎫 Ticket: `{ticket}`\n"
            f"💱 **{signal.symbol}** | **{signal.direction.value}**\n"
            f"📊 Size: `{position_size:.2f}` lots\n"
            f"📉 Price: `{entry_price:.5f}`\n"
            f"🛑 SL: `{signal.stop_loss:.5f}`\n"
            f"🎯 TP: `{signal.take_profit:.5f}`"
            f"{confluence_text}"
            f"{price_action_text}"
        )

    def _format_price_action(self, signal) -> str:
        """Format the price-action line of an order notification."""
        if not (signal.metadata and "price_action" in signal.metadata):
            return ""

        pa_info = signal.metadata["price_action"]
        pattern_type = pa_info.get("pattern_type", "UNKNOWN")
        direction = pa_info.get("direction", "")
        confidence = pa_info.get("confidence", 0.0)
        status = pa_info.get("status", "detected")

        if status in ("detected", "neutral_pattern"):
            direction_emoji = (
                "🟢" if direction == "BULLISH" else "🔴" if direction == "BEARISH" else "⚪"
            )
            pattern_emoji = "📊"
            if "PINBAR" in pattern_type:
                pattern_emoji = "📌"
            elif "ENGULFING" in pattern_type:
                pattern_emoji = "🔄"
            elif "HARAMI" in pattern_type:
                pattern_emoji = "🔀"
            elif "MORNING_STAR" in pattern_type or "EVENING_STAR" in pattern_type:
                pattern_emoji = "⭐"
            elif "PULLBACK" in pattern_type:
                pattern_emoji = "↩️"
            elif "ORDER_BLOCK" in pattern_type:
                pattern_emoji = "📦"
            elif "LIQUIDITY_SWEEP" in pattern_type:
                pattern_emoji = "🌊"

            neutral_note = " (neutral)" if status == "neutral_pattern" else ""
            return (
                f"\n{pattern_emoji} Price Action: {direction_emoji} "
                f"**{pattern_type}** ({direction}, {confidence:.0f}%){neutral_note}"
            )
        if status == "wrong_direction":
            detected_pattern = pa_info.get("detected_pattern", "UNKNOWN")
            return f"\n⚠️ Price Action: **{detected_pattern}** (wrong direction)"
        return "\n📈 Price Action: No pattern detected"
