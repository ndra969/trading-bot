"""
Main trading bot orchestrator.

Coordinates all trading components and manages the trading loop.
"""

import asyncio
from datetime import UTC

from .connectors.data_manager import DataManager
from .connectors.mt5_connector import MT5Connector
from .connectors.symbol_mapper import SymbolMapper
from .position.automation.breakeven_manager import BreakevenManager
from .position.automation.partial_close_manager import PartialCloseManager
from .position.automation.trailing_stop_manager import TrailingStopManager
from .position.position_manager import PositionManager
from .risk.drawdown_protector import DrawdownProtector
from .risk.exposure_manager import ExposureManager
from .risk.portfolio_risk_manager import PortfolioRiskManager
from .strategies.foundation.foundation_engine import FoundationEngine
from .strategies.signal_aggregator import SignalAggregator
from .strategies.strategy_manager import StrategyManager
from .utils.logger import get_logger
from .utils.notification_manager import NotificationLevel, NotificationManager

logger = get_logger(__name__)


class TradingBot:
    """
    Main trading bot orchestrator.

    Coordinates all trading components and manages the trading loop.
    """

    def __init__(self, config):
        """
        Initialize trading bot.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.is_running = False

        # Initialize components
        self.mt5 = None
        self.data_manager = None
        self.foundation_engine = None
        self.symbol_mapper = None
        self.strategy_manager = None
        self.signal_aggregator = None
        self.notification_manager = None

        # Position and Risk Management components
        self.position_manager = None
        self.breakeven_manager = None
        self.trailing_manager = None
        self.partial_manager = None
        self.portfolio_risk = None
        self.exposure_manager = None
        self.drawdown_protector = None

        # Initialize symbol mapper for broker symbol conversion
        try:
            self.symbol_mapper = SymbolMapper()
            # Get active broker from config or use default
            self.active_broker = config.get("active_broker") or self.symbol_mapper.default_broker
            logger.info(f"Symbol mapper initialized with broker: {self.active_broker}")
        except Exception as e:
            logger.warning(f"Symbol mapper initialization failed: {e} - using symbols as-is")
            self.symbol_mapper = None
            self.active_broker = None

        # Initialize Notification Manager
        self.notification_manager = NotificationManager(self.config)

        # Trading symbols (internal/universal format)
        self.symbols: list[str] = config.get("symbols", ["EURUSD", "GBPUSD"])
        self.timeframe = config.get("timeframe", "H1")
        self.analysis_interval = config.get("analysis_interval", 300)  # 5 minutes

        logger.info(f"TradingBot initialized for symbols: {self.symbols}")

    async def start(self):
        """Start trading bot."""
        logger.info("🚀 Starting trading bot...")

        try:
            # Initialize MT5 connection (skip if already set from CLI or in mock mode)
            if self.mt5 is None:
                # In mock MT5 mode (dry-run), mt5 is intentionally None
                # Skip initialization and continue without MT5
                logger.debug("MT5 not set (mock mode) - continuing without MT5 connection")
                self.data_manager = None
            else:
                # MT5 connector provided, verify connection
                try:
                    if not self.mt5.is_connected():
                        logger.warning(
                            "MT5 connector provided but not connected - attempting connection..."
                        )
                        await self._initialize_mt5()
                    else:
                        # MT5 already connected, just create data manager if needed
                        if self.data_manager is None:
                            from .connectors.symbol_manager import SymbolManager

                            symbol_manager = SymbolManager(self.mt5)
                            self.data_manager = DataManager(self.mt5, symbol_manager)
                except Exception as e:
                    logger.warning(f"MT5 initialization failed: {e} - continuing without MT5")
                    self.data_manager = None

            # Initialize foundation strategy
            await self._initialize_foundation_strategy()

            # Initialize strategy system (manager + aggregator)
            await self._initialize_strategy_system()

            # Initialize position and risk management system
            await self._initialize_position_risk_system()

            # Start notification manager
            await self.notification_manager.start()

            # Start main trading loop
            self.is_running = True
            logger.info("✅ Trading bot started successfully")

            await self._trading_loop()

        except Exception as e:
            logger.error(f"❌ Error starting trading bot: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop trading bot."""
        logger.info("🛑 Stopping trading bot...")
        self.is_running = False

        # Stop notification manager
        if self.notification_manager:
            await self.notification_manager.stop()

        # Cleanup MT5 connection
        if self.mt5:
            try:
                # MT5Connector uses shutdown(), not disconnect()
                if hasattr(self.mt5, "shutdown"):
                    self.mt5.shutdown()
                elif hasattr(self.mt5, "disconnect"):
                    await self.mt5.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting MT5: {e}")

        logger.info("✅ Trading bot stopped")

    async def _initialize_mt5(self):
        """Initialize MT5 connection."""
        logger.info("Initializing MT5 connection...")

        # If MT5 already set (from CLI), use it
        if self.mt5 is None:
            self.mt5 = MT5Connector()
            await self.mt5.connect()

            # Verify connection
            if not await self.mt5.is_connected():
                raise ConnectionError("Failed to connect to MT5")

            # Initialize data manager (requires symbol_manager)
            from .connectors.symbol_manager import SymbolManager

            symbol_manager = SymbolManager(self.mt5)
            self.data_manager = DataManager(self.mt5, symbol_manager)
        else:
            # MT5 already initialized from CLI, just create data manager
            if self.data_manager is None:
                from .connectors.symbol_manager import SymbolManager

                symbol_manager = SymbolManager(self.mt5)
                self.data_manager = DataManager(self.mt5, symbol_manager)

        logger.info("✅ MT5 connection initialized")

    async def _initialize_foundation_strategy(self):
        """Initialize foundation strategy."""
        logger.info("Initializing foundation strategy...")

        # Load strategy config
        strategy_config = {
            "supply_demand": {
                "zone_detection": {
                    "min_zone_strength": 50.0,
                    "max_zone_age_hours": 72,
                    "min_touch_points": 2,
                    "volume_confirmation": True,
                },
                "zone_management": {
                    "max_zones_per_symbol": 50,
                    "max_zone_age_hours": 72,
                },
            }
        }

        # Check if database is available
        use_database = True
        try:
            from .data import get_session

            async with get_session():
                pass
        except Exception:
            logger.warning("Database not available - zones will be stored in memory only")
            use_database = False

        self.foundation_engine = FoundationEngine(strategy_config, use_database=use_database)

        # Load existing zones from database
        if use_database:
            logger.info("Loading zones from database...")
            for symbol in self.symbols:
                await self.foundation_engine.load_zones(symbol)

        logger.info("✅ Foundation strategy initialized")

    async def _initialize_strategy_system(self):
        """Initialize strategy manager and signal aggregator."""
        logger.info("Initializing strategy system...")

        # Get config dict (handle both Configuration object and dict)
        if hasattr(self.config, "_config"):
            config_dict = self.config._config
        else:
            config_dict = self.config if isinstance(self.config, dict) else {}

        # Initialize StrategyManager
        self.strategy_manager = StrategyManager(config_dict)

        # Register foundation strategy
        self.strategy_manager.register_strategy("foundation", self.foundation_engine)
        logger.info("Foundation strategy registered with StrategyManager")

        # Initialize SignalAggregator
        self.signal_aggregator = SignalAggregator(config_dict)

        logger.info("✅ Strategy system initialized")

    async def _initialize_position_risk_system(self):
        """Initialize position and risk management system."""
        logger.info("Initializing position and risk management system...")

        try:
            # Initialize Position Manager
            self.position_manager = PositionManager(self.config)

            # Initialize Automation Managers
            self.breakeven_manager = BreakevenManager(self.config)
            self.trailing_manager = TrailingStopManager(self.config)
            self.partial_manager = PartialCloseManager(self.config)

            # Initialize Risk Management
            self.portfolio_risk = PortfolioRiskManager(self.config)
            self.exposure_manager = ExposureManager(self.config)
            self.drawdown_protector = DrawdownProtector(self.config)

            # Initialize portfolio risk with starting balance
            # Priority: 1. Live MT5 Balance, 2. Config Balance, 3. Default 10k
            initial_balance = self.config.get("initial_balance", 10000.0)

            if self.mt5 and self.mt5.is_connected():
                account_info = self.mt5.account_info
                mt5_balance = account_info.get("balance")
                if mt5_balance is not None and mt5_balance > 0:
                    initial_balance = float(mt5_balance)
                    logger.info(f"Using live MT5 balance: ${initial_balance:,.2f}")

            self.portfolio_risk.initialize_balance(initial_balance)

            # Load active positions from database
            await self.position_manager.load_positions_from_db()

            logger.info("✅ Position and risk management system initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize position and risk management: {e}")
            raise

    async def _execute_signal(self, signal):
        """
        Execute a trading signal by creating and managing a position.

        Args:
            signal: TradingSignal object to execute
        """
        try:
            # Log signal details
            logger.info(
                f"  📍 SIGNAL: {signal.direction.value} {signal.symbol} @ {signal.entry_price:.5f} | "
                f"SL: {signal.stop_loss:.5f} | TP: {signal.take_profit:.5f} | "
                f"R:R: {signal.risk_reward_ratio:.2f} | "
                f"Confluence: {signal.confluence_score:.1f}%"
            )

            # Notify signal detection (Optional: can be noisy if many signals)
            # await self.notification_manager.send_message(
            #     f"📍 **SIGNAL DETECTED**\n"
            #     f"💱 **{signal.symbol}** | **{signal.direction.value}**\n"
            #     f"📉 Entry: `{signal.entry_price:.5f}`\n"
            #     f"📊 Score: `{signal.confluence_score:.1f}%`",
            #     level=NotificationLevel.INFO,
            #     sound=False
            # )

            # Log strategy scores
            for strategy_name, score in signal.strategy_scores.items():
                logger.debug(f"    └─ {strategy_name}: {score:.1f}")

            # Step 1: Risk validation
            if not await self._validate_signal_risk(signal):
                logger.warning(f"  ❌ Signal {signal.symbol} failed risk validation")
                await self.notification_manager.send_message(
                    f"🛡️ **SIGNAL REJECTED (RISK)**\n"
                    f"💱 `{signal.symbol}`\n"
                    f"Reason: Risk Validation Failed\n"
                    f"(Check logs for details)",
                    level=NotificationLevel.WARNING,
                )
                return

            # Step 2: Check exposure limits
            if not await self._check_exposure_limits(signal):
                logger.warning(f"  ❌ Signal {signal.symbol} failed exposure validation")
                # Silent rejection for exposure to avoid spam if signal persists
                return

            # Step 3: Calculate position size
            position_size = await self._calculate_position_size(signal)
            if position_size <= 0:
                logger.warning(f"  ❌ Invalid position size for {signal.symbol}")
                return

            # Step 3.5: Execute order on MT5 (if not dry-run)
            is_dry_run = self.config.get("trading", {}).get("dry_run", True)

            if not is_dry_run:
                if not self.mt5 or not self.mt5.is_connected():
                    logger.error("  ❌ Cannot execute trade: MT5 not connected")
                    return

                logger.info(f"  🚀 Executing LIVE order for {signal.symbol}...")
                order_result = self.mt5.place_order(
                    symbol=signal.symbol,
                    order_type=signal.direction.value,
                    volume=position_size,
                    price=signal.entry_price,
                    sl=signal.stop_loss,
                    tp=signal.take_profit,
                    comment=f"Signal {signal.signal_id}",
                )

                if not order_result:
                    logger.error(f"  ❌ MT5 Order Execution Failed for {signal.symbol}")
                    await self.notification_manager.send_message(
                        f"❌ **MT5 Order Failed**\n"
                        f"Symbol: `{signal.symbol}`\n"
                        f"Direction: `{signal.direction.value}`",
                        level=NotificationLevel.ERROR,
                    )
                    return

                logger.info(f"  ✅ MT5 Order Executed: Ticket {order_result.get('order')}")

                await self.notification_manager.send_message(
                    f"✅ **LIVE ORDER EXECUTED**\n"
                    f"🎫 Ticket: `{order_result.get('order')}`\n"
                    f"💱 **{signal.symbol}** | **{signal.direction.value}**\n"
                    f"📊 Size: `{position_size:.2f}` lots\n"
                    f"📉 Price: `{signal.entry_price:.5f}`\n"
                    f"🛑 SL: `{signal.stop_loss:.5f}`\n"
                    f"🎯 TP: `{signal.take_profit:.5f}`",
                    level=NotificationLevel.SUCCESS,
                )
            else:
                logger.info(f"  ⚠️ Dry-Run Mode: Skipping MT5 execution for {signal.symbol}")
                await self.notification_manager.send_message(
                    f"⚠️ **Dry-Run Order**\n"
                    f"💱 **{signal.symbol}** | **{signal.direction.value}**\n"
                    f"📊 Size: `{position_size:.2f}` lots\n"
                    f"📉 Price: `{signal.entry_price:.5f}`",
                    level=NotificationLevel.INFO,
                    sound=False,
                )

            # Step 4: Create position
            position = self.position_manager.create_position_from_signal(signal, position_size)

            # Step 5: Register with exposure manager
            asset_class = self._get_asset_class(signal.symbol)
            self.exposure_manager.register_position(signal.symbol, asset_class, position_size)

            # Step 6: Open position
            self.position_manager.open_position(position.position_id)

            # Save to database
            await self.position_manager.save_position(position)

            logger.info(
                f"  ✅ POSITION OPENED: {position.position_id} | "
                f"{position.position_type} {position.symbol} @ {position.entry_price:.5f} | "
                f"Volume: {position.volume:.2f} | Risk: ${position.risk_amount_usd:.2f}"
            )

        except Exception as e:
            logger.error(f"  ❌ Error executing signal {signal.symbol}: {e}")
            raise

    async def _validate_signal_risk(self, signal):
        """Validate signal against risk management rules."""
        try:
            # Calculate max risk amount from portfolio balance (2% default)
            max_risk_amount = self.portfolio_risk.calculate_max_risk_amount(
                self.portfolio_risk.current_balance
            )

            # Check portfolio risk limits using max risk amount
            can_trade, reason = self.portfolio_risk.can_take_trade(max_risk_amount)
            if not can_trade:
                logger.warning(f"  Portfolio risk validation failed: {reason}")
                return False

            # Check drawdown protection
            if self.drawdown_protector.should_close_all_positions():
                logger.warning("  Drawdown protection triggered - no new positions allowed")
                return False

            return True

        except Exception as e:
            logger.error(f"  Risk validation error: {e}")
            return False

    async def _check_exposure_limits(self, signal):
        """Check if signal respects exposure limits."""
        try:
            # Check if we already have a position for this symbol
            open_positions = self.position_manager.get_open_positions()
            if any(p.symbol == signal.symbol for p in open_positions):
                logger.warning(f"  Already have open position for {signal.symbol}")
                return False

            # Calculate max risk amount for exposure check
            max_risk_amount = self.portfolio_risk.calculate_max_risk_amount(
                self.portfolio_risk.current_balance
            )

            # Check symbol exposure limits
            asset_class = self._get_asset_class(signal.symbol)
            can_open, reason = self.exposure_manager.can_open_position(
                signal.symbol, asset_class, max_risk_amount
            )

            if not can_open:
                logger.warning(f"  Exposure validation failed: {reason}")
                return False

            return True

        except Exception as e:
            logger.error(f"  Exposure validation error: {e}")
            return False

    async def _calculate_position_size(self, signal):
        """Calculate appropriate position size for the signal."""
        try:
            from trading_bot.position.pip_calculator import PipCalculator

            # Calculate max risk amount (2% of portfolio)
            max_risk_amount = self.portfolio_risk.calculate_max_risk_amount(
                self.portfolio_risk.current_balance
            )

            # Get pip calculator to determine pip size and value
            pip_calculator = PipCalculator()
            pip_size = pip_calculator.get_pip_size(signal.symbol)

            # Calculate stop loss distance in pips
            # signal.risk_pips is already the price difference, convert to pips
            stop_distance_pips = signal.risk_pips / pip_size

            # Calculate pip value per lot
            pip_value_per_lot = pip_calculator.calculate_pip_value(signal.symbol, 1.0)  # 1 lot

            # Calculate position size using portfolio risk manager
            position_size = self.portfolio_risk.calculate_position_size(
                account_balance=self.portfolio_risk.current_balance,
                risk_amount_usd=max_risk_amount,
                stop_distance_pips=stop_distance_pips,
                pip_value_per_lot=pip_value_per_lot,
            )

            return position_size

        except Exception as e:
            logger.error(f"  Position size calculation error: {e}")
            return 0

    def _get_asset_class(self, symbol):
        """Determine asset class from symbol using config."""
        try:
            # Load asset classes from config
            if not hasattr(self, "_asset_classes"):
                from .connectors.symbol_mapper import SymbolMapper

                symbol_mapper = SymbolMapper()
                self._asset_classes = symbol_mapper.asset_classes

            # First, try to find exact match in config (for internal symbols)
            for asset_class, symbols in self._asset_classes.items():
                if symbol in symbols:
                    # Map to the expected format for position/risk managers
                    if asset_class == "commodity":
                        return "commodities"
                    elif asset_class == "forex":
                        # Further classify forex pairs
                        if symbol.endswith("JPY"):
                            return "forex_jpy"
                        else:
                            return "forex_major"
                    elif asset_class == "crypto":
                        return "crypto"
                    elif asset_class == "index":
                        return "index"
                    else:
                        return asset_class

            # If not found, try to convert broker symbol back to internal symbol
            internal_symbol = self._convert_broker_to_internal_symbol(symbol)
            if internal_symbol != symbol:
                # Try again with internal symbol
                return self._get_asset_class(internal_symbol)

            # Default fallback - try to determine from symbol pattern
            if any(c in symbol for c in ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]):
                # It's a forex pair
                if symbol.endswith("JPY") or "JPY" in symbol:
                    return "forex_jpy"
                else:
                    return "forex_major"
            elif any(c in symbol for c in ["XAU", "XAG", "WTI", "BRENT"]):
                return "commodities"
            elif any(c in symbol for c in ["BTC", "ETH", "LTC", "BCH", "XRP"]):
                return "crypto"
            elif any(c in symbol for c in ["US30", "SPX", "NAS", "UK100", "GER", "JPN", "CHN"]):
                return "index"

            # Final fallback
            return "forex_major"

        except Exception as e:
            logger.error(f"Error determining asset class for {symbol}: {e}")
            return "forex_major"  # Safe default

    def _convert_broker_to_internal_symbol(self, symbol):
        """Convert broker symbol back to internal symbol format."""
        try:
            if not self.symbol_mapper:
                return symbol

            # First normalize the broker symbol
            normalized_broker_symbol = self.symbol_mapper.normalize_symbol(symbol)

            # Get broker name
            broker_name = self.active_broker.lower()

            # Check reverse mappings
            if hasattr(self.symbol_mapper, "_reverse_mappings"):
                if broker_name in self.symbol_mapper._reverse_mappings:
                    reverse_mappings = self.symbol_mapper._reverse_mappings[broker_name]
                    if normalized_broker_symbol in reverse_mappings:
                        return reverse_mappings[normalized_broker_symbol]

            # If not found in reverse mappings, try to strip broker suffixes
            # Common suffixes: 'c' for cent, 'm' for standard, etc.
            clean_symbol = normalized_broker_symbol.rstrip("cm")

            # Try again with clean symbol
            if hasattr(self.symbol_mapper, "_reverse_mappings"):
                if broker_name in self.symbol_mapper._reverse_mappings:
                    reverse_mappings = self.symbol_mapper._reverse_mappings[broker_name]
                    if clean_symbol in reverse_mappings:
                        return reverse_mappings[clean_symbol]

            # Final fallback - return normalized symbol
            return normalized_broker_symbol

        except Exception as e:
            logger.debug(f"Error converting broker symbol {symbol}: {e}")
            return symbol

    async def _manage_positions(self):
        """Update and manage all open positions."""
        try:
            if not self.position_manager:
                return

            # Get current prices for all symbols with open positions
            open_positions = self.position_manager.get_open_positions()
            if not open_positions:
                return

            # Update positions with current prices
            for position in open_positions:
                try:
                    # Get current price (in production, this would be from MT5)
                    current_price = await self._get_current_price(position.symbol)
                    if current_price is None:
                        continue

                    # Update position
                    self.position_manager.update_position(position.position_id, current_price)

                    # Save update to database
                    await self.position_manager.save_position(position)

                    # Check automation triggers
                    await self._check_position_automation(position)

                except Exception as e:
                    logger.error(f"Error updating position {position.position_id}: {e}")

            # Check for SL/TP hits and close positions
            await self._check_position_closure()

        except Exception as e:
            logger.error(f"Error managing positions: {e}")

    async def _get_current_price(self, symbol):
        """Get current price for a symbol."""
        try:
            if self.data_manager:
                # Convert to broker symbol if needed
                broker_symbol = symbol
                if self.symbol_mapper:
                    try:
                        broker_symbol = self.symbol_mapper.convert_to_broker_symbol(
                            symbol, self.active_broker
                        )
                    except Exception:
                        broker_symbol = symbol

                # Get current price from data manager
                data = self.data_manager.get_ohlcv(
                    symbol=broker_symbol, timeframe="M1", count=1  # Use M1 for current price
                )

                if data is not None and not data.empty:
                    return float(data["close"].iloc[-1])

            # Fallback: only simulate price in dry-run/mock mode
            is_dry_run = self.config.get("trading", {}).get("dry_run", True)
            if is_dry_run or not self.data_manager:
                import random

                # Use a more realistic base price simulation if available, otherwise static default
                base_price = 1.1000 if symbol == "EURUSD" else 1.2000
                return base_price + random.uniform(-0.001, 0.001)

            # In live mode with missing data (e.g. market closed), return None
            # This prevents updating positions with fake data
            logger.debug(f"Live mode: No price data available for {symbol} (Market closed?)")
            return None

        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None

    async def _check_position_automation(self, position):
        """Check and apply automation features for a position."""
        try:
            # Breakeven check
            if self.breakeven_manager.should_move_to_breakeven(position):
                new_sl = self.breakeven_manager.move_to_breakeven(position)
                if new_sl:
                    logger.info(f"  🔄 BREAKEVEN: {position.position_id} SL moved to {new_sl:.5f}")
                    await self.position_manager.save_position(position)
                    await self.notification_manager.send_message(
                        f"🛡️ **BREAKEVEN SECURED**\n"
                        f"🆔 `{position.position_id}`\n"
                        f"🛑 SL Moved: `{new_sl:.5f}`\n"
                        f"🔒 Risk Free",
                        level=NotificationLevel.INFO,
                        sound=False,
                    )

            # Trailing stop check
            if self.trailing_manager.should_update_trailing_stop(position):
                new_sl = self.trailing_manager.update_trailing_stop(position)
                if new_sl:
                    logger.info(f"  🔄 TRAILING: {position.position_id} SL moved to {new_sl:.5f}")
                    await self.position_manager.save_position(position)
                    # Don't notify every trailing step to avoid spam, or use silent notification
                    # await self.notification_manager.send_message(..., sound=False)

            # Partial close check
            if self.partial_manager.should_close_partial(position):
                current_price = await self._get_current_price(position.symbol)
                result = self.partial_manager.execute_partial_close(position, current_price)
                if result and result["closed_volume"] > 0:
                    logger.info(
                        f"  🔄 PARTIAL CLOSE: {position.position_id} "
                        f"Closed {result['closed_volume']:.2f} at {current_price:.5f} "
                        f"P&L: ${result['profit_usd']:.2f}"
                    )
                    await self.position_manager.save_position(position)
                    await self.notification_manager.send_message(
                        f"💰 **PARTIAL PROFIT TAKEN**\n"
                        f"🆔 `{position.position_id}`\n"
                        f"📊 Closed: `{result['closed_volume']:.2f}` lots\n"
                        f"💵 Profit: **${result['profit_usd']:.2f}**",
                        level=NotificationLevel.SUCCESS,
                    )

        except Exception as e:
            logger.error(f"Error checking automation for position {position.position_id}: {e}")

    async def _check_position_closure(self):
        """Check for stop loss and take profit hits."""
        try:
            if not self.data_manager:
                return

            open_positions = self.position_manager.get_open_positions()
            for position in open_positions:
                try:
                    # Get current price
                    current_price = await self._get_current_price(position.symbol)
                    if current_price is None:
                        continue

                    # Check if SL or TP is hit
                    should_close = False
                    close_reason = None

                    if position.position_type == "BUY":
                        if current_price <= position.stop_loss:
                            should_close = True
                            close_reason = "Stop Loss"
                        elif current_price >= position.take_profit:
                            should_close = True
                            close_reason = "Take Profit"
                    else:  # SELL
                        if current_price >= position.stop_loss:
                            should_close = True
                            close_reason = "Stop Loss"
                        elif current_price <= position.take_profit:
                            should_close = True
                            close_reason = "Take Profit"

                    if should_close:
                        # Close position
                        result = self.position_manager.close_position(
                            position.position_id, current_price, close_reason
                        )

                        if result:
                            # Unregister from exposure manager
                            self.exposure_manager.unregister_position(
                                position.symbol, position.position_type
                            )

                            # Update portfolio risk
                            self.portfolio_risk.update_balance(
                                self.portfolio_risk.current_balance + result["pnl_usd"]
                            )

                            # Save closed state to database
                            await self.position_manager.save_position(position)

                            logger.info(
                                f"  ✅ POSITION CLOSED: {position.position_id} | "
                                f"{close_reason} | "
                                f"P&L: ${result['pnl_usd']:.2f} | "
                                f"Pips: {result['pips']:.1f}"
                            )

                            # Determine emoji based on profit
                            pnl_emoji = "💰" if result["pnl_usd"] > 0 else "💸"

                            await self.notification_manager.send_message(
                                f"{pnl_emoji} **POSITION CLOSED**\n"
                                f"🆔 `{position.position_id}`\n"
                                f"📝 Reason: `{close_reason}`\n"
                                f"💵 P&L: **${result['pnl_usd']:.2f}**\n"
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

    async def _trading_loop(self):
        """Main trading loop."""
        logger.info("📊 Starting main trading loop...")

        # Start heartbeat loop in background
        asyncio.create_task(self._heartbeat_loop())

        while self.is_running:
            try:
                # Analyze each symbol
                for symbol in self.symbols:
                    await self._analyze_symbol(symbol)

                # Update and manage positions
                await self._manage_positions()

                # Wait before next analysis
                logger.debug(f"Waiting {self.analysis_interval}s before next analysis...")
                await asyncio.sleep(self.analysis_interval)

            except KeyboardInterrupt:
                logger.info("Received stop signal")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                # Notify critical error
                if self.notification_manager:
                    await self.notification_manager.send_message(
                        f"❌ **CRITICAL ERROR**\n" f"Error in trading loop:\n" f"`{str(e)}`",
                        level=NotificationLevel.CRITICAL,
                    )
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _heartbeat_loop(self):
        """Periodic heartbeat notifications."""
        # Default interval: 4 hours (14400 seconds)
        # Use config if available or fallback
        interval_hours = 4

        logger.info(f"Heartbeat monitor started (interval: {interval_hours}h)")

        while self.is_running:
            try:
                # Wait for interval (convert to seconds)
                await asyncio.sleep(interval_hours * 3600)

                if not self.notification_manager:
                    continue

                # Gather stats
                balance = 0.0
                if self.portfolio_risk:
                    balance = self.portfolio_risk.current_balance

                open_positions = 0
                if self.position_manager:
                    open_positions = len(self.position_manager.get_open_positions())

                stats = {"balance": balance, "open_positions": open_positions}

                # Send heartbeat
                await self.notification_manager.send_heartbeat(stats)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(300)  # Retry after 5 mins on error

    def _is_market_open(self, symbol: str) -> bool:
        """
        Check if market is open for the symbol.

        Args:
            symbol: Trading symbol

        Returns:
            True if market is likely open, False otherwise
        """
        from datetime import datetime

        # Get asset class
        asset_class = self._get_asset_class(symbol)

        # Crypto is always open
        if asset_class == "crypto":
            return True

        # Get current UTC time
        now = datetime.now(UTC)
        weekday = now.weekday()  # 0=Monday, ..., 5=Saturday, 6=Sunday
        hour = now.hour

        # Weekend logic for Forex/Commodities (Simplified)
        # Saturday: Closed
        if weekday == 5:
            return False

        # Sunday: Closed before 21:00 UTC (approx market open)
        if weekday == 6 and hour < 21:
            return False

        # Friday: Closed after 22:00 UTC (approx market close)
        if weekday == 4 and hour >= 22:
            return False

        return True

    async def _analyze_symbol(self, symbol: str):
        """
        Analyze a symbol using strategy system.

        Args:
            symbol: Trading symbol (internal/universal format)
        """
        # Check market hours first
        if not self._is_market_open(symbol):
            logger.debug(f"Skipping {symbol}: Market closed (Weekend)")
            return

        try:
            # Convert internal symbol to broker symbol if mapper is available
            broker_symbol = symbol
            if self.symbol_mapper:
                try:
                    broker_symbol = self.symbol_mapper.convert_to_broker_symbol(
                        symbol, self.active_broker
                    )
                    logger.info(f"🔍 Analyzing {symbol} (broker: {broker_symbol})...")
                except Exception as e:
                    logger.warning(
                        f"Failed to convert symbol {symbol} to broker format: {e} - using as-is"
                    )
                    broker_symbol = symbol
            else:
                logger.info(f"🔍 Analyzing {symbol}...")

            # Get market data
            if self.data_manager is None:
                logger.warning(f"No data manager available for {symbol}")
                return

            # DataManager.get_ohlcv is synchronous, not async
            # Use broker symbol for MT5 data retrieval
            try:
                data = self.data_manager.get_ohlcv(
                    symbol=broker_symbol,
                    timeframe=self.timeframe,
                    count=100,  # Get 100 candles for analysis
                )
            except Exception as e:
                # Handle symbol not available or other data errors
                logger.warning(
                    f"Could not retrieve data for {symbol} (broker: {broker_symbol}): {e}"
                )
                return

            if data is None or data.empty:
                logger.warning(f"No data available for {symbol} (broker: {broker_symbol})")
                return

            # Run strategy analysis via StrategyManager
            strategy_results = await self.strategy_manager.analyze_symbol(
                symbol, data, self.timeframe
            )

            if not strategy_results:
                logger.debug(f"{symbol}: No strategy results generated")
                return

            logger.info(f"📊 {symbol}: Received {len(strategy_results)} results from strategies")

            # Aggregate signals via SignalAggregator
            signals = await self.signal_aggregator.aggregate_signals(strategy_results)

            if not signals:
                logger.debug(f"{symbol}: No valid signals after aggregation")
                return

            logger.info(f"✅ {symbol}: Generated {len(signals)} trading signals")

            # Execute signals (Phase 3: position execution)
            for signal in signals:
                await self._execute_signal(signal)

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
