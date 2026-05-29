"""
Analysis Service — per-symbol strategy + MTF analysis.

Extracted from TradingBot (back-reference pattern): detects signals and hands
them to ``self.bot.execution_service`` to act on. The only public entry point
is :meth:`analyze_symbol`, called from ``TradingBot._trading_loop``.
"""

from typing import TYPE_CHECKING

from trading_core.utils.logger import get_logger

if TYPE_CHECKING:
    from trading_worker.main import TradingBot

logger = get_logger(__name__)


class AnalysisService:
    def __init__(self, bot: "TradingBot"):
        self.bot = bot

    async def analyze_symbol(self, symbol: str):
        """Analyze a symbol using the strategy system and execute resulting signals.

        Args:
            symbol: Trading symbol (internal/universal format)
        """
        # Pre-flight: skip if market closed
        if not self.bot._is_market_open(symbol):
            logger.debug(f"Skipping {symbol}: Market closed (Weekend)")
            return

        try:
            broker_symbol = self.bot._convert_to_broker_symbol(symbol)
            is_dry_run = self.bot.config.get("trading", {}).get("dry_run", False)
            is_mock_mode = self.bot.mt5 is None

            # Run strategy analysis (MTF or single TF)
            strategy_results = await self._run_strategy_analysis(
                symbol, broker_symbol, is_dry_run, is_mock_mode
            )

            if not strategy_results:
                logger.debug(f"{symbol}: No strategy results generated")
                return

            logger.info(f"📊 {symbol}: Received {len(strategy_results)} results")

            # Aggregate and execute signals
            signals = await self.bot.signal_aggregator.aggregate_signals(strategy_results)
            if not signals:
                logger.debug(f"{symbol}: No valid signals after aggregation")
                return

            logger.info(f"✅ {symbol}: Generated {len(signals)} trading signals")
            for signal in signals:
                await self.bot.execution_service.execute_signal(signal)

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)

    async def _run_strategy_analysis(
        self, symbol: str, broker_symbol: str, is_dry_run: bool, is_mock_mode: bool
    ) -> list:
        """Dispatch to MTF or single-TF strategy analysis based on mode."""
        if self.bot.mtf_mode and self.bot.mtf_analyzer:
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
        return await self.bot.mtf_analyzer.analyze(
            symbol=symbol,
            zone_tf_data=zone_data,
            entry_tf_data=entry_data,
            zone_tf=self.bot.zone_timeframe,
            entry_tf=self.bot.entry_timeframe,
        )

    def _fetch_mtf_data(
        self, symbol: str, broker_symbol: str, is_dry_run: bool, is_mock_mode: bool
    ) -> tuple:
        """Fetch (zone_data, entry_data) from MT5 or generate mock data."""
        zone_data = None
        entry_data = None

        if self.bot.data_manager and not is_dry_run and not is_mock_mode:
            try:
                zone_data = self.bot.data_manager.get_ohlcv(
                    symbol=broker_symbol,
                    timeframe=self.bot.zone_timeframe,
                    count=200,
                    enabled_symbols=self.bot.symbols,
                )
                entry_data = self.bot.data_manager.get_ohlcv(
                    symbol=broker_symbol,
                    timeframe=self.bot.entry_timeframe,
                    count=100,
                    enabled_symbols=self.bot.symbols,
                )
            except Exception as e:
                logger.warning(f"Error fetching real data for {symbol}: {e}")
                if not is_dry_run:
                    return None, None

        # Fallback to mock data for dry-run/mock modes
        if (zone_data is None or entry_data is None) and (is_dry_run or is_mock_mode):
            logger.debug(f"Generating MTF mock data for {symbol}")
            zone_data = self.bot._generate_mock_data(symbol, self.bot.zone_timeframe, count=200)
            entry_data = self.bot._generate_mock_data(symbol, self.bot.entry_timeframe, count=100)

        return zone_data, entry_data

    async def _run_single_tf_analysis(
        self, symbol: str, broker_symbol: str, is_dry_run: bool, is_mock_mode: bool
    ) -> list:
        """Fetch single timeframe data and run legacy strategy_manager analysis."""
        data = None

        if self.bot.data_manager and not is_dry_run and not is_mock_mode:
            try:
                data = self.bot.data_manager.get_ohlcv(
                    symbol=broker_symbol,
                    timeframe=self.bot.timeframe,
                    count=100,
                    enabled_symbols=self.bot.symbols,
                )
            except Exception as e:
                logger.warning(f"Error fetching real data for {symbol}: {e}")
                if not is_dry_run:
                    return []

        if data is None and (is_dry_run or is_mock_mode):
            logger.debug(f"Generating mock data for {symbol} ({self.bot.timeframe})")
            data = self.bot._generate_mock_data(symbol, self.bot.timeframe)

        if data is None or data.empty:
            logger.warning(f"No data available for {symbol}")
            return []

        return await self.bot.strategy_manager.analyze_symbol(symbol, data, self.bot.timeframe)
