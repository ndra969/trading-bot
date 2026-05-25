"""
Main trading bot orchestrator.

Coordinates all trading components and manages the trading loop.
"""

import asyncio
from datetime import UTC, datetime

from .connectors.data_manager import DataManager
from .connectors.mt5_connector import MT5Connector
from .connectors.symbol_mapper import SymbolMapper
from .position.automation.breakeven_manager import BreakevenManager
from .position.automation.partial_close_manager import PartialCloseManager
from .position.automation.trailing_stop_manager import TrailingStopManager
from .position.close_reason import CloseReason, resolve_close_reason
from .position.pip_calculator import PipCalculator
from .position.position_manager import PositionManager
from .position.position_models import Position
from .risk.drawdown_protector import DrawdownProtector
from .risk.exposure_manager import ExposureManager
from .risk.portfolio_risk_manager import PortfolioRiskManager
from .strategies.foundation.foundation_engine import FoundationEngine
from .strategies.signal_aggregator import SignalAggregator
from .strategies.strategy_manager import StrategyManager
from .utils.config_validator import validate_position_management_config
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

        # Account Management components
        self.account_sync_service = None
        self.account_selector = None
        self.current_account = None

        # Session & Config Management components
        self.session_repository = None
        self.config_repository = None
        self.current_session = None

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

        # Initialize symbol resolver (asset class + broker→internal conversion)
        from .utils.symbol_resolver import SymbolResolver

        self._symbol_resolver = SymbolResolver(
            symbol_mapper=self.symbol_mapper, active_broker=self.active_broker
        )

        # Initialize Notification Manager
        self.notification_manager = NotificationManager(self.config)

        # MTF Mode Configuration
        self.mtf_mode = config.get("trading", {}).get("mode", "single") == "mtf"
        self.mtf_analyzer = None  # Will be initialized in _initialize_foundation_strategy

        if self.mtf_mode:
            # MTF Mode: Load watchlist from trading.watchlist
            watchlist_config = config.get("trading", {}).get("watchlist", [])
            self.symbols = [
                item["symbol"] for item in watchlist_config if item.get("enabled", True)
            ]
            mtf_settings = config.get("trading", {}).get("mtf", {})
            self.zone_timeframe = mtf_settings.get("zone_timeframe", "H1")
            self.entry_timeframe = mtf_settings.get("entry_timeframe", "M30")
            self.timeframe = self.entry_timeframe  # Use entry TF for analysis loop
            logger.info(f"MTF Mode: Zone={self.zone_timeframe}, Entry={self.entry_timeframe}")
        else:
            # Single TF Mode (legacy)
            self.symbols = config.get("enabled_symbols", ["EURUSD", "GBPUSD"])
            self.timeframe = config.get("timeframe", "H1")
            logger.info(f"Single TF Mode: {self.timeframe}")

        # Default analysis interval: 60s (1 minute) for responsive trading
        self.analysis_interval = config.get("analysis_interval", 60)

        logger.info(f"TradingBot initialized for symbols: {self.symbols}")

    async def start(self):
        """Start trading bot."""
        logger.info("🚀 Starting trading bot...")

        try:
            # Validate config invariants before doing any work
            validate_position_management_config(self.config)

            # Check dry-run mode from config
            is_dry_run = self.config.get("trading", {}).get("dry_run", False)

            # Initialize MT5 connection (skip if already set from CLI or in mock mode)
            if self.mt5 is None:
                # In mock MT5 mode (dry-run), mt5 is intentionally None
                # Skip initialization and continue without MT5
                if is_dry_run:
                    logger.info("🔧 DRY-RUN MODE: MT5 not set (mock mode) - using simulated data")
                    self.data_manager = None
                else:
                    # LIVE TRADING: Initialize MT5 connector
                    logger.info("🔴 LIVE MODE: Initializing MT5 connector...")
                    try:
                        await self._initialize_mt5()
                    except Exception as e:
                        logger.error(f"❌ Failed to initialize MT5: {e}")
                        logger.error("❌ Cannot proceed in live mode without MT5 connection")
                        raise
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
                            logger.info("✅ Data manager initialized - will use REAL MT5 data")
                except Exception as e:
                    logger.warning(f"MT5 initialization failed: {e} - continuing without MT5")
                    self.data_manager = None
                    if not is_dry_run:
                        logger.error(
                            "❌ CRITICAL: MT5 failed but dry_run=False - bot will not work properly in live mode!"
                        )

            # Initialize account management (if MT5 is connected)
            if not is_dry_run and self.mt5 and self.mt5.is_connected():
                await self._initialize_account_management()

            # Initialize session and config management
            await self._initialize_session_management(is_dry_run)

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
        try:
            logger.info("🛑 Stopping trading bot...")
        except Exception:
            # If logger fails, just print to console
            print("🛑 Stopping trading bot...")

        self.is_running = False

        # Stop notification manager
        if self.notification_manager:
            try:
                await self.notification_manager.stop()
            except Exception as e:
                print(f"⚠️ Error stopping notification manager: {e}")

        # Close trading session
        if self.current_session and self.session_repository:
            try:
                # Get ending balance
                ending_balance = self.config.get("initial_balance", 10000.0)
                if self.mt5 and self.mt5.is_connected():
                    account_info = self.mt5.account_info
                    mt5_balance = account_info.get("balance")
                    if mt5_balance is not None and mt5_balance > 0:
                        ending_balance = float(mt5_balance)

                # Close session
                await self.session_repository.close_session(
                    session_id=self.current_session.session_id,
                    ending_balance=ending_balance,
                )
                logger.info(f"✅ Trading session closed: {self.current_session.session_id}")
            except Exception as e:
                logger.warning(f"Error closing trading session: {e}")

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

        # Get config dict
        if hasattr(self.config, "_config"):
            config_dict = self.config._config
        else:
            config_dict = self.config if isinstance(self.config, dict) else {}

        # Use the loaded configuration
        # If strategy_parameters.yaml is loaded, it should be in config_dict
        strategy_config = config_dict

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

        # Initialize MTFAnalyzer if in MTF mode
        if self.mtf_mode:
            from .strategies.mtf_analyzer import MTFAnalyzer

            self.mtf_analyzer = MTFAnalyzer(config=strategy_config, use_database=use_database)
            logger.info(
                f"MTFAnalyzer initialized (Zone: {self.zone_timeframe}, Entry: {self.entry_timeframe})"
            )

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

    async def _initialize_account_management(self):
        """Initialize account management system."""
        try:
            from .data.services.account_selector import AccountSelector
            from .data.services.account_sync_service import AccountSyncService

            # Initialize account sync service
            self.account_sync_service = AccountSyncService(mt5_connector=self.mt5)

            # Ensure current MT5 account exists in database
            logger.info("📊 Checking/creating trading account in database...")
            account = await self.account_sync_service.ensure_account_exists(self.mt5)

            if account:
                self.current_account = account
                logger.info(
                    f"✅ Account management initialized: Account {account.account_id} "
                    f"({account.broker_name}, {account.account_type})"
                )
            else:
                logger.warning(
                    "⚠️ Failed to ensure account exists - continuing without account tracking"
                )

            # Initialize account selector
            self.account_selector = AccountSelector()
            if account:
                await self.account_selector.switch_account(account.account_id)
                logger.info(f"✅ Active account set: {account.account_id}")

        except Exception as e:
            logger.warning(
                f"Account management initialization failed: {e} - continuing without account tracking"
            )
            self.account_sync_service = None
            self.account_selector = None

    async def _initialize_session_management(self, is_dry_run: bool):
        """Initialize session and config management system."""
        try:
            from .data.repositories.config_repository import ConfigRepository
            from .data.repositories.session_repository import SessionRepository
            from .utils.config_hasher import hash_config

            # Initialize repositories
            self.session_repository = SessionRepository()
            self.config_repository = ConfigRepository()

            # Step 1: Create ConfigSnapshot from current config
            logger.info("📸 Creating config snapshot...")
            # Convert config to dict safely
            if hasattr(self.config, "_config"):
                config_dict = self.config._config.copy()
            elif hasattr(self.config, "__dict__"):
                config_dict = dict(self.config.__dict__)
            else:
                config_dict = dict(self.config) if isinstance(self.config, dict) else {}

            # Step 1: Create ConfigSnapshot from current config
            try:
                result = await self.config_repository.get_or_create(
                    config_data=config_dict,
                    description=f"Bot start - {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}",
                    environment="development" if is_dry_run else "production",
                )
                # Unpack tuple (ConfigSnapshot, bool)
                if isinstance(result, tuple) and len(result) == 2:
                    config_snapshot, created = result
                else:
                    # Fallback if result is not tuple (shouldn't happen, but safety check)
                    config_snapshot = result if not isinstance(result, tuple) else result[0]
                    created = True

                if not config_snapshot:
                    raise ValueError("Config snapshot is None after get_or_create")

                if created:
                    logger.info(f"✅ Config snapshot created: {config_snapshot.config_hash[:12]}...")
                else:
                    logger.info(
                        f"✅ Config snapshot already exists: {config_snapshot.config_hash[:12]}..."
                    )
            except Exception as e:
                logger.error(f"❌ Failed to create config snapshot: {e}", exc_info=True)
                raise

            # Step 2: Get trading type from config
            trading_type = self.config.get("trading", {}).get("trading_type", "day_trading")
            if not trading_type or trading_type not in [
                "scalping",
                "day_trading",
                "swing_trading",
                "position_trading",
            ]:
                trading_type = "day_trading"

            # Step 3: Get account_id if available
            account_id = None
            if self.current_account:
                account_id = self.current_account.account_id

            # Step 4: Get starting balance
            starting_balance = self.config.get("initial_balance", 10000.0)
            if self.mt5 and self.mt5.is_connected():
                account_info = self.mt5.account_info
                mt5_balance = account_info.get("balance")
                if mt5_balance is not None and mt5_balance > 0:
                    starting_balance = float(mt5_balance)

            # Step 5: Generate unique session_id
            try:
                config_hash_short = hash_config(config_dict)[:8]
            except Exception as e:
                logger.warning(f"Failed to hash config for session_id: {e}, using timestamp only")
                config_hash_short = datetime.now(UTC).strftime("%H%M%S")

            session_id = (
                f"session_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{config_hash_short}"
            )

            # Step 6: Create TradingSession
            logger.info(f"📊 Creating trading session: {session_id}...")
            session_data = {
                "session_id": session_id,
                "account_id": account_id,
                "config_hash": config_snapshot.config_hash,
                "trading_type": trading_type,
                "is_backtest": False,
                "is_dry_run": is_dry_run,
                "starting_balance": starting_balance,
                "status": "ACTIVE",
            }

            try:
                self.current_session = await self.session_repository.create(session_data)
                logger.info(
                    f"✅ Trading session created: {session_id} "
                    f"(type: {trading_type}, account: {account_id}, dry_run: {is_dry_run})"
                )
                # Verify session was saved by querying database
                if self.current_session and self.current_session.session_id:
                    verified_session = await self.session_repository.get_by_session_id(session_id)
                    if verified_session:
                        logger.info(
                            f"✅ Session verified in database: ID={verified_session.id}, session_id={verified_session.session_id}"
                        )
                    else:
                        logger.error(f"❌ Session created but not found in database: {session_id}")
                else:
                    logger.error("❌ Session created but session_id is None!")
            except Exception as e:
                logger.error(f"❌ Failed to create trading session: {e}", exc_info=True)
                raise

        except Exception as e:
            logger.error(
                f"❌ Session management initialization failed: {e} - continuing without session tracking",
                exc_info=True,
            )
            self.session_repository = None
            self.config_repository = None
            self.current_session = None

    async def _update_session_on_position_close(self, position: Position, result: dict | None):
        """
        Update session aggregations when a position closes.

        Args:
            position: Closed position
            result: Close result dict with pnl_usd and pips
        """
        if not self.current_session or not self.session_repository or not result:
            return

        try:
            pnl_usd = result.get("pnl_usd", 0.0)
            is_winner = pnl_usd > 0
            gross_profit = pnl_usd if is_winner else 0.0
            gross_loss = abs(pnl_usd) if not is_winner else 0.0

            await self.session_repository.update_aggregations(
                session_id=self.current_session.session_id,
                pnl=pnl_usd,
                is_winner=is_winner,
                gross_profit=gross_profit,
                gross_loss=gross_loss,
            )
            logger.debug(
                f"  📊 Session aggregations updated: " f"P&L=${pnl_usd:.2f}, Winner={is_winner}"
            )
        except Exception as e:
            logger.warning(f"Error updating session aggregations: {e}")

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
                    mt5_balance = float(mt5_balance)
                    # WARNING: Check if config balance significantly differs from MT5
                    config_balance = initial_balance
                    if abs(mt5_balance - config_balance) / config_balance > 0.1:  # >10% difference
                        logger.warning(
                            f"⚠️  BALANCE MISMATCH: MT5 balance (${mt5_balance:,.2f}) differs "
                            f"significantly from default (${config_balance:,.2f}). "
                            f"Using MT5 balance for accurate risk management!"
                        )
                    initial_balance = mt5_balance
                    logger.info(f"✅ Using live MT5 balance: ${initial_balance:,.2f}")
                else:
                    logger.warning(
                        f"⚠️  Could not get MT5 balance, using default: ${initial_balance:,.2f}. "
                        f"RISK: Position sizing may be inaccurate!"
                    )
            else:
                logger.warning(
                    f"⚠️  MT5 not connected during init, using default balance: ${initial_balance:,.2f}. "
                    f"Balance will be updated when MT5 connects."
                )

            # Store the expected MT5 balance for later verification
            self.expected_mt5_balance = None

            self.portfolio_risk.initialize_balance(initial_balance)
            logger.info(
                f"📊 Portfolio Risk initialized with balance: ${initial_balance:,.2f} "
                f"(Risk per trade: {self.portfolio_risk.max_risk_per_trade_pct}% = ${initial_balance * self.portfolio_risk.max_risk_per_trade_pct / 100:.2f})"
            )

            # Load active positions from database
            await self.position_manager.load_positions_from_db()

            # Register loaded positions with exposure manager (for correlation tracking)
            open_positions = self.position_manager.get_open_positions()
            for position in open_positions:
                asset_class = self._get_asset_class(position.symbol)
                self.exposure_manager.register_position(
                    position.symbol,
                    asset_class,
                    position.volume,
                    direction=position.position_type.value,
                )
                logger.debug(
                    f"Registered existing position: {position.symbol} ({position.position_type.value})"
                )

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

            # Get dry-run mode (needed for MT5 position check)
            is_dry_run = self.config.get("trading", {}).get("dry_run", False)

            # Step 1: Skip if duplicate position exists (database or MT5)
            if self._has_duplicate_position(signal, is_dry_run):
                return

            # Step 2: Check exposure limits (position limits per symbol/total)
            if not await self._check_exposure_limits(signal):
                logger.warning(f"  ❌ Signal {signal.symbol} failed exposure validation")
                # Silent rejection for exposure to avoid spam if signal persists
                return

            # Step 3: Risk validation (portfolio risk, daily limits, etc.)
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

            # Step 3: Calculate position size
            position_size = await self._calculate_position_size(signal)
            if position_size <= 0:
                logger.warning(f"  ❌ Invalid position size for {signal.symbol}")
                return

            # Step 3.5: Execute order on MT5 (if not dry-run)
            is_dry_run = self.config.get("trading", {}).get(
                "dry_run", False
            )  # Default to False for live trading
            real_entry_price = signal.entry_price  # Default to signal price

            order_result = None
            if not is_dry_run:
                # Send live order to MT5 (handles connection check + order placement)
                order_result = await self._execute_mt5_order(signal, position_size)
                if order_result is None:
                    return  # MT5 not connected or order rejected (notifications already sent)

                # Update entry price from actual execution price
                if "price" in order_result:
                    real_entry_price = float(order_result["price"])
                    logger.info(
                        f"  📝 Execution Price Updated: "
                        f"{signal.entry_price:.5f} -> {real_entry_price:.5f}"
                    )

                # Format confluence breakdown
                confluence_text = f"\n📊 Confluence: **{signal.confluence_score:.1f}%**"

                # Add strategy scores breakdown
                if signal.strategy_scores:
                    active_layers = []
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

                    for layer, score in sorted(
                        signal.strategy_scores.items(), key=lambda x: x[1], reverse=True
                    ):
                        if score > 0:
                            layer_display = layer_names.get(layer, layer.title())
                            active_layers.append(f"{layer_display}: {score:.1f}%")

                    if active_layers:
                        confluence_text += f"\n   └─ {' | '.join(active_layers[:5])}"  # Max 5 layers to avoid too long
                        if len(active_layers) > 5:
                            confluence_text += f" (+{len(active_layers) - 5} more)"

                # Extract price action info from signal metadata
                price_action_text = ""
                if signal.metadata and "price_action" in signal.metadata:
                    pa_info = signal.metadata["price_action"]
                    pattern_type = pa_info.get("pattern_type", "UNKNOWN")
                    direction = pa_info.get("direction", "")
                    confidence = pa_info.get("confidence", 0.0)
                    status = pa_info.get("status", "detected")

                    if status == "detected" or status == "neutral_pattern":
                        direction_emoji = (
                            "🟢"
                            if direction == "BULLISH"
                            else "🔴"
                            if direction == "BEARISH"
                            else "⚪"
                        )
                        pattern_emoji = "📊"
                        # Add specific emoji for common patterns
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
                        price_action_text = f"\n{pattern_emoji} Price Action: {direction_emoji} **{pattern_type}** ({direction}, {confidence:.0f}%){neutral_note}"
                    elif status == "wrong_direction":
                        detected_pattern = pa_info.get("detected_pattern", "UNKNOWN")
                        price_action_text = (
                            f"\n⚠️ Price Action: **{detected_pattern}** (wrong direction)"
                        )
                    else:
                        price_action_text = "\n📈 Price Action: No pattern detected"

                await self.notification_manager.send_message(
                    f"✅ **LIVE ORDER EXECUTED**\n"
                    f"🎫 Ticket: `{order_result.get('order')}`\n"
                    f"💱 **{signal.symbol}** | **{signal.direction.value}**\n"
                    f"📊 Size: `{position_size:.2f}` lots\n"
                    f"📉 Price: `{real_entry_price:.5f}`\n"
                    f"🛑 SL: `{signal.stop_loss:.5f}`\n"
                    f"🎯 TP: `{signal.take_profit:.5f}`"
                    f"{confluence_text}"
                    f"{price_action_text}",
                    level=NotificationLevel.SUCCESS,
                )
            else:
                logger.info(f"  ⚠️ Dry-Run Mode: Skipping MT5 execution for {signal.symbol}")

                # Format confluence breakdown
                confluence_text = f"\n📊 Confluence: **{signal.confluence_score:.1f}%**"

                # Add strategy scores breakdown
                if signal.strategy_scores:
                    active_layers = []
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

                    for layer, score in sorted(
                        signal.strategy_scores.items(), key=lambda x: x[1], reverse=True
                    ):
                        if score > 0:
                            layer_display = layer_names.get(layer, layer.title())
                            active_layers.append(f"{layer_display}: {score:.1f}%")

                    if active_layers:
                        confluence_text += f"\n   └─ {' | '.join(active_layers[:5])}"  # Max 5 layers to avoid too long
                        if len(active_layers) > 5:
                            confluence_text += f" (+{len(active_layers) - 5} more)"

                # Extract price action info from signal metadata
                price_action_text = ""
                if signal.metadata and "price_action" in signal.metadata:
                    pa_info = signal.metadata["price_action"]
                    pattern_type = pa_info.get("pattern_type", "UNKNOWN")
                    direction = pa_info.get("direction", "")
                    confidence = pa_info.get("confidence", 0.0)
                    status = pa_info.get("status", "detected")

                    if status == "detected" or status == "neutral_pattern":
                        direction_emoji = (
                            "🟢"
                            if direction == "BULLISH"
                            else "🔴"
                            if direction == "BEARISH"
                            else "⚪"
                        )
                        pattern_emoji = "📊"
                        # Add specific emoji for common patterns
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
                        price_action_text = f"\n{pattern_emoji} Price Action: {direction_emoji} **{pattern_type}** ({direction}, {confidence:.0f}%){neutral_note}"
                    elif status == "wrong_direction":
                        detected_pattern = pa_info.get("detected_pattern", "UNKNOWN")
                        price_action_text = (
                            f"\n⚠️ Price Action: **{detected_pattern}** (wrong direction)"
                        )
                    else:
                        price_action_text = "\n📈 Price Action: No pattern detected"

                await self.notification_manager.send_message(
                    f"⚠️ **Dry-Run Order**\n"
                    f"💱 **{signal.symbol}** | **{signal.direction.value}**\n"
                    f"📊 Size: `{position_size:.2f}` lots\n"
                    f"📉 Price: `{signal.entry_price:.5f}`"
                    f"{confluence_text}"
                    f"{price_action_text}",
                    level=NotificationLevel.INFO,
                    sound=False,
                )

            # Step 4: Create position (Update entry price with real one)
            # We temporarily update signal entry price to reflect reality for position creation
            original_signal_price = signal.entry_price
            signal.entry_price = real_entry_price

            position = self.position_manager.create_position_from_signal(signal, position_size)

            # Restore signal price (good practice not to mutate passed objects permanently)
            signal.entry_price = original_signal_price

            # Add confluence_score from signal (always available)
            position.confluence_score = signal.confluence_score
            if not position.metadata:
                position.metadata = {}
            position.metadata["confluence_score"] = signal.confluence_score
            logger.debug(
                f"  📊 Confluence Score: {signal.confluence_score:.1f}% (saved to position)"
            )

            # Add ticket if available (store in metadata for persistence)
            if not is_dry_run and "order_result" in locals() and order_result:
                ticket_value = int(order_result.get("order"))
                # Store ticket in both position object and metadata
                position.ticket = ticket_value
                position.metadata["ticket"] = ticket_value
                logger.info(f"  🎫 Position Ticket: {ticket_value} (saved to position and metadata)")

            # Link position to current active account (multi-account support)
            if self.account_selector:
                active_account = await self.account_selector.get_active_account()
                if active_account:
                    position.account_id = active_account.account_id
                    logger.debug(f"  🏦 Position linked to account: {active_account.account_id}")

            # Link position to current trading session
            if self.current_session:
                position.session_id = self.current_session.session_id
                logger.debug(f"  📊 Position linked to session: {self.current_session.session_id}")

            # Step 5: Register with exposure manager
            asset_class = self._get_asset_class(signal.symbol)
            self.exposure_manager.register_position(
                signal.symbol, asset_class, position_size, direction=signal.direction.value
            )

            # Step 6: Open position
            self.position_manager.open_position(position.position_id)

            # Save to database (skip in dry-run mode)
            await self.position_manager.save_position(position, is_dry_run=is_dry_run)

            logger.info(
                f"  ✅ POSITION OPENED: {position.position_id} | "
                f"{position.position_type} {position.symbol} @ {position.entry_price:.5f} | "
                f"Volume: {position.volume:.2f} | Risk: ${position.risk_amount_usd:.2f}"
            )

        except Exception as e:
            logger.error(f"  ❌ Error executing signal {signal.symbol}: {e}")
            raise

    async def _execute_mt5_order(self, signal, position_size: float) -> dict | None:
        """Execute a live order on MT5 with connection check and error handling.

        Steps:
            1. Verify MT5 connection (notify on failure)
            2. Convert signal symbol to broker format
            3. Place order via mt5.place_order()
            4. Handle order rejection with notification

        Returns:
            order_result dict on success, None if connection failed or order rejected.
            All failure paths send notifications and log errors before returning None.
        """
        # Step 1: Verify MT5 connection
        if not self._is_mt5_ready_for_trading(signal):
            return None

        # Step 2: Convert to broker symbol
        execute_symbol = self._convert_to_broker_symbol_safe(signal.symbol)
        if execute_symbol != signal.symbol:
            logger.debug(f"  Converted {signal.symbol} to {execute_symbol} for execution")

        logger.info(f"  🚀 Executing LIVE order for {signal.symbol}...")

        # Step 3: Place order
        order_result = self.mt5.place_order(
            symbol=execute_symbol,
            order_type=signal.direction.value,
            volume=position_size,
            price=signal.entry_price,
            sl=signal.stop_loss,
            tp=signal.take_profit,
            comment=f"Signal {signal.signal_id}",
        )

        # Step 4: Handle rejection
        if order_result.get("success") is False:
            await self._notify_order_failed(signal, position_size, order_result)
            return None

        logger.info(f"  ✅ MT5 Order Executed: Ticket {order_result.get('order')}")
        return order_result

    def _is_mt5_ready_for_trading(self, signal) -> bool:
        """Check MT5 is connected and ready. Sends notification + returns False on failure."""
        mt5_status = self._diagnose_mt5_connection()
        if self.mt5 and self.mt5.is_connected():
            logger.debug("  ✅ MT5 connection verified: ready for trade execution")
            return True

        logger.warning(f"  ⚠️ Cannot execute trade: MT5 not connected ({mt5_status})")
        if self.notification_manager:
            try:
                asyncio.create_task(
                    self.notification_manager.send_message(
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

    def _diagnose_mt5_connection(self) -> str:
        """Return a human-readable string describing current MT5 connection state."""
        if self.mt5 is None:
            return "MT5 connector is None"
        if not hasattr(self.mt5, "is_connected"):
            return "MT5 connector missing is_connected method"
        if not self.mt5.is_connected():
            try:
                health = self.mt5.health_check() if hasattr(self.mt5, "health_check") else {}
                return (
                    f"is_connected()=False, "
                    f"_is_connected={getattr(self.mt5, '_is_connected', 'unknown')}, "
                    f"terminal_connected={health.get('connected', 'unknown')}, "
                    f"trade_allowed={health.get('trade_allowed', 'unknown')}"
                )
            except Exception as e:
                return f"Error checking connection: {e}"
        return "connected"

    # MT5 error codes that don't warrant user notification (expected/transient)
    _SILENT_MT5_ERROR_CODES: frozenset[int] = frozenset(
        {
            10018,  # Market is closed
            10035,  # Market is closed (alt code)
        }
    )

    async def _notify_order_failed(self, signal, position_size: float, order_result: dict) -> None:
        """Log order failure and notify user (unless error code is silenced).

        Some errors (e.g. market closed) are expected and don't warrant
        Telegram alerts - we log them but skip the notification.
        """
        error_msg = order_result.get("error", "Unknown error")
        error_code = order_result.get("error_code", 0)
        error_description = order_result.get("error_description", "No description available")

        logger.error(
            f"  ❌ MT5 Order Execution Failed for {signal.symbol}: "
            f"{error_msg} (code: {error_code})"
        )

        # Skip notification for expected/transient errors (market closed, etc.)
        if error_code in self._SILENT_MT5_ERROR_CODES:
            logger.debug(
                f"  🔕 Silent error code {error_code} ({error_description}) - "
                f"no notification sent"
            )
            return

        await self.notification_manager.send_message(
            f"❌ **MT5 Order Failed**\n"
            f"Symbol: `{signal.symbol}`\n"
            f"Direction: `{signal.direction.value}`\n"
            f"Volume: `{position_size}`\n"
            f"Error: `{error_msg}`\n"
            f"Error Code: `{error_code}`\n"
            f"Description: `{error_description}`",
            level=NotificationLevel.ERROR,
        )

    def _has_duplicate_position(self, signal, is_dry_run: bool) -> bool:
        """Check if an open position already exists for this signal's symbol.

        Checks both:
        1. In-memory position_manager state (DB-backed)
        2. Live MT5 positions (in case DB is out of sync)

        Returns:
            True if duplicate exists (signal should be skipped), False otherwise.
        """
        signal_symbol_norm = self._normalize_symbol(signal.symbol)

        # Check DB-backed positions
        existing = [
            p
            for p in self.position_manager.get_open_positions()
            if self._normalize_position_symbol(p.symbol) == signal_symbol_norm
        ]
        if existing:
            logger.info(
                f"  ⏭️  Skipping signal for {signal.symbol} - already have {len(existing)} "
                f"open position(s): {[p.position_id for p in existing]} "
                f"(symbols: {[p.symbol for p in existing]})"
            )
            return True

        # Check live MT5 positions (DB might be out of sync)
        if not is_dry_run and self.mt5 and self.mt5.is_connected():
            try:
                broker_symbol = self._convert_to_broker_symbol_safe(signal.symbol)
                mt5_positions = self.mt5.get_positions(symbol=broker_symbol)
                if mt5_positions:
                    logger.info(
                        f"  ⏭️  Skipping signal for {signal.symbol} - found {len(mt5_positions)} "
                        f"open position(s) in MT5 (broker: {broker_symbol})"
                    )
                    return True
            except Exception as e:
                logger.debug(f"  Could not check MT5 positions for {signal.symbol}: {e}")

        return False

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize a symbol via symbol_mapper, with fallback to upper().strip()."""
        if self.symbol_mapper:
            try:
                return self.symbol_mapper.normalize_symbol(symbol)
            except Exception:
                pass
        return symbol.upper().strip()

    def _normalize_position_symbol(self, symbol: str) -> str:
        """Normalize a position's stored symbol back to universal form for comparison."""
        if not self.symbol_mapper:
            return symbol.upper().strip()
        try:
            return self.symbol_mapper.convert_to_universal_symbol(symbol, self.active_broker)
        except Exception:
            return self._normalize_symbol(symbol)

    def _convert_to_broker_symbol_safe(self, symbol: str) -> str:
        """Convert symbol to broker format, returning input symbol on any failure."""
        if not self.symbol_mapper:
            return symbol
        try:
            return self.symbol_mapper.convert_to_broker_symbol(symbol, self.active_broker)
        except Exception:
            return symbol

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
        """Check if signal respects exposure limits (position limits per symbol/total)."""
        try:
            # Note: Existing position check is now done in _execute_signal() Step 1
            # This method only checks position limits (max per symbol, max total)

            # Calculate max risk amount for exposure check
            max_risk_amount = self.portfolio_risk.calculate_max_risk_amount(
                self.portfolio_risk.current_balance
            )

            # Check symbol exposure limits (including correlation conflicts)
            asset_class = self._get_asset_class(signal.symbol)
            can_open, reason = self.exposure_manager.can_open_position(
                signal.symbol, asset_class, max_risk_amount, signal.direction.value
            )

            if not can_open:
                logger.warning(f"  Exposure validation failed: {reason}")
                return False

            return True

        except Exception as e:
            logger.error(f"  Exposure validation error: {e}")
            return False

    async def _sync_balance_from_mt5(self):
        """Sync balance from MT5 to ensure accurate position sizing."""
        if not self.mt5 or not self.mt5.is_connected():
            logger.debug("MT5 not connected - skipping balance sync")
            return

        try:
            account_info = self.mt5.account_info
            mt5_balance = account_info.get("balance")

            if mt5_balance is not None and mt5_balance > 0:
                mt5_balance = float(mt5_balance)
                current_balance = self.portfolio_risk.current_balance

                # Check if balance changed significantly (more than 1%)
                if abs(mt5_balance - current_balance) / current_balance > 0.01:
                    logger.info(
                        f"💰 Balance updated: ${current_balance:,.2f} → ${mt5_balance:,.2f} "
                        f"(Change: {(mt5_balance - current_balance):+.2f}, "
                        f"{(mt5_balance - current_balance) / current_balance * 100:+.1f}%)"
                    )
                    self.portfolio_risk.update_balance(mt5_balance)
                    self.expected_mt5_balance = mt5_balance
                else:
                    # Small change or no change, just verify
                    self.expected_mt5_balance = mt5_balance

        except Exception as e:
            logger.error(f"Failed to sync balance from MT5: {e}")

    async def _calculate_position_size(self, signal):
        """
        Calculate appropriate position size for the signal.

        Uses config-based lot size setting:
        - If use_dynamic_lot_size=false: Use fixed min_volume_lots from config
        - If use_dynamic_lot_size=true (or not set): Calculate dynamically based on risk

        This allows per-symbol control of lot sizing strategy.
        """
        logger.info(f"  🔧 [LOT CALC] Starting position size calculation for {signal.symbol}...")

        try:
            # CRITICAL: Sync balance from MT5 BEFORE calculating position size
            # This ensures we always use the most recent balance
            await self._sync_balance_from_mt5()

            # CRITICAL: Convert broker symbol to universal format for config lookup
            # EURUSDc -> EURUSD so we can find the config in active_symbols.yaml
            # Uses proper broker mapping from symbol_mapping.yaml (e.g., exness_cent)
            symbol_for_config = signal.symbol
            if self.symbol_mapper:
                try:
                    # Use convert_to_universal_symbol() to properly map broker symbols to universal format
                    symbol_for_config = self.symbol_mapper.convert_to_universal_symbol(
                        signal.symbol
                    )
                except Exception:
                    # Fallback to basic normalization if conversion fails
                    symbol_for_config = signal.symbol.upper().strip()

            # Get symbol config from active_symbols.yaml
            # CRITICAL FIX: Config structure is config['symbols'] not config['active_symbols']['symbols']
            symbol_cfg = self.config.get("symbols", {}).get(symbol_for_config, {})

            # DEBUG: Log symbol config lookup
            logger.debug(
                f"  🔍 Symbol lookup: signal.symbol={signal.symbol}, symbol_for_config={symbol_for_config}"
            )
            logger.debug(
                f"  🔍 Symbol config found: {bool(symbol_cfg)}, keys={list(symbol_cfg.keys()) if symbol_cfg else 'None'}"
            )

            # Check if symbol should use dynamic lot sizing
            use_dynamic = symbol_cfg.get("use_dynamic_lot_size", True)  # Default to True
            logger.debug(f"  🔍 use_dynamic_lot_size={use_dynamic} (from config or default True)")

            # FIXED LOT SIZE MODE (for testing or risky symbols like XAUUSD)
            if not use_dynamic:
                fixed_lot_size = symbol_cfg.get("min_volume_lots", 0.01)

                logger.info(
                    f"  📊 {signal.symbol} FIXED lot size: {fixed_lot_size:.2f} lots (config-based)"
                )
                return fixed_lot_size

            # DYNAMIC LOT SIZE MODE (calculate based on risk)
            logger.info(f"  📊 {signal.symbol} using DYNAMIC lot sizing mode...")
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

            # Apply min/max limits from config if available
            min_lot = symbol_cfg.get("min_volume_lots", 0.01)
            max_lot = symbol_cfg.get("max_volume_lots", 100.0)

            # Clamp position size to config limits
            position_size = max(min_lot, min(position_size, max_lot))

            logger.info(
                f"  📊 Position sizing: {signal.symbol} | Balance=${self.portfolio_risk.current_balance:.2f}, "
                f"Risk=${max_risk_amount:.2f}, SL={stop_distance_pips:.1f} pips, "
                f"PipValue=${pip_value_per_lot:.2f}, Size={position_size:.2f} lots (dynamic)"
            )

            return position_size

        except Exception as e:
            logger.error(f"  Position size calculation error: {e}")
            logger.error(
                f"  Trace: symbol={signal.symbol}, balance={self.portfolio_risk.current_balance}"
            )
            # Fallback: Try to get from config with proper structure
            # CRITICAL: Config structure is config['symbols'] not config['active_symbols']['symbols']
            symbol_cfg = self.config.get("symbols", {}).get(signal.symbol, {})
            fallback_lot = symbol_cfg.get("min_volume_lots", 0.01)

            logger.info(f"  ⚠️  Using fallback lot size: {fallback_lot:.2f} lots")
            return fallback_lot

    def _get_asset_class(self, symbol):
        """Determine asset class from symbol. Delegates to SymbolResolver."""
        return self._symbol_resolver.get_asset_class(symbol)

    def _convert_broker_to_internal_symbol(self, symbol):
        """Convert broker symbol to internal format. Delegates to SymbolResolver."""
        return self._symbol_resolver.convert_broker_to_internal_symbol(symbol)

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
        if not self.mt5:
            return None

        logger.debug(f"  🔍 Looking up ticket for {broker_symbol} from MT5...")
        open_positions = self.mt5.get_positions(symbol=broker_symbol)
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
        if not is_dry_run and self.mt5 and self.mt5.is_connected():
            ticket = getattr(position, "ticket", None)
            if not ticket and position.metadata:
                ticket = position.metadata.get("ticket")

            if ticket:
                mt5_tickets = {p.get("ticket") for p in self.mt5.get_positions() if p.get("ticket")}
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
                    f"This is an ORPHANED position. Check _manage_positions sync logic."
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
        if not is_dry_run and self.mt5 and self.mt5.is_connected():
            if await self._close_if_missing_from_mt5(position, is_dry_run):
                return  # Position was closed (no longer in MT5)

        # Re-check after MT5 verification
        if not position.is_open:
            logger.debug(f"  ⚠️ Position {position.position_id} closed during MT5 check - skipping")
            return

        # 3. Get current price
        current_price = await self._get_current_price(position.symbol)
        if current_price is None:
            logger.debug(
                f"  ⚠️ Could not get current price for {position.symbol} - skipping update"
            )
            return

        # 4. Update + persist
        self.position_manager.update_position(position.position_id, current_price)
        logger.debug(
            f"  ✅ Updated {position.position_id} ({position.symbol}): "
            f"price={current_price:.5f}, profit={position.current_profit_pips:.1f} pips"
        )
        await self.position_manager.save_position(position, is_dry_run=is_dry_run)

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

        mt5_positions = self.mt5.get_positions()
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
        positions for symbols enabled in self.symbols.
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
            universal_symbol = self._broker_to_universal_symbol(broker_symbol)

            # Skip if symbol is not in our watchlist
            if universal_symbol not in self.symbols:
                continue

            logger.info(f"  🔄 Syncing MT5 position {mt5_ticket} ({broker_symbol}) to database...")
            try:
                position = self._build_position_from_mt5(universal_symbol, mt5_pos)
                self.position_manager.update_position(position.position_id, position.current_price)
                await self.position_manager.save_position(position, is_dry_run=is_dry_run)
                logger.info(
                    f"  ✅ Synced MT5 position {mt5_ticket} ({universal_symbol}) to database"
                )
            except Exception as e:
                logger.error(f"  ❌ Failed to sync MT5 position {mt5_ticket}: {e}", exc_info=True)

    def _broker_to_universal_symbol(self, broker_symbol: str) -> str:
        """Convert broker symbol to universal format, with fallback to suffix-strip."""
        if not self.symbol_mapper:
            return broker_symbol
        try:
            return self.symbol_mapper.convert_to_universal_symbol(broker_symbol, self.active_broker)
        except Exception:
            return broker_symbol.rstrip("cmCM")

    def _build_position_from_mt5(self, universal_symbol: str, mt5_pos: dict) -> "Position":
        """Construct a Position from MT5 position dict for DB sync."""
        from .position.position_models import Position, PositionStatus, PositionType

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
        current_price = await self._get_current_price(position.symbol)
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
        deal = self.mt5.get_history_deal(ticket)
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
        """
        # Close in position_manager state
        result = self.position_manager.close_position(
            position.position_id, close_price, reason.value
        )
        if result:
            result["pnl_usd"] = pnl

        # Persist to DB
        await self.position_manager.save_position(position, is_dry_run=is_dry_run)

        # Update session aggregations
        await self._update_session_on_position_close(position, result)

        if log_comment:
            logger.debug(f"  📝 Close context for {position.position_id}: {log_comment}")

        # Update portfolio balance with realized P&L
        if self.portfolio_risk and pnl:
            self.portfolio_risk.update_balance(self.portfolio_risk.current_balance + pnl)

        # Release exposure slot
        if self.exposure_manager:
            asset_class = self._get_asset_class(position.symbol)
            self.exposure_manager.unregister_position(position.symbol, asset_class, position.volume)

    async def _manage_positions(self):
        """Update and manage all open positions."""
        try:
            if not self.position_manager:
                return

            # Get current prices for all symbols with open positions
            open_positions = self.position_manager.get_open_positions()
            if not open_positions:
                return

            # --- POSITION RECONCILIATION ---
            # Check if positions still exist in MT5 (only for live trading)
            is_dry_run = self.config.get("trading", {}).get(
                "dry_run", False
            )  # Default to False for live trading
            if not is_dry_run and self.mt5 and self.mt5.is_connected():
                logger.debug(f"  🔍 Reconciliating {len(open_positions)} positions with MT5...")
                mt5_positions = self.mt5.get_positions()
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
                        if self.symbol_mapper:
                            try:
                                broker_symbol = self.symbol_mapper.convert_to_broker_symbol(
                                    position.symbol, self.active_broker
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
                        current_price = await self._get_current_price(position.symbol)
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
                        )
                        logger.info(f"  ✅ Synced Close: {position.position_id} | P&L: ${pnl:.2f}")
                        continue
                    # Case 2: Position has NO ticket - check if symbol exists in MT5
                    broker_symbol = self._convert_to_broker_symbol_safe(position.symbol)
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
            open_positions = self.position_manager.get_open_positions()
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

    async def _get_current_price(self, symbol):
        """Get current price for a symbol."""
        try:
            # Convert broker symbol to universal symbol for checking
            universal_symbol = symbol
            if self.symbol_mapper:
                try:
                    # Try to convert broker symbol back to universal
                    universal_symbol = self.symbol_mapper.convert_to_universal_symbol(
                        symbol, self.active_broker
                    )
                except Exception:
                    # If conversion fails, use symbol as-is (might already be universal)
                    universal_symbol = symbol.rstrip("cmCM")  # Remove broker suffixes as fallback

            # Skip disabled symbols (not in enabled symbols list)
            if universal_symbol not in self.symbols:
                logger.debug(
                    f"Skipping price update for disabled symbol: {symbol} (universal: {universal_symbol})"
                )
                return None

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
                # Pass enabled symbols to prevent validating/enabling disabled symbols
                data = self.data_manager.get_ohlcv(
                    symbol=broker_symbol,
                    timeframe="M1",
                    count=1,  # Use M1 for current price
                    enabled_symbols=self.symbols,  # Only validate/enable symbols in this list
                )

                if data is not None and not data.empty:
                    return float(data["close"].iloc[-1])

            # Fallback: only simulate price in dry-run/mock mode
            is_dry_run = self.config.get("trading", {}).get(
                "dry_run", False
            )  # Default to False for live trading
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
        """Check and apply automation features (breakeven, trailing, partial close) for a position."""
        try:
            is_dry_run = self.config.get("trading", {}).get("dry_run", False)

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

    # Max sane SL movement per trailing update (sanity check against bad pip_size data)
    _MAX_TRAILING_MOVEMENT_PIPS: dict[str, float] = {
        "forex_major": 500.0,
        "forex_jpy": 5000.0,
        "commodities": 10000.0,
        "crypto": 1000.0,
    }

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
        if not self.trailing_manager.should_update_trailing_stop(position):
            return False

        old_sl = position.stop_loss
        new_sl = self.trailing_manager.update_trailing_stop(position)
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
        asset_class = self._get_asset_class(position.symbol)
        max_allowed = self._MAX_TRAILING_MOVEMENT_PIPS.get(asset_class, 1000.0)

        if sl_movement_pips > max_allowed:
            logger.error(
                f"  ❌ SUSPICIOUS TRAILING MOVEMENT: {position.position_id} "
                f"({position.symbol})\n"
                f"     SL: {old_sl:.5f} → {new_sl:.5f}\n"
                f"     Movement: {sl_movement_pips:.1f} pips (max allowed: {max_allowed:.1f})\n"
                f"     pip_size: {position.pip_size}, current_price: {position.current_price}\n"
                f"     This suggests incorrect old_sl or pip_size - skipping notification"
            )
            await self.position_manager.save_position(position, is_dry_run=is_dry_run)
            return True  # Skip partial close too (orig early-return semantics)

        # Sync new SL with MT5 (live only)
        mt5_modified = False
        if not is_dry_run and self.mt5 and self.mt5.is_connected():
            broker_symbol = self._convert_to_broker_symbol_safe(position.symbol)
            ticket = self._resolve_mt5_ticket(position, broker_symbol)

            if ticket:
                res = self.mt5.modify_position(ticket=ticket, sl=new_sl, tp=position.take_profit)
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
        await self.position_manager.save_position(position, is_dry_run=is_dry_run)
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
        ts_should_activate = self.trailing_manager.should_activate_trailing(position)
        logger.debug(
            f"  Trailing activation check for {position.position_id}: "
            f"should_activate={ts_should_activate}, "
            f"profit={position.current_profit_pips:.1f} pips, "
            f"already_active={position.position_id in self.trailing_manager.trailing_active}"
        )
        if not ts_should_activate:
            return

        self.trailing_manager.activate_trailing(position)
        logger.info(
            f"  🎯 TRAILING ACTIVATED: {position.position_id} at "
            f"{position.current_profit_pips:.1f} pips"
        )
        await self.position_manager.save_position(position, is_dry_run=is_dry_run)

        if not is_dry_run and self.notification_manager:
            await self.notification_manager.send_message(
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
            if self.mt5 and self.mt5.is_connected():
                logger.warning(
                    f"  ⚠️ Not sending notification for {position.position_id}: "
                    f"MT5 update failed or no ticket found"
                )
            return

        if not self.notification_manager:
            return

        try:
            await self.notification_manager.send_message(
                f"🔄 **TRAILING STOP UPDATED**\n"
                f"📊 Symbol: `{position.symbol}`\n"
                f"🆔 Position: `{position.position_id}`\n"
                f"🛑 SL: `{old_sl:.5f}` → `{new_sl:.5f}`\n"
                f"📈 Movement: `{sl_movement_pips:.1f} pips`\n"
                f"💰 Profit: `{position.current_profit_pips:.1f} pips`\n"
                f"💵 P&L: `${position.current_pnl_usd:.2f}`\n"
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
        if not self.partial_manager.should_close_partial(position):
            return

        current_price = await self._get_current_price(position.symbol)

        try:
            result = self.partial_manager.execute_partial_close(position, current_price)
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
        if not is_dry_run and self.mt5 and self.mt5.is_connected():
            broker_symbol = self._convert_to_broker_symbol_safe(position.symbol)
            ticket = self._resolve_mt5_ticket(position, broker_symbol)

            if ticket:
                mt5_result = self.mt5.close_position(
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
            f"P&L: ${result['profit_usd']:.2f}"
        )
        await self.position_manager.save_position(position, is_dry_run=is_dry_run)

        # Send notification (live only)
        if not is_dry_run and self.notification_manager:
            await self.notification_manager.send_message(
                f"💰 **PARTIAL PROFIT TAKEN**\n"
                f"🆔 `{position.position_id}`\n"
                f"📊 Closed: `{closed_volume:.3f}` lots\n"
                f"💵 Profit: **${result['profit_usd']:.2f}**",
                level=NotificationLevel.SUCCESS,
            )

    async def _handle_breakeven_automation(self, position, is_dry_run: bool) -> None:
        """Move SL to breakeven once profit threshold reached.

        Side effects:
            - Modifies SL via MT5 modify_position (live trading)
            - Saves position to DB
            - Sends Telegram notification (live only, once - deduplicates re-triggers)
        """
        be_should_move = self.breakeven_manager.should_move_to_breakeven(position)
        logger.debug(
            f"  Breakeven check for {position.position_id}: should_move={be_should_move}, "
            f"profit={position.current_profit_pips:.1f} pips"
        )

        if not be_should_move:
            return

        new_sl = self.breakeven_manager.move_to_breakeven(position)
        if not new_sl:
            return

        # MT5 modification only for live trading
        if not is_dry_run and self.mt5 and self.mt5.is_connected():
            broker_symbol = self._convert_to_broker_symbol_safe(position.symbol)
            ticket = self._resolve_mt5_ticket(position, broker_symbol)
            mt5_modified = False
            res: dict = {}
            if ticket:
                logger.debug(
                    f"  🔧 Modifying MT5 position {ticket}: "
                    f"SL={new_sl:.5f}, TP={position.take_profit:.5f}"
                )
                res = self.mt5.modify_position(ticket=ticket, sl=new_sl, tp=position.take_profit)
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
            is_already_at_breakeven = self.breakeven_manager.is_at_breakeven(position.position_id)

            # Save + notify based on state
            if mt5_modified and not is_already_at_breakeven:
                logger.info(f"  🔄 BREAKEVEN: {position.position_id} SL moved to {new_sl:.5f}")
                await self.position_manager.save_position(position, is_dry_run=is_dry_run)
                logger.info(f"  💾 Breakeven SL saved to database: {new_sl:.5f}")
                if self.notification_manager:
                    await self.notification_manager.send_message(
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
                await self.position_manager.save_position(position, is_dry_run=is_dry_run)
                logger.debug("  💾 Position saved to database (already at breakeven)")
            else:
                # MT5 not modified (failed or already set)
                await self.position_manager.save_position(position, is_dry_run=is_dry_run)
                logger.debug(
                    f"  💾 Position saved (MT5 not modified: "
                    f"{res.get('message') if ticket else 'no ticket'})"
                )
        elif is_dry_run:
            # Dry-run: save to DB but skip MT5 + notification
            logger.info(
                f"  🔄 BREAKEVEN (DRY-RUN): {position.position_id} " f"SL moved to {new_sl:.5f}"
            )
            await self.position_manager.save_position(position, is_dry_run=is_dry_run)
            logger.info("  💾 Breakeven SL saved to database (dry-run, no notification)")

    async def _check_position_closure(self):
        """Check for stop loss and take profit hits."""
        try:
            if not self.data_manager:
                return

            # Get dry-run mode
            is_dry_run = self.config.get("trading", {}).get("dry_run", False)

            open_positions = self.position_manager.get_open_positions()
            for position in open_positions:
                try:
                    # Get current price
                    current_price = await self._get_current_price(position.symbol)
                    if current_price is None:
                        continue

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
                        result = self.position_manager.close_position(
                            position.position_id, current_price, close_reason.value
                        )

                        if result:
                            # Unregister from exposure manager
                            asset_class = self._get_asset_class(position.symbol)
                            self.exposure_manager.unregister_position(
                                position.symbol, asset_class, position.volume
                            )

                            # Update portfolio risk
                            self.portfolio_risk.update_balance(
                                self.portfolio_risk.current_balance + result["pnl_usd"]
                            )

                            # Save closed state to database
                            await self.position_manager.save_position(
                                position, is_dry_run=is_dry_run
                            )

                            # Update session aggregations
                            await self._update_session_on_position_close(position, result)

                            logger.info(
                                f"  ✅ POSITION CLOSED: {position.position_id} | "
                                f"{close_reason.value} | "
                                f"P&L: ${result['pnl_usd']:.2f} | "
                                f"Pips: {result['pips']:.1f}"
                            )

                            # Determine emoji based on profit
                            pnl_emoji = "💰" if result["pnl_usd"] > 0 else "💸"

                            await self.notification_manager.send_message(
                                f"{pnl_emoji} **POSITION CLOSED**\n"
                                f"🆔 `{position.position_id}`\n"
                                f"📝 Reason: `{close_reason.value}`\n"
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
                # CRITICAL: Sync balance from MT5 on every loop iteration
                # This ensures we always use the correct balance for position sizing
                await self._sync_balance_from_mt5()

                # CRITICAL: Verify MT5 server hasn't changed (prevent auto-switch)
                if self.mt5 and not self.config.get("trading", {}).get("dry_run", False):
                    health = self.mt5.health_check()
                    if not health.get("server_match", True):
                        logger.error(
                            f"🚨 CRITICAL: MT5 server changed to '{health.get('current_server')}' "
                            f"(expected '{health.get('expected_server')}'). "
                            f"Stopping bot to prevent trading on wrong server!"
                        )
                        # Send emergency notification
                        if self.notification_manager:
                            await self.notification_manager.send_message(
                                f"🚨 **CRITICAL: Server Mismatch Detected!**\n"
                                f"Expected: `{health.get('expected_server')}`\n"
                                f"Current: `{health.get('current_server')}`\n"
                                f"⚠️ Bot stopped to prevent trading on wrong server.",
                                level=NotificationLevel.ERROR,
                            )
                        # Stop the bot
                        self.is_running = False
                        break

                logger.info(
                    f"🔄 Trading loop iteration - analyzing {len(self.symbols)} symbol(s) in PARALLEL"
                )

                # Analyze all symbols in parallel using asyncio.gather
                # This ensures all symbols are analyzed simultaneously instead of sequentially
                # Benefits:
                # - XAUUSD won't be delayed by other symbols
                # - All symbols get equal processing time
                # - Faster overall analysis (limited by slowest symbol, not sum of all)
                try:
                    # Create analysis tasks for all symbols
                    analysis_tasks = [self._analyze_symbol(symbol) for symbol in self.symbols]

                    # Run all tasks in parallel and capture exceptions
                    results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

                    # Log any errors that occurred during analysis
                    for symbol, result in zip(self.symbols, results, strict=False):
                        if isinstance(result, Exception):
                            logger.error(f"Error analyzing {symbol}: {result}")

                except Exception as e:
                    logger.error(f"Error in parallel analysis: {e}")

                # Update and manage positions
                await self._manage_positions()

                # Wait before next analysis
                logger.info(f"⏳ Waiting {self.analysis_interval}s before next analysis cycle...")
                await asyncio.sleep(self.analysis_interval)

            except KeyboardInterrupt:
                logger.info("Received stop signal")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                # Notify critical error
                if self.notification_manager:
                    await self.notification_manager.send_message(
                        f"❌ **CRITICAL ERROR**\nError in trading loop:\n`{str(e)}`",
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
        """Check if market is open for the symbol. Delegates to utils.market_hours."""
        from .utils.market_hours import is_market_open

        return is_market_open(self._get_asset_class(symbol))

    def _generate_mock_data(self, symbol: str, timeframe: str, count: int = 100):
        """Generate mock OHLCV data for dry-run. Delegates to utils.mock_data."""
        from .utils.mock_data import generate_mock_ohlcv

        return generate_mock_ohlcv(symbol, timeframe, count)

    async def _analyze_symbol(self, symbol: str):
        """Analyze a symbol using the strategy system and execute resulting signals.

        Args:
            symbol: Trading symbol (internal/universal format)
        """
        # Pre-flight: skip if market closed
        if not self._is_market_open(symbol):
            logger.debug(f"Skipping {symbol}: Market closed (Weekend)")
            return

        try:
            broker_symbol = self._convert_to_broker_symbol(symbol)
            is_dry_run = self.config.get("trading", {}).get("dry_run", False)
            is_mock_mode = self.mt5 is None

            # Run strategy analysis (MTF or single TF)
            strategy_results = await self._run_strategy_analysis(
                symbol, broker_symbol, is_dry_run, is_mock_mode
            )

            if not strategy_results:
                logger.debug(f"{symbol}: No strategy results generated")
                return

            logger.info(f"📊 {symbol}: Received {len(strategy_results)} results")

            # Aggregate and execute signals
            signals = await self.signal_aggregator.aggregate_signals(strategy_results)
            if not signals:
                logger.debug(f"{symbol}: No valid signals after aggregation")
                return

            logger.info(f"✅ {symbol}: Generated {len(signals)} trading signals")
            for signal in signals:
                await self._execute_signal(signal)

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)

    def _convert_to_broker_symbol(self, symbol: str) -> str:
        """Convert internal symbol to broker-specific format (e.g., EURUSD → EURUSDc)."""
        if not self.symbol_mapper:
            logger.debug(f"🔍 Analyzing {symbol}...")
            return symbol
        try:
            broker_symbol = self.symbol_mapper.convert_to_broker_symbol(symbol, self.active_broker)
            logger.debug(f"🔍 Analyzing {symbol} (broker: {broker_symbol})...")
            return broker_symbol
        except Exception as e:
            logger.warning(f"Failed to convert symbol {symbol} to broker format: {e} - using as-is")
            return symbol

    async def _run_strategy_analysis(
        self, symbol: str, broker_symbol: str, is_dry_run: bool, is_mock_mode: bool
    ) -> list:
        """Dispatch to MTF or single-TF strategy analysis based on mode."""
        if self.mtf_mode and self.mtf_analyzer:
            return await self._run_mtf_analysis(symbol, broker_symbol, is_dry_run, is_mock_mode)
        return await self._run_single_tf_analysis(symbol, broker_symbol, is_dry_run, is_mock_mode)

    async def _run_mtf_analysis(
        self, symbol: str, broker_symbol: str, is_dry_run: bool, is_mock_mode: bool
    ) -> list:
        """Fetch Zone TF + Entry TF data and run MTF analyzer."""
        zone_data, entry_data = self._fetch_mtf_data(
            symbol, broker_symbol, is_dry_run, is_mock_mode
        )
        if zone_data is None or zone_data.empty or entry_data is None or entry_data.empty:
            logger.warning(f"Insufficient data for MTF analysis of {symbol}")
            return []
        return await self.mtf_analyzer.analyze(
            symbol=symbol,
            zone_tf_data=zone_data,
            entry_tf_data=entry_data,
            zone_tf=self.zone_timeframe,
            entry_tf=self.entry_timeframe,
        )

    def _fetch_mtf_data(
        self, symbol: str, broker_symbol: str, is_dry_run: bool, is_mock_mode: bool
    ) -> tuple:
        """Fetch (zone_data, entry_data) from MT5 or generate mock data."""
        zone_data = None
        entry_data = None

        if self.data_manager and not is_dry_run and not is_mock_mode:
            try:
                zone_data = self.data_manager.get_ohlcv(
                    symbol=broker_symbol,
                    timeframe=self.zone_timeframe,
                    count=200,
                    enabled_symbols=self.symbols,
                )
                entry_data = self.data_manager.get_ohlcv(
                    symbol=broker_symbol,
                    timeframe=self.entry_timeframe,
                    count=100,
                    enabled_symbols=self.symbols,
                )
            except Exception as e:
                logger.warning(f"Error fetching real data for {symbol}: {e}")
                if not is_dry_run:
                    return None, None

        # Fallback to mock data for dry-run/mock modes
        if (zone_data is None or entry_data is None) and (is_dry_run or is_mock_mode):
            logger.debug(f"Generating MTF mock data for {symbol}")
            zone_data = self._generate_mock_data(symbol, self.zone_timeframe, count=200)
            entry_data = self._generate_mock_data(symbol, self.entry_timeframe, count=100)

        return zone_data, entry_data

    async def _run_single_tf_analysis(
        self, symbol: str, broker_symbol: str, is_dry_run: bool, is_mock_mode: bool
    ) -> list:
        """Fetch single timeframe data and run legacy strategy_manager analysis."""
        data = None

        if self.data_manager and not is_dry_run and not is_mock_mode:
            try:
                data = self.data_manager.get_ohlcv(
                    symbol=broker_symbol,
                    timeframe=self.timeframe,
                    count=100,
                    enabled_symbols=self.symbols,
                )
            except Exception as e:
                logger.warning(f"Error fetching real data for {symbol}: {e}")
                if not is_dry_run:
                    return []

        if data is None and (is_dry_run or is_mock_mode):
            logger.debug(f"Generating mock data for {symbol} ({self.timeframe})")
            data = self._generate_mock_data(symbol, self.timeframe)

        if data is None or data.empty:
            logger.warning(f"No data available for {symbol}")
            return []

        return await self.strategy_manager.analyze_symbol(symbol, data, self.timeframe)
