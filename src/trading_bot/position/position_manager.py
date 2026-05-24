"""
Position Manager - Main position management orchestrator.

Coordinates position lifecycle, tracking, and management.
"""

import uuid
from datetime import datetime

from sqlalchemy import select

from trading_bot.data.database import get_session
from trading_bot.data.models import Position as DBPosition
from trading_bot.position.automation.breakeven_manager import BreakevenManager
from trading_bot.position.automation.trailing_stop_manager import TrailingStopManager
from trading_bot.position.pip_calculator import PipCalculator
from trading_bot.position.position_models import Position, PositionStatus, PositionType
from trading_bot.position.position_tracker import PositionTracker
from trading_bot.strategies.models import TradingSignal
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class PositionManager:
    """
    Manages trading positions lifecycle.

    Responsibilities:
    - Create positions from trading signals
    - Track open positions
    - Update position prices in real-time
    - Close positions (manual or automatic)
    - Provide position summaries and reporting
    - Enforce position limits (1 per symbol)
    """

    def __init__(self, config: dict = None):
        """
        Initialize position manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.pip_calculator = PipCalculator()
        self.tracker = PositionTracker()

        # Automation managers
        self.breakeven_manager = BreakevenManager(config)
        self.trailing_stop_manager = TrailingStopManager(config)

        # Position storage
        self.positions: dict[str, Position] = {}  # position_id -> Position
        self.positions_by_symbol: dict[str, list[str]] = {}  # symbol -> list of position_ids

        # Get active trading type and its configuration
        trading_types = self.config.get("trading_types", {})
        active_type = (
            self.config.get("active_trading_type")
            or trading_types.get("active_trading_type")
            or "day_trading"
        )
        type_config = trading_types.get(active_type, {})

        # Configuration - PRIORITY: Trading Type Config > General Config > Default
        self.max_positions_per_symbol = type_config.get(
            "max_positions",
            self.config.get("position_manager", {}).get("max_positions_per_symbol", 1),
        )

        logger.info(
            f"PositionManager initialized with automation "
            f"(trading_type: {active_type}, max positions per symbol: {self.max_positions_per_symbol})"
        )

    async def load_positions_from_db(self):
        """Load active positions from database."""
        try:
            async with get_session() as session:
                db_positions = await self._query_active_db_positions(session)

                count = 0
                invalid_count = 0
                for db_pos in db_positions:
                    result = await self._load_single_position(db_pos, session)
                    if result == "loaded":
                        count += 1
                    else:
                        invalid_count += 1

                self._log_load_summary(count, invalid_count)

                if count > 0:
                    self._restore_automation_tracking()

        except Exception as e:
            logger.error(f"Error loading positions from database: {e}")

    async def _query_active_db_positions(self, session):
        """Query active (PENDING/OPEN) positions from database."""
        stmt = select(DBPosition).where(
            DBPosition.status.in_([PositionStatus.PENDING.value, PositionStatus.OPEN.value])
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def _load_single_position(self, db_pos, session) -> str:
        """Load and validate a single DB position.

        Returns:
            "loaded" if successfully loaded into memory, "invalid" otherwise.
        """
        try:
            metadata = db_pos.meta_data or {}
            position_type = PositionType(db_pos.position_type)
            position_status = PositionStatus(db_pos.status)

            if not self._validate_db_position_prices(db_pos, position_type, position_status):
                return "invalid"

            position = self._db_row_to_position(db_pos, metadata)
            self._load_position_ticket(position, db_pos, metadata)

            if await self._handle_orphaned_position(position, db_pos, session):
                return "invalid"

            self._register_position_in_memory(position)
            return "loaded"

        except ValueError as e:
            logger.warning(
                f"Skipping invalid position {db_pos.position_id} ({db_pos.symbol}): {e}"
            )
            return "invalid"
        except Exception as e:
            logger.error(
                f"Error loading position {db_pos.position_id} ({db_pos.symbol}): {e}",
                exc_info=True,
            )
            return "invalid"

    def _validate_db_position_prices(self, db_pos, position_type, position_status) -> bool:
        """Validate SL/TP prices based on position status.

        Returns:
            True if valid, False if invalid (caller should skip).
        """
        entry = db_pos.entry_price
        sl = db_pos.stop_loss
        tp = db_pos.take_profit

        if position_status == PositionStatus.PENDING:
            return self._validate_pending_sl_tp(db_pos, position_type, entry, sl, tp)
        elif position_status == PositionStatus.OPEN:
            return self._validate_open_sl_tp(db_pos, sl, tp)
        return True  # pragma: no cover - defensive (query filters to PENDING/OPEN only)

    def _validate_pending_sl_tp(self, db_pos, position_type, entry, sl, tp) -> bool:
        """Strict SL/TP validation for PENDING positions."""
        if position_type == PositionType.BUY:
            if sl >= entry:
                logger.warning(
                    f"Skipping invalid PENDING BUY position {db_pos.position_id} ({db_pos.symbol}): "
                    f"SL {sl:.5f} >= Entry {entry:.5f}"
                )
                return False
            if tp <= entry:
                logger.warning(
                    f"Skipping invalid PENDING BUY position {db_pos.position_id} ({db_pos.symbol}): "
                    f"TP {tp:.5f} <= Entry {entry:.5f}"
                )
                return False
        elif position_type == PositionType.SELL:
            if sl <= entry:
                logger.warning(
                    f"Skipping invalid PENDING SELL position {db_pos.position_id} ({db_pos.symbol}): "
                    f"SL {sl:.5f} <= Entry {entry:.5f}"
                )
                return False
            if tp >= entry:
                logger.warning(
                    f"Skipping invalid PENDING SELL position {db_pos.position_id} ({db_pos.symbol}): "
                    f"TP {tp:.5f} >= Entry {entry:.5f}"
                )
                return False
        return True

    def _validate_open_sl_tp(self, db_pos, sl, tp) -> bool:
        """Relaxed SL/TP validation for OPEN positions (breakeven allowed)."""
        if sl <= 0:
            logger.warning(
                f"Skipping invalid OPEN position {db_pos.position_id} ({db_pos.symbol}): "
                f"SL {sl:.5f} <= 0"
            )
            return False
        if tp <= 0:
            logger.warning(
                f"Skipping invalid OPEN position {db_pos.position_id} ({db_pos.symbol}): "
                f"TP {tp:.5f} <= 0"
            )
            return False
        return True

    def _db_row_to_position(self, db_pos, metadata) -> Position:
        """Convert DB row to Position object with all fields."""
        return Position(
            position_id=db_pos.position_id,
            symbol=db_pos.symbol,
            position_type=PositionType(db_pos.position_type),
            entry_price=db_pos.entry_price,
            stop_loss=db_pos.stop_loss,
            take_profit=db_pos.take_profit,
            volume=db_pos.volume,
            pip_size=db_pos.pip_size,
            pip_value_per_lot=db_pos.pip_value_per_lot,
            status=PositionStatus(db_pos.status),
            account_id=db_pos.account_id,
            asset_class=db_pos.asset_class,
            signal_id=db_pos.signal_id,
            strategy_id=db_pos.strategy_id,
            session_id=db_pos.session_id,
            open_time=db_pos.open_time,
            close_time=db_pos.close_time,
            close_price=db_pos.close_price,
            close_reason=db_pos.close_reason,
            exit_type=db_pos.exit_type,
            current_price=db_pos.current_price,
            current_profit_pips=db_pos.current_profit_pips,
            current_pnl_usd=db_pos.current_pnl_usd,
            risk_amount_usd=db_pos.risk_amount_usd,
            potential_profit_usd=db_pos.potential_profit_usd,
            is_winner=db_pos.is_winner,
            breakeven_activated=db_pos.breakeven_activated,
            trailing_activated=db_pos.trailing_activated,
            entry_to_sl_pips=db_pos.entry_to_sl_pips,
            entry_to_tp_pips=db_pos.entry_to_tp_pips,
            mae_pips=db_pos.mae_pips,
            mfe_pips=db_pos.mfe_pips,
            max_profit_pips=db_pos.max_profit_pips,
            max_drawdown_pips=db_pos.max_drawdown_pips,
            holding_time_seconds=db_pos.holding_time_seconds,
            quality_score=db_pos.quality_score,
            signal_confidence=db_pos.signal_confidence,
            execution_duration_ms=db_pos.execution_duration_ms,
            slippage_pips=db_pos.slippage_pips,
            closing_slippage_pips=db_pos.closing_slippage_pips,
            metadata=metadata,
        )

    def _load_position_ticket(self, position, db_pos, metadata) -> None:
        """Load ticket from metadata or DB column."""
        if "ticket" in metadata:
            position.ticket = int(metadata["ticket"])
            logger.debug(
                f"Loaded ticket {position.ticket} for position {position.position_id}"
            )
        elif db_pos.ticket:
            position.ticket = db_pos.ticket
            logger.debug(
                f"Loaded ticket {position.ticket} from ticket field for position {position.position_id}"
            )

    async def _handle_orphaned_position(self, position, db_pos, session) -> bool:
        """Close orphaned OPEN positions (no ticket).

        Returns:
            True if position was orphaned and closed, False otherwise.
        """
        if position.ticket or position.status != PositionStatus.OPEN:
            return False

        logger.error(
            f"❌ SKIPPING ORPHANED POSITION: {position.position_id} ({position.symbol}) "
            f"has NO TICKET but status is OPEN. This position is invalid and will be closed."
        )

        position.status = PositionStatus.CLOSED
        position.close_time = datetime.now()
        position.close_price = position.entry_price

        db_pos.status = PositionStatus.CLOSED.value
        db_pos.close_time = position.close_time
        db_pos.close_price = position.close_price
        await session.commit()

        logger.info(
            f"🚫 Closed orphaned position {position.position_id} in database (no ticket)"
        )
        return True

    def _register_position_in_memory(self, position: Position) -> None:
        """Add position to in-memory storage dicts."""
        self.positions[position.position_id] = position
        if position.symbol not in self.positions_by_symbol:
            self.positions_by_symbol[position.symbol] = []
        self.positions_by_symbol[position.symbol].append(position.position_id)

    def _restore_automation_tracking(self) -> None:
        """Restore breakeven/trailing tracking for loaded OPEN positions."""
        for position in self.get_open_positions():
            if position.breakeven_activated:
                self.breakeven_manager.breakeven_positions.add(position.position_id)
                logger.debug(f"Restored breakeven tracking for {position.position_id}")

            if position.trailing_activated:
                self.trailing_stop_manager.trailing_active.add(position.position_id)
                self.trailing_stop_manager.highest_profit[position.position_id] = (
                    position.current_profit_pips
                )
                logger.debug(f"Restored trailing tracking for {position.position_id}")

    def _log_load_summary(self, count: int, invalid_count: int) -> None:
        """Log summary of position loading."""
        if count > 0:
            logger.info(f"Loaded {count} active positions from database")
        if invalid_count > 0:
            logger.warning(
                f"Skipped {invalid_count} invalid positions from database. "
                f"These positions may need manual review or cleanup."
            )

    async def save_position(self, position: Position, is_dry_run: bool = False):
        """
        Save or update position in database.

        Args:
            position: Position to save
            is_dry_run: If True, skip saving to database (dry-run mode)
        """
        # CRITICAL: Skip saving to database in dry-run mode
        if is_dry_run:
            logger.debug(
                f"🧪 Dry-run mode: Skipping database save for position {position.position_id}"
            )
            return

        try:
            # Extract confluence_score and ticket from position
            confluence_score = 0.0
            ticket = None

            # Get confluence_score from position object or metadata
            if hasattr(position, "confluence_score") and position.confluence_score:
                confluence_score = position.confluence_score
            elif position.metadata and "confluence_score" in position.metadata:
                confluence_score = position.metadata.get("confluence_score", 0.0)

            # Get ticket from position object or metadata
            if hasattr(position, "ticket") and position.ticket:
                ticket = position.ticket
                # Sync to metadata for backward compatibility
                if not position.metadata:
                    position.metadata = {}
                position.metadata["ticket"] = ticket
            elif position.metadata and "ticket" in position.metadata:
                ticket = position.metadata.get("ticket")

            async with get_session() as session:
                # Check if position exists
                stmt = select(DBPosition).where(DBPosition.position_id == position.position_id)
                result = await session.execute(stmt)
                db_pos = result.scalars().first()

                if db_pos:
                    # Validate SL/TP before updating (only for PENDING positions)
                    # OPEN positions may have SL above/below entry (breakeven/trailing)
                    if position.status == PositionStatus.PENDING:
                        if position.position_type == PositionType.BUY:
                            if position.stop_loss >= position.entry_price:
                                logger.error(
                                    f"Cannot save position {position.position_id}: "
                                    f"BUY SL {position.stop_loss:.5f} >= Entry {position.entry_price:.5f}"
                                )
                                raise ValueError("Invalid stop_loss for BUY position")
                            if position.take_profit <= position.entry_price:
                                logger.error(
                                    f"Cannot save position {position.position_id}: "
                                    f"BUY TP {position.take_profit:.5f} <= Entry {position.entry_price:.5f}"
                                )
                                raise ValueError("Invalid take_profit for BUY position")
                        elif position.position_type == PositionType.SELL:
                            if position.stop_loss <= position.entry_price:
                                logger.error(
                                    f"Cannot save position {position.position_id}: "
                                    f"SELL SL {position.stop_loss:.5f} <= Entry {position.entry_price:.5f}"
                                )
                                raise ValueError("Invalid stop_loss for SELL position")
                            if position.take_profit >= position.entry_price:
                                logger.error(
                                    f"Cannot save position {position.position_id}: "
                                    f"SELL TP {position.take_profit:.5f} >= Entry {position.entry_price:.5f}"
                                )
                                raise ValueError("Invalid take_profit for SELL position")
                    # For OPEN positions, allow SL above/below entry (breakeven/trailing)
                    # Only validate that SL/TP are positive
                    if position.stop_loss <= 0:
                        raise ValueError("Stop loss must be positive")
                    if position.take_profit <= 0:
                        raise ValueError("Take profit must be positive")

                    # Update existing
                    db_pos.status = position.status.value
                    db_pos.stop_loss = position.stop_loss  # Update SL (for breakeven/trailing)
                    db_pos.take_profit = position.take_profit  # Update TP (if changed)
                    db_pos.current_price = position.current_price
                    db_pos.close_price = position.close_price
                    db_pos.current_profit_pips = position.current_profit_pips
                    db_pos.current_pnl_usd = position.current_pnl_usd
                    db_pos.open_time = position.open_time
                    db_pos.close_time = position.close_time
                    db_pos.confluence_score = confluence_score  # Update confluence score
                    db_pos.ticket = ticket  # Update MT5 ticket
                    db_pos.account_id = position.account_id  # Update account_id
                    db_pos.asset_class = position.asset_class  # Update asset_class
                    db_pos.session_id = position.session_id  # Update session_id
                    db_pos.is_winner = position.is_winner  # Update is_winner
                    db_pos.breakeven_activated = (
                        position.breakeven_activated
                    )  # Update breakeven_activated
                    db_pos.trailing_activated = (
                        position.trailing_activated
                    )  # Update trailing_activated
                    # Update new fields
                    db_pos.signal_id = position.signal_id
                    db_pos.strategy_id = position.strategy_id
                    db_pos.close_reason = position.close_reason
                    db_pos.exit_type = position.exit_type
                    db_pos.entry_to_sl_pips = position.entry_to_sl_pips
                    db_pos.entry_to_tp_pips = position.entry_to_tp_pips
                    db_pos.mae_pips = position.mae_pips
                    db_pos.mfe_pips = position.mfe_pips
                    db_pos.max_profit_pips = position.max_profit_pips
                    db_pos.max_drawdown_pips = position.max_drawdown_pips
                    db_pos.holding_time_seconds = position.holding_time_seconds
                    db_pos.quality_score = position.quality_score
                    db_pos.signal_confidence = position.signal_confidence
                    db_pos.execution_duration_ms = position.execution_duration_ms
                    db_pos.slippage_pips = position.slippage_pips
                    db_pos.closing_slippage_pips = position.closing_slippage_pips
                    db_pos.meta_data = position.metadata  # Keep metadata for backward compatibility
                else:
                    # Create new
                    db_pos = DBPosition(
                        position_id=position.position_id,
                        symbol=position.symbol,
                        position_type=position.position_type.value,
                        entry_price=position.entry_price,
                        stop_loss=position.stop_loss,
                        take_profit=position.take_profit,
                        volume=position.volume,
                        pip_size=position.pip_size,
                        pip_value_per_lot=position.pip_value_per_lot,
                        status=position.status.value,
                        current_price=position.current_price,
                        current_profit_pips=position.current_profit_pips,
                        current_pnl_usd=position.current_pnl_usd,
                        risk_amount_usd=position.risk_amount_usd,
                        potential_profit_usd=position.potential_profit_usd,
                        confluence_score=confluence_score,  # Add confluence score
                        ticket=ticket,  # Add MT5 ticket
                        account_id=position.account_id,  # Add account_id
                        asset_class=position.asset_class,  # Add asset_class
                        signal_id=position.signal_id,  # Add signal_id
                        strategy_id=position.strategy_id,  # Add strategy_id
                        session_id=position.session_id,  # Add session_id
                        is_winner=position.is_winner,  # Add is_winner
                        breakeven_activated=position.breakeven_activated,  # Add breakeven_activated
                        trailing_activated=position.trailing_activated,  # Add trailing_activated
                        close_reason=position.close_reason,  # Add close_reason
                        exit_type=position.exit_type,  # Add exit_type
                        entry_to_sl_pips=position.entry_to_sl_pips,  # Add entry_to_sl_pips
                        entry_to_tp_pips=position.entry_to_tp_pips,  # Add entry_to_tp_pips
                        mae_pips=position.mae_pips,  # Add mae_pips
                        mfe_pips=position.mfe_pips,  # Add mfe_pips
                        max_profit_pips=position.max_profit_pips,  # Add max_profit_pips
                        max_drawdown_pips=position.max_drawdown_pips,  # Add max_drawdown_pips
                        holding_time_seconds=position.holding_time_seconds,  # Add holding_time_seconds
                        quality_score=position.quality_score,  # Add quality_score
                        signal_confidence=position.signal_confidence,  # Add signal_confidence
                        execution_duration_ms=position.execution_duration_ms,  # Add execution_duration_ms
                        slippage_pips=position.slippage_pips,  # Add slippage_pips
                        closing_slippage_pips=position.closing_slippage_pips,  # Add closing_slippage_pips
                        open_time=position.open_time,
                        meta_data=position.metadata,
                    )
                    session.add(db_pos)

                await session.commit()
                # logger.debug(f"Position {position.position_id} saved to database")

        except Exception as e:
            logger.error(f"Error saving position {position.position_id} to database: {e}")

    def create_position_from_signal(self, signal: TradingSignal, volume: float) -> Position:
        """
        Create a position from a trading signal.

        Args:
            signal: Trading signal
            volume: Position volume (lot size)

        Returns:
            Created Position object

        Raises:
            ValueError: If position limit reached for symbol
        """
        # Check position limit for symbol
        existing_positions = self.get_positions_by_symbol(signal.symbol)
        open_positions = [p for p in existing_positions if p.is_open]

        if len(open_positions) >= self.max_positions_per_symbol:
            raise ValueError(
                f"Position limit reached for {signal.symbol}: "
                f"{len(open_positions)}/{self.max_positions_per_symbol}"
            )

        # Get pip size for symbol
        pip_size = self.pip_calculator.get_pip_size(signal.symbol)

        # Calculate pip value
        pip_value_per_lot = self.pip_calculator.calculate_pip_value(signal.symbol, volume)

        # Get asset class for symbol
        asset_class = self.pip_calculator.symbol_mapper.get_asset_class(signal.symbol)

        # Extract price action info from signal metadata (if available)
        price_action_info = signal.metadata.get("price_action") if signal.metadata else None

        # Create position metadata
        position_metadata = {
            "signal_id": signal.signal_id,
            "confluence_score": signal.confluence_score,
            "strategy_scores": signal.strategy_scores,
        }

        # Add price action pattern info to position metadata for tracking
        if price_action_info:
            position_metadata["price_action"] = {
                "pattern_type": price_action_info.get("desc", "UNKNOWN"),
                "status": price_action_info.get("status", "detected"),
                "pattern_details": price_action_info,
            }
            logger.debug(
                f"Position {signal.symbol}: Price action pattern saved: {price_action_info.get('desc', 'UNKNOWN')}"
            )

        # Create position
        position = Position(
            position_id=self._generate_position_id(),
            symbol=signal.symbol,
            position_type=PositionType(signal.direction.value),
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            volume=volume,
            pip_size=pip_size,
            pip_value_per_lot=pip_value_per_lot,
            confluence_score=signal.confluence_score,
            asset_class=asset_class,
            signal_id=signal.signal_id,
            strategy_id="foundation",  # TODO: Get from signal
            status=PositionStatus.PENDING,
            metadata=position_metadata,
        )

        # Store position
        self.positions[position.position_id] = position

        # Update symbol index
        if signal.symbol not in self.positions_by_symbol:
            self.positions_by_symbol[signal.symbol] = []
        self.positions_by_symbol[signal.symbol].append(position.position_id)

        logger.info(
            f"Created position {position.position_id}: {position.position_type.value} "
            f"{position.symbol} @ {position.entry_price:.5f}, Volume: {volume:.2f}"
        )

        return position

    def open_position(self, position_id: str) -> None:
        """
        Open a position.

        Args:
            position_id: Position ID to open

        Raises:
            ValueError: If position not found
        """
        position = self.get_position(position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found")

        self.tracker.open_position(position)

    def update_position(self, position_id: str, current_price: float) -> None:
        """
        Update position with current market price.

        Args:
            position_id: Position ID to update
            current_price: Current market price

        Raises:
            ValueError: If position not found
        """
        position = self.get_position(position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found")

        self.tracker.update_position_price(position, current_price)

    def close_position(
        self, position_id: str, close_price: float, reason: str = "Manual"
    ) -> dict | None:
        """
        Close a position.

        Args:
            position_id: Position ID to close
            close_price: Price at which to close
            reason: Reason for closing

        Returns:
            Dictionary with close results or None if not found
        """
        position = self.get_position(position_id)
        if not position:
            return None

        result = self.tracker.close_position(position, close_price)
        position.metadata["close_reason"] = reason

        return result

    def get_position(self, position_id: str) -> Position | None:
        """
        Get a position by ID.

        Args:
            position_id: Position ID

        Returns:
            Position or None if not found
        """
        return self.positions.get(position_id)

    def get_all_positions(self) -> list[Position]:
        """
        Get all positions.

        Returns:
            List of all positions
        """
        return list(self.positions.values())

    def get_open_positions(self) -> list[Position]:
        """
        Get all open positions.

        Returns:
            List of open positions
        """
        return [p for p in self.positions.values() if p.is_open]

    def get_closed_positions(self) -> list[Position]:
        """
        Get all closed positions.

        Returns:
            List of closed positions
        """
        return [p for p in self.positions.values() if p.is_closed]

    def get_positions_by_symbol(self, symbol: str) -> list[Position]:
        """
        Get all positions for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of positions for the symbol
        """
        position_ids = self.positions_by_symbol.get(symbol, [])
        return [self.positions[pid] for pid in position_ids if pid in self.positions]

    def get_position_count(self) -> int:
        """Get total number of positions."""
        return len(self.positions)

    def get_open_position_count(self) -> int:
        """Get number of open positions."""
        return len(self.get_open_positions())

    def update_all_positions(self, prices: dict[str, float]) -> None:
        """
        Update all open positions with current prices.

        Args:
            prices: Dictionary of symbol -> current_price
        """
        for position in self.get_open_positions():
            if position.symbol in prices:
                self.tracker.update_position_price(position, prices[position.symbol])

    def check_and_close_positions(self, prices: dict[str, float]) -> list[Position]:
        """
        Check and auto-close positions that hit SL, TP, or max duration.

        Args:
            prices: Dictionary of symbol -> current_price

        Returns:
            List of positions that were closed
        """
        closed_positions = []

        for position in self.get_open_positions():
            if position.symbol not in prices:
                continue

            current_price = prices[position.symbol]

            # Update position price first
            self.tracker.update_position_price(position, current_price)

            # Manage automation (Breakeven & Trailing Stop)
            self._manage_automation(position)

            # Check max position duration (for intraday trading)
            if self._check_max_duration(position, current_price):
                logger.info(
                    f"Max duration exceeded for {position.position_id}: {position.symbol} - auto-closing"
                )
                closed_positions.append(position)
                continue

            # Check stop loss
            if self.tracker.check_stop_loss(position):
                logger.info(f"Stop loss hit for {position.position_id}: {position.symbol}")
                self.tracker.close_position(position, current_price)
                position.metadata["close_reason"] = "Stop Loss"
                closed_positions.append(position)
                continue

            # Check take profit
            if self.tracker.check_take_profit(position):
                logger.info(f"Take profit hit for {position.position_id}: {position.symbol}")
                self.tracker.close_position(position, current_price)
                position.metadata["close_reason"] = "Take Profit"
                closed_positions.append(position)

        return closed_positions

    def _check_max_duration(self, position: Position, current_price: float) -> bool:
        """
        Check if position exceeds maximum duration and close if needed.

        IMPORTANT: Only closes position if it's in profit to avoid forced losses.
        If position is in loss, let SL/TP handle the closure.

        Args:
            position: Position to check
            current_price: Current market price

        Returns:
            True if position was closed due to max duration
        """
        if not position.open_time:
            return False

        # Get max duration from trading type config
        trading_types = self.config.get("trading_types", {})
        # Get active trading type from config (can be in root or trading_types section)
        active_type = (
            self.config.get("active_trading_type")
            or self.config.get("trading_types", {}).get("active_trading_type")
            or "day_trading"
        )
        type_config = trading_types.get(active_type, {})

        max_duration_hours = type_config.get("max_position_duration_hours")
        if max_duration_hours is None:
            # No max duration configured, skip check
            return False

        # Calculate position duration
        duration_seconds = position.duration_seconds
        if duration_seconds is None:
            return False

        duration_hours = duration_seconds / 3600.0

        # Check if exceeded max duration
        if duration_hours >= max_duration_hours:
            # CRITICAL: Only close if position is in profit
            # If position is in loss, let SL/TP handle the closure

            # Get current profit/loss values (should be updated by update_position_price)
            profit_pips = position.current_profit_pips or 0.0
            pnl_usd = position.current_pnl_usd or 0.0

            # Check if position is in profit (either pips or USD)
            is_profit = profit_pips > 0 or pnl_usd > 0

            if not is_profit:
                # Position is in loss - don't force close, let SL/TP handle it
                logger.debug(
                    f"Position {position.position_id} ({position.symbol}) exceeded max duration "
                    f"({duration_hours:.2f}h >= {max_duration_hours}h) but is in loss "
                    f"({profit_pips:.1f} pips, ${pnl_usd:.2f}) - skipping auto-close, "
                    f"waiting for SL/TP"
                )
                return False

            # Position is in profit - safe to close
            logger.info(
                f"Position {position.position_id} ({position.symbol}) exceeded max duration: "
                f"{duration_hours:.2f}h >= {max_duration_hours}h and is in profit "
                f"({profit_pips:.1f} pips, ${pnl_usd:.2f}) - closing position"
            )
            self.tracker.close_position(position, current_price)
            position.metadata["close_reason"] = f"Max Duration ({max_duration_hours}h) - Profit"
            return True

        return False

    def _manage_automation(self, position: Position) -> None:
        """
        Manage automated position adjustments (Breakeven & Trailing Stop).

        Args:
            position: Position to manage
        """
        if not position.is_open:
            return

        # Breakeven Management
        if self.breakeven_manager.should_move_to_breakeven(position):
            try:
                new_sl = self.breakeven_manager.move_to_breakeven(position)
                logger.info(
                    f"📍 BREAKEVEN activated for {position.position_id}: "
                    f"SL moved to {new_sl:.5f}"
                )
            except Exception as e:
                logger.error(f"Failed to move {position.position_id} to breakeven: {e}")

        # Trailing Stop Management
        # First check if we should activate trailing
        if self.trailing_stop_manager.should_activate_trailing(position):
            self.trailing_stop_manager.activate_trailing(position)

        # Then check if we should update trailing stop
        if self.trailing_stop_manager.should_update_trailing_stop(position):
            try:
                new_sl = self.trailing_stop_manager.update_trailing_stop(position)
                # Logging is already done in TrailingStopManager
            except Exception as e:
                logger.error(f"Failed to update trailing stop for {position.position_id}: {e}")

    def get_portfolio_summary(self) -> dict:
        """
        Get portfolio summary.

        Returns:
            Dictionary with portfolio statistics
        """
        open_positions = self.get_open_positions()
        closed_positions = self.get_closed_positions()

        total_pnl = sum(p.current_pnl_usd for p in self.positions.values())
        open_pnl = sum(p.current_pnl_usd for p in open_positions)
        closed_pnl = sum(p.current_pnl_usd for p in closed_positions)

        total_risk = sum(p.risk_amount_usd for p in open_positions)

        return {
            "total_positions": len(self.positions),
            "open_positions": len(open_positions),
            "closed_positions": len(closed_positions),
            "total_pnl_usd": total_pnl,
            "open_pnl_usd": open_pnl,
            "closed_pnl_usd": closed_pnl,
            "total_risk_usd": total_risk,
            "symbols_traded": len(self.positions_by_symbol),
        }

    def _generate_position_id(self) -> str:
        """Generate unique position ID."""
        return f"pos_{uuid.uuid4().hex[:12]}"

    def __str__(self) -> str:
        """String representation."""
        return (
            f"PositionManager("
            f"{self.get_open_position_count()} open, "
            f"{len(self.get_closed_positions())} closed)"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
