"""
Position data models.

Data models for position management and tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PositionStatus(str, Enum):
    """Position status."""

    PENDING = "PENDING"  # Signal received, not yet opened
    OPEN = "OPEN"  # Position is open
    CLOSED = "CLOSED"  # Position is closed
    CANCELLED = "CANCELLED"  # Signal cancelled before opening


class PositionType(str, Enum):
    """Position type (direction)."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Position:
    """
    Trading position with pip tracking.

    Attributes:
        position_id: Unique position identifier
        symbol: Trading symbol
        position_type: BUY or SELL
        entry_price: Position entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        volume: Position volume (lot size)
        pip_size: Asset-specific pip size
        pip_value_per_lot: USD value per pip per lot
        confluence_score: Signal confluence score (0-100)
        ticket: MT5 ticket number (if available)
        account_id: Link to TradingAccount (multi-account support)
        asset_class: Asset class (forex_major, forex_jpy, commodities, crypto)
        signal_id: Link to TradingSignal
        strategy_id: Strategy identifier
        session_id: Link to TradingSession
        status: Current position status
        open_time: When position was opened
        close_time: When position was closed (if closed)
        close_price: Price at which position was closed
        close_reason: Reason for closing (SL, TP, Manual, etc.)
        exit_type: Outcome class on close (WIN / LOSS / BREAKEVEN)
        current_price: Current market price
        current_profit_pips: Current profit in pips
        current_pnl_usd: Current P&L in USD
        risk_amount_usd: USD amount at risk (SL distance)
        potential_profit_usd: Potential USD profit (TP distance)
        is_winner: Whether position was profitable (set on close)
        breakeven_activated: Whether breakeven was triggered
        trailing_activated: Whether trailing stop was triggered
        entry_to_sl_pips: Distance from entry to SL in pips
        entry_to_tp_pips: Distance from entry to TP in pips
        mae_pips: Maximum adverse excursion (max drawdown in pips)
        mfe_pips: Maximum favorable excursion (max profit in pips)
        max_profit_pips: Maximum profit achieved in pips
        max_drawdown_pips: Maximum drawdown in pips
        holding_time_seconds: Duration position was held
        slippage_pips: Slippage at entry in pips
        closing_slippage_pips: Slippage at exit in pips
        metadata: Additional position metadata
    """

    position_id: str
    symbol: str
    position_type: PositionType
    entry_price: float
    stop_loss: float
    take_profit: float
    volume: float  # Lot size
    pip_size: float  # Asset-specific pip size
    pip_value_per_lot: float  # USD value per pip per lot
    confluence_score: float = 0.0  # Signal confluence score (0-100)
    ticket: int | None = None  # MT5 ticket number
    account_id: int | None = None  # Link to TradingAccount (multi-account support)
    asset_class: str | None = None  # Asset class (forex_major, forex_jpy, commodities, crypto)
    signal_id: str | None = None  # Link to TradingSignal
    strategy_id: str | None = None  # Strategy identifier
    session_id: str | None = None  # Link to TradingSession
    status: PositionStatus = PositionStatus.PENDING
    open_time: datetime | None = None
    close_time: datetime | None = None
    close_price: float | None = None
    close_reason: str | None = None  # Reason for closing
    exit_type: str | None = None  # Outcome class on close: WIN / LOSS / BREAKEVEN
    current_price: float | None = None
    current_profit_pips: float = 0.0
    current_pnl_usd: float = 0.0
    realized_profit_pips: float = 0.0  # Final profit pips, frozen at close
    realized_pnl_usd: float = 0.0  # Final P&L, frozen at close
    risk_amount_usd: float = 0.0
    potential_profit_usd: float = 0.0
    is_winner: bool | None = None  # Set when position is closed
    breakeven_activated: bool = False  # Whether breakeven was triggered
    trailing_activated: bool = False  # Whether trailing stop was triggered
    entry_to_sl_pips: float = 0.0  # Distance from entry to SL
    entry_to_tp_pips: float = 0.0  # Distance from entry to TP
    mae_pips: float = 0.0  # Maximum adverse excursion
    mfe_pips: float = 0.0  # Maximum favorable excursion
    max_profit_pips: float = 0.0  # Maximum profit achieved
    max_drawdown_pips: float = 0.0  # Maximum drawdown
    holding_time_seconds: int = 0  # Duration held
    slippage_pips: float = 0.0  # Entry slippage
    closing_slippage_pips: float = 0.0  # Exit slippage
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate position after initialization."""
        if self.entry_price <= 0:
            raise ValueError("Entry price must be positive")
        if self.stop_loss <= 0:
            raise ValueError("Stop loss must be positive")
        if self.take_profit <= 0:
            raise ValueError("Take profit must be positive")
        if self.volume <= 0:
            raise ValueError("Volume must be positive")
        if self.pip_size <= 0:
            raise ValueError("Pip size must be positive")

        # Validate position logic (only for PENDING positions)
        # OPEN positions may have SL above/below entry (breakeven/trailing)
        if self.status == PositionStatus.PENDING:
            if self.position_type == PositionType.BUY:
                if self.stop_loss >= self.entry_price:
                    raise ValueError("BUY: stop_loss must be below entry_price")
                if self.take_profit <= self.entry_price:
                    raise ValueError("BUY: take_profit must be above entry_price")
            elif self.position_type == PositionType.SELL:
                if self.stop_loss <= self.entry_price:
                    raise ValueError("SELL: stop_loss must be above entry_price")
                if self.take_profit >= self.entry_price:
                    raise ValueError("SELL: take_profit must be below entry_price")

        # Convert string to enum if needed
        if not isinstance(self.position_type, PositionType):
            self.position_type = PositionType(self.position_type)
        if not isinstance(self.status, PositionStatus):
            self.status = PositionStatus(self.status)

    @property
    def is_open(self) -> bool:
        """Check if position is open."""
        return self.status == PositionStatus.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if position is closed."""
        return self.status == PositionStatus.CLOSED

    @property
    def duration_seconds(self) -> float | None:
        """Calculate position duration in seconds."""
        if not self.open_time:
            return None
        end_time = self.close_time if self.close_time else datetime.now()
        return (end_time - self.open_time).total_seconds()

    @property
    def risk_reward_ratio(self) -> float:
        """Calculate risk/reward ratio."""
        if self.position_type == PositionType.BUY:
            risk = self.entry_price - self.stop_loss
            reward = self.take_profit - self.entry_price
        else:  # SELL
            risk = self.stop_loss - self.entry_price
            reward = self.entry_price - self.take_profit

        if risk <= 0:
            return 0.0
        return reward / risk

    def to_dict(self) -> dict:
        """Convert position to dictionary."""
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "position_type": self.position_type.value,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "volume": self.volume,
            "pip_size": self.pip_size,
            "pip_value_per_lot": self.pip_value_per_lot,
            "confluence_score": self.confluence_score,
            "ticket": self.ticket,
            "account_id": self.account_id,
            "asset_class": self.asset_class,
            "session_id": self.session_id,
            "status": self.status.value,
            "open_time": self.open_time.isoformat() if self.open_time else None,
            "close_time": self.close_time.isoformat() if self.close_time else None,
            "close_price": self.close_price,
            "current_price": self.current_price,
            "current_profit_pips": self.current_profit_pips,
            "current_pnl_usd": self.current_pnl_usd,
            "realized_profit_pips": self.realized_profit_pips,
            "realized_pnl_usd": self.realized_pnl_usd,
            "risk_amount_usd": self.risk_amount_usd,
            "potential_profit_usd": self.potential_profit_usd,
            "is_winner": self.is_winner,
            "breakeven_activated": self.breakeven_activated,
            "trailing_activated": self.trailing_activated,
            "risk_reward_ratio": self.risk_reward_ratio,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Position({self.position_type.value} {self.symbol} @ {self.entry_price:.5f}, "
            f"SL: {self.stop_loss:.5f}, TP: {self.take_profit:.5f}, "
            f"Volume: {self.volume:.2f}, Status: {self.status.value})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
