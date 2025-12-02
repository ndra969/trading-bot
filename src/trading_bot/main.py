"""
Main trading bot orchestrator.

Coordinates all trading components and manages the trading loop.
"""

import asyncio

from .connectors.data_manager import DataManager
from .connectors.mt5_connector import MT5Connector
from .connectors.symbol_mapper import SymbolMapper
from .strategies.foundation.foundation_engine import FoundationEngine
from .utils.logger import get_logger

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

        # Trading symbols (internal/universal format)
        self.symbols: list[str] = config.get("symbols", ["EURUSD", "GBPUSD"])
        self.timeframe = config.get("timeframe", "H1")
        self.analysis_interval = config.get("analysis_interval", 300)  # 5 minutes

        logger.info(f"TradingBot initialized for symbols: {self.symbols}")

    async def start(self):
        """Start trading bot."""
        logger.info("🚀 Starting trading bot...")

        try:
            # Initialize MT5 connection (skip if already set from CLI)
            if self.mt5 is None:
                try:
                    await self._initialize_mt5()
                except Exception as e:
                    logger.warning(f"MT5 initialization failed: {e} - continuing without MT5")
                    # Create mock data manager for dry-run
                    # Skip data manager initialization if MT5 not available
                    logger.warning("MT5 not available - data manager will not be initialized")
                    self.data_manager = None

            # Initialize foundation strategy
            await self._initialize_foundation_strategy()

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

    async def _trading_loop(self):
        """Main trading loop."""
        logger.info("📊 Starting main trading loop...")

        while self.is_running:
            try:
                # Analyze each symbol
                for symbol in self.symbols:
                    await self._analyze_symbol(symbol)

                # Wait before next analysis
                logger.debug(f"Waiting {self.analysis_interval}s before next analysis...")
                await asyncio.sleep(self.analysis_interval)

            except KeyboardInterrupt:
                logger.info("Received stop signal")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _analyze_symbol(self, symbol: str):
        """
        Analyze a symbol using foundation strategy.

        Args:
            symbol: Trading symbol (internal/universal format)
        """
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

            # Analyze with foundation strategy (use internal symbol for logging/storage)
            zones = await self.foundation_engine.analyze_symbol(symbol, data, self.timeframe)

            # Log results
            if zones:
                logger.info(f"✅ {symbol} ({broker_symbol}): Found {len(zones)} high-quality zones")
                for i, zone in enumerate(zones[:3], 1):  # Log top 3 zones
                    logger.info(
                        f"  Zone {i}: {zone.zone_type.value} | "
                        f"{zone.lower_bound:.5f}-{zone.upper_bound:.5f} | "
                        f"Strength: {zone.strength:.1f}"
                    )
            else:
                logger.debug(f"{symbol} ({broker_symbol}): No high-quality zones detected")

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
