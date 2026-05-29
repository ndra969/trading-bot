"""
Main trading bot orchestrator.

Coordinates all trading components and manages the trading loop.
"""

import asyncio
from datetime import UTC, datetime

from trading_core.utils.logger import get_logger

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
from .services.execution_service import ExecutionService
from .services.position_orchestrator import PositionOrchestrator
from .strategies.foundation.foundation_engine import FoundationEngine
from .strategies.signal_aggregator import SignalAggregator
from .strategies.strategy_manager import StrategyManager
from .utils.config_validator import validate_position_management_config
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

        # Service layer
        self.execution_service: ExecutionService | None = None
        self.position_orchestrator: PositionOrchestrator | None = None

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

        # Account type detection — derive from broker name. Cent accounts use
        # 1/100 lot sizing and report balances/P&L in the cent currency (USC).
        # The math is unit-consistent so bot calculations are fine, but display
        # labels and recorded values need the right unit suffix to be readable.
        self.is_cent_account = bool(self.active_broker and "cent" in self.active_broker.lower())
        self.account_currency_unit = "USC" if self.is_cent_account else "USD"
        logger.info(
            f"📊 Account type: {'CENT' if self.is_cent_account else 'STANDARD'} "
            f"(display unit: {self.account_currency_unit}, broker: {self.active_broker})"
        )

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
        """Initialize MT5 connection.

        Used as a fallback when CLI didn't successfully create + initialize the
        MT5Connector (e.g., live mode but CLI's initialize() failed). Pulls
        credentials from the loaded config rather than assuming defaults.
        """
        logger.info("Initializing MT5 connection...")

        # If MT5 already set (from CLI), use it
        if self.mt5 is None:
            mt5_cfg = self.config.get("mt5", {}) if isinstance(self.config, dict) else {}
            self.mt5 = MT5Connector(
                terminal_path=mt5_cfg.get("terminal_path"),
                login=mt5_cfg.get("login"),
                password=mt5_cfg.get("password"),
                server=mt5_cfg.get("server"),
                timeout=mt5_cfg.get("connection_timeout", 30),
            )

            # MT5Connector.initialize() is synchronous and returns bool
            if not self.mt5.initialize():
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
            from trading_core.data import get_session

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
            from trading_core.data.services.account_selector import AccountSelector

            from trading_worker.services.account_sync_service import AccountSyncService

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
            from trading_core.data.repositories.config_repository import ConfigRepository
            from trading_core.data.repositories.session_repository import SessionRepository
            from trading_core.utils.config_hasher import hash_config

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

            # Step 4b: Close any sessions left ACTIVE by previous crashes.
            # Bot may have been killed without graceful shutdown; those
            # sessions stay ACTIVE forever otherwise.
            if account_id is not None:
                closed = await self.session_repository.close_abandoned_sessions(
                    account_id=account_id, ending_balance=starting_balance
                )
                if closed > 0:
                    logger.info(f"🧹 Closed {closed} abandoned session(s) from previous runs")

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

            # Initialize execution service (depends on position_manager, portfolio_risk,
            # exposure_manager, drawdown_protector — all set up above)
            self.execution_service = ExecutionService(self)

            # Position reconciliation + automation (same deps as ExecutionService)
            self.position_orchestrator = PositionOrchestrator(self)

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
                        f"💰 Balance updated: {current_balance:,.2f} → {mt5_balance:,.2f} "
                        f"{self.account_currency_unit} "
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

    def _get_asset_class(self, symbol):
        """Determine asset class from symbol. Delegates to SymbolResolver."""
        return self._symbol_resolver.get_asset_class(symbol)

    def _convert_broker_to_internal_symbol(self, symbol):
        """Convert broker symbol to internal format. Delegates to SymbolResolver."""
        return self._symbol_resolver.convert_broker_to_internal_symbol(symbol)

    def _broker_to_universal_symbol(self, broker_symbol: str) -> str:
        """Convert broker symbol to universal format, with fallback to suffix-strip."""
        if not self.symbol_mapper:
            return broker_symbol
        try:
            return self.symbol_mapper.convert_to_universal_symbol(broker_symbol, self.active_broker)
        except Exception:
            return broker_symbol.rstrip("cmCM")

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

    # Max sane SL movement per trailing update (sanity check against bad pip_size data)
    _MAX_TRAILING_MOVEMENT_PIPS: dict[str, float] = {
        "forex_major": 500.0,
        "forex_jpy": 5000.0,
        "commodities": 10000.0,
        "crypto": 1000.0,
    }

    async def _finalize_max_duration_close(self, position, is_dry_run: bool) -> None:
        """Finalise a max-duration auto-close: MT5 close, DB save, notify.

        position_manager._check_max_duration has already marked the position
        CLOSED in memory (and set close_reason=MAX_DURATION). This routine
        carries out the side effects MT5 + DB need.
        """
        # Mirror SL/TP close finalisation: compute realized P&L from tracker
        # (already set by close_position via _check_max_duration).
        pnl_usd = position.current_pnl_usd or 0.0
        pips = position.current_profit_pips or 0.0

        # Close the position on MT5 too (we initiated this, MT5 won't otherwise)
        if not is_dry_run and self.mt5 and self.mt5.is_connected():
            broker_symbol = self._convert_to_broker_symbol_safe(position.symbol)
            ticket = self._resolve_mt5_ticket(position, broker_symbol)
            if ticket:
                try:
                    self.mt5.close_position(
                        ticket=ticket,
                        volume=position.volume,
                        comment=f"MaxDuration {position.position_id}",
                    )
                except Exception as e:
                    logger.error(
                        f"  ❌ MT5 close failed for max-duration on {position.position_id}: {e}"
                    )

        # Unregister exposure
        asset_class = self._get_asset_class(position.symbol)
        self.exposure_manager.unregister_position(position.symbol, asset_class, position.volume)

        # Update portfolio balance with realized P&L
        self.portfolio_risk.update_balance(self.portfolio_risk.current_balance + pnl_usd)

        # Persist + session aggregation
        await self.position_manager.save_position(position, is_dry_run=is_dry_run)
        await self._update_session_on_position_close(position, {"pnl_usd": pnl_usd, "pips": pips})

        logger.info(
            f"  ⏰ POSITION CLOSED (MAX DURATION): {position.position_id} | "
            f"P&L: {pnl_usd:.2f} {self.account_currency_unit} | Pips: {pips:.1f}"
        )

        if self.notification_manager:
            pnl_emoji = "💰" if pnl_usd > 0 else "💸"
            await self.notification_manager.send_message(
                f"{pnl_emoji} **POSITION CLOSED (Max Duration)**\n"
                f"🆔 `{position.position_id}`\n"
                f"⏰ Reason: Max duration reached in profit\n"
                f"💵 P&L: **{pnl_usd:.2f} {self.account_currency_unit}**\n"
                f"📏 Pips: `{pips:.1f}`",
                level=NotificationLevel.SUCCESS,
            )

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
                await self.position_orchestrator.manage_positions()

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
        """Check market open (weekend + per-symbol session filter)."""
        from .utils.market_hours import is_market_open

        asset_class = self._get_asset_class(symbol)
        # Per-symbol allowed sessions from active_symbols.yaml. When absent,
        # only the weekend rule applies (legacy behaviour).
        symbol_cfg = self.config.get("symbols", {}).get(symbol, {})
        allowed_sessions = symbol_cfg.get("trading_sessions")
        return is_market_open(asset_class, allowed_sessions=allowed_sessions)

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
                await self.execution_service.execute_signal(signal)

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
