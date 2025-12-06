"""
Position Manager - Main position management orchestrator.

Coordinates position lifecycle, tracking, and management.
"""

import uuid

from sqlalchemy import select

from trading_bot.data.database import get_session
from trading_bot.data.models import Position as DBPosition
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

        # Position storage
        self.positions: dict[str, Position] = {}  # position_id -> Position
        self.positions_by_symbol: dict[str, list[str]] = {}  # symbol -> list of position_ids

        # Configuration
        self.max_positions_per_symbol = self.config.get("position_manager", {}).get(
            "max_positions_per_symbol", 1
        )

        logger.info(
            f"PositionManager initialized "
            f"(max positions per symbol: {self.max_positions_per_symbol})"
        )

    async def load_positions_from_db(self):
        """Load active positions from database."""
        try:
            async with get_session() as session:
                # Query active positions (PENDING or OPEN)
                stmt = select(DBPosition).where(
                    DBPosition.status.in_([PositionStatus.PENDING.value, PositionStatus.OPEN.value])
                )
                result = await session.execute(stmt)
                db_positions = result.scalars().all()

                count = 0
                for db_pos in db_positions:
                    # Convert DB model to Position object
                    position = Position(
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
                        open_time=db_pos.open_time,
                        close_time=db_pos.close_time,
                        close_price=db_pos.close_price,
                        current_price=db_pos.current_price,
                        current_profit_pips=db_pos.current_profit_pips,
                        current_pnl_usd=db_pos.current_pnl_usd,
                        risk_amount_usd=db_pos.risk_amount_usd,
                        potential_profit_usd=db_pos.potential_profit_usd,
                        metadata=db_pos.meta_data or {},
                    )

                    # Store in memory
                    self.positions[position.position_id] = position

                    if position.symbol not in self.positions_by_symbol:
                        self.positions_by_symbol[position.symbol] = []
                    self.positions_by_symbol[position.symbol].append(position.position_id)

                    count += 1

                if count > 0:
                    logger.info(f"Loaded {count} active positions from database")

        except Exception as e:
            logger.error(f"Error loading positions from database: {e}")

    async def save_position(self, position: Position):
        """Save or update position in database."""
        try:
            async with get_session() as session:
                # Check if position exists
                stmt = select(DBPosition).where(DBPosition.position_id == position.position_id)
                result = await session.execute(stmt)
                db_pos = result.scalars().first()

                if db_pos:
                    # Update existing
                    db_pos.status = position.status.value
                    db_pos.current_price = position.current_price
                    db_pos.close_price = position.close_price
                    db_pos.current_profit_pips = position.current_profit_pips
                    db_pos.current_pnl_usd = position.current_pnl_usd
                    db_pos.open_time = position.open_time
                    db_pos.close_time = position.close_time
                    db_pos.meta_data = position.metadata
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
            status=PositionStatus.PENDING,
            metadata={
                "signal_id": signal.signal_id,
                "confluence_score": signal.confluence_score,
                "strategy_scores": signal.strategy_scores,
            },
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
        Check and auto-close positions that hit SL or TP.

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
