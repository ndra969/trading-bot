"""
Database Models for Trading Bot

SQLAlchemy 2.0 models with async support.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, validates

from .database import Base


class SupplyDemandZone(Base):
    """
    Supply & Demand zone model for market structure analysis.

    Tracks key support and resistance levels with validation scores.
    """

    __tablename__ = "supply_demand_zones"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Zone identification
    zone_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    zone_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'rejection', 'consolidation', 'breakout_origin'

    # Zone boundaries
    high_price: Mapped[float] = mapped_column(Float(precision=10), nullable=False)
    low_price: Mapped[float] = mapped_column(Float(precision=10), nullable=False)
    entry_price: Mapped[float | None] = mapped_column(Float(precision=10), nullable=True)

    # Zone characteristics
    strength: Mapped[float] = mapped_column(
        Float(precision=2), default=50.0
    )  # Zone strength (0-100)
    confluence_score: Mapped[float] = mapped_column(
        Float(precision=2), default=0.0
    )  # Confluence score
    touched_count: Mapped[int] = mapped_column(
        Integer, default=0
    )  # How many times zone was touched
    volume_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Session relationship and quality metrics
    session_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("trading_sessions.session_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )  # Link to TradingSession (group zones by session)
    freshness_score: Mapped[float] = mapped_column(
        Float(precision=2), default=0.0
    )  # Zone quality metric (0-100) - based on age, touches, relevance

    # Temporal data
    timeframe: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # M1, M5, M15, H1, H4, D1, etc.
    first_detected: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    last_touched: Mapped[datetime | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Market structure context
    trend_direction: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # 'up', 'down', 'sideways'
    market_session: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # 'london', 'ny', 'tokyo', 'sydney'

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("high_price > low_price", name="check_price_range"),
        CheckConstraint("strength >= 0 AND strength <= 100", name="check_strength_range"),
        CheckConstraint(
            "confluence_score >= 0 AND confluence_score <= 100", name="check_confluence_range"
        ),
        CheckConstraint(
            "freshness_score >= 0 AND freshness_score <= 100", name="check_freshness_range"
        ),
        Index("idx_symbol_type", "symbol", "zone_type"),
        Index("idx_strength", "strength"),
        Index("idx_zone_session", "session_id"),
        Index("idx_zone_freshness", "freshness_score"),
    )

    @property
    def zone_range(self) -> float:
        """Calculate zone range in price."""
        return self.high_price - self.low_price

    @property
    def zone_midpoint(self) -> float:
        """Calculate zone midpoint."""
        return (self.high_price + self.low_price) / 2

    def is_price_in_zone(self, price: float) -> bool:
        """Check if price is within zone boundaries."""
        return self.low_price <= price <= self.high_price

    def touch_zone(self):
        """Record zone touch."""
        self.touched_count += 1
        self.last_touched = datetime.now(UTC).replace(tzinfo=None)
        self.updated_at = datetime.now(UTC).replace(tzinfo=None)

    def deactivate_zone(self):
        """Deactivate zone (no longer valid)."""
        self.is_active = False
        self.updated_at = datetime.now(UTC).replace(tzinfo=None)

    def __repr__(self) -> str:
        return (
            f"<SupplyDemandZone(id={self.id}, symbol={self.symbol}, "
            f"zone_type={self.zone_type}, strength={self.strength:.1f})>"
        )


class Position(Base):
    """
    Trading Position Model.

    Stores active and closed positions with performance metrics.
    """

    __tablename__ = "positions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    position_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Relationships (7 fields)
    account_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("trading_accounts.account_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )  # Link to TradingAccount
    session_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("trading_sessions.session_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )  # Link to TradingSession
    signal_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )  # Link to TradingSignal (future - nullable for now)
    strategy_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # Strategy identifier (e.g., "foundation", "momentum")
    magic_number: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # MT5 magic number for order filtering
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)  # MT5 comment field

    # Core fields
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    position_type: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY/SELL
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")

    # Price levels
    entry_price: Mapped[float] = mapped_column(Float(precision=10), nullable=False)
    stop_loss: Mapped[float] = mapped_column(Float(precision=10), nullable=False)
    take_profit: Mapped[float] = mapped_column(Float(precision=10), nullable=False)
    current_price: Mapped[float | None] = mapped_column(Float(precision=10), nullable=True)
    close_price: Mapped[float | None] = mapped_column(Float(precision=10), nullable=True)

    # Position sizing
    volume: Mapped[float] = mapped_column(Float(precision=2), nullable=False)
    pip_size: Mapped[float] = mapped_column(Float(precision=10), nullable=False)
    pip_value_per_lot: Mapped[float] = mapped_column(Float(precision=10), nullable=False)

    # Performance metrics
    current_profit_pips: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    current_pnl_usd: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    risk_amount_usd: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    potential_profit_usd: Mapped[float] = mapped_column(Float(precision=2), default=0.0)

    # Signal quality metrics
    confluence_score: Mapped[float] = mapped_column(
        Float(precision=2), default=0.0, index=True
    )  # Confluence score (0-100) for analytics

    # MT5 integration
    ticket: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True, unique=True
    )  # MT5 ticket number (already exists)

    # Closing details (4 fields)
    realized_pnl_usd: Mapped[float] = mapped_column(
        Float(precision=2), default=0.0
    )  # Final P&L when closed
    realized_profit_pips: Mapped[float] = mapped_column(
        Float(precision=2), default=0.0
    )  # Final profit in pips
    close_reason: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # Why closed (SL/TP/Manual/Trailing)
    exit_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # Exit classification (WIN/LOSS/BREAKEVEN)

    # Quality metrics (8 fields)
    mae_pips: Mapped[float] = mapped_column(
        Float(precision=2), default=0.0
    )  # Max Adverse Excursion
    mfe_pips: Mapped[float] = mapped_column(
        Float(precision=2), default=0.0
    )  # Max Favorable Excursion
    is_winner: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # Win/Loss flag
    holding_time_seconds: Mapped[int] = mapped_column(Integer, default=0)  # Position duration
    max_profit_pips: Mapped[float] = mapped_column(
        Float(precision=2), default=0.0
    )  # Max profit reached
    max_drawdown_pips: Mapped[float] = mapped_column(
        Float(precision=2), default=0.0
    )  # Max loss from peak

    # Execution metrics
    slippage_pips: Mapped[float] = mapped_column(Float(precision=2), default=0.0)  # Entry slippage
    closing_slippage_pips: Mapped[float] = mapped_column(
        Float(precision=2), default=0.0
    )  # Exit slippage
    entry_tags: Mapped[dict] = mapped_column(JSON, default=dict)  # Entry context tags (JSON)

    # Context fields (3 fields)
    asset_class: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # Forex/Commodities/Crypto
    entry_to_sl_pips: Mapped[float] = mapped_column(Float(precision=2), default=0.0)  # Risk in pips
    entry_to_tp_pips: Mapped[float] = mapped_column(
        Float(precision=2), default=0.0
    )  # Reward in pips

    # Automation fields (2 fields)
    breakeven_activated: Mapped[bool] = mapped_column(Boolean, default=False)  # Automation tracking
    trailing_activated: Mapped[bool] = mapped_column(Boolean, default=False)  # Automation tracking

    # Timestamps
    open_time: Mapped[datetime | None] = mapped_column(nullable=True)
    close_time: Mapped[datetime | None] = mapped_column(nullable=True)

    # Metadata (using JSON type for additional fields)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "confluence_score >= 0 AND confluence_score <= 100",
            name="check_position_confluence_range",
        ),
        CheckConstraint(
            "exit_type IS NULL OR exit_type IN ('WIN', 'LOSS', 'BREAKEVEN')",
            name="check_exit_type_valid",
        ),
        Index("idx_position_confluence", "confluence_score"),
        Index("idx_position_ticket", "ticket"),
        Index("idx_position_account", "account_id"),
        Index("idx_position_session", "session_id"),
        Index("idx_position_strategy", "strategy_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Position(id={self.position_id}, symbol={self.symbol}, "
            f"type={self.position_type}, status={self.status})>"
        )


class TradingAccount(Base):
    """
    Trading Account Model - Multi-account support.

    Stores MT5 account information for trading bot sessions.
    Supports multiple brokers and account types (DEMO/LIVE).
    """

    __tablename__ = "trading_accounts"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True
    )  # MT5 login ID

    # Account identification
    broker_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "Exness", "XM", "OANDA"
    account_number: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # Account number (string for flexibility)
    account_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "DEMO" or "LIVE"

    # Account balances
    balance: Mapped[float] = mapped_column(
        Float(precision=2), nullable=False
    )  # Current account balance
    equity: Mapped[float | None] = mapped_column(
        Float(precision=2), nullable=True
    )  # Current equity (balance + floating P&L)
    leverage: Mapped[int] = mapped_column(Integer, default=100)  # Leverage (e.g., 100, 500, 1000)

    # Account settings
    currency: Mapped[str] = mapped_column(String(10), default="USD")  # Account currency
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Is account active?

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("leverage >= 1 AND leverage <= 2000", name="check_leverage_range"),
        CheckConstraint("balance >= 0", name="check_balance_positive"),
        CheckConstraint("account_type IN ('DEMO', 'LIVE')", name="check_account_type_valid"),
        Index("idx_account_broker", "broker_name", "account_number"),
        Index("idx_account_active", "is_active"),
    )

    @validates("account_type")
    def validate_account_type(self, key, value):
        """Validate account type is DEMO or LIVE."""
        if value not in ("DEMO", "LIVE"):
            raise ValueError("Account type must be DEMO or LIVE")
        return value

    @validates("leverage")
    def validate_leverage(self, key, value):
        """Validate leverage is between 1 and 2000."""
        if not (1 <= value <= 2000):
            raise ValueError("Leverage must be between 1 and 2000")
        return value

    @validates("balance")
    def validate_balance(self, key, value):
        """Validate balance is positive."""
        if value < 0:
            raise ValueError("Balance must be positive")
        return value

    def update_balance(self, new_balance: float, new_equity: float | None = None):
        """Update account balance and equity."""
        if new_balance < 0:
            raise ValueError("Balance must be positive")

        self.balance = new_balance
        if new_equity is not None:
            self.equity = new_equity
        self.updated_at = datetime.now(UTC).replace(tzinfo=None)

    def deactivate(self):
        """Deactivate account."""
        self.is_active = False
        self.updated_at = datetime.now(UTC).replace(tzinfo=None)

    def __repr__(self) -> str:
        return (
            f"<TradingAccount(id={self.account_id}, broker={self.broker_name}, "
            f"type={self.account_type}, balance={self.balance:.2f})>"
        )


class TradingSession(Base):
    """
    Trading Session Model - Session tracking and aggregations.

    Stores trading session information with performance metrics.
    Links positions to specific trading sessions for analytics.
    """

    __tablename__ = "trading_sessions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )  # Unique session identifier

    # Relationships
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("trading_accounts.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )  # Link to TradingAccount
    config_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )  # Link to ConfigSnapshot (future)

    # Session info
    start_time: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    end_time: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE"
    )  # ACTIVE/CLOSED

    # Trading context
    trading_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="day_trading"
    )  # scalping/day_trading/swing/position
    is_backtest: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dry_run: Mapped[bool] = mapped_column(Boolean, default=False)

    # Session aggregations (updated as positions close)
    total_pnl_usd: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float(precision=2), default=0.0)  # Percentage

    # Performance metrics
    gross_profit: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    gross_loss: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    average_win: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    average_loss: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    max_consecutive_wins: Mapped[int] = mapped_column(Integer, default=0)
    max_consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)

    # Risk metrics
    max_drawdown: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    max_drawdown_percentage: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    starting_balance: Mapped[float] = mapped_column(Float(precision=2), default=0.0)
    ending_balance: Mapped[float] = mapped_column(Float(precision=2), default=0.0)

    # Quality metrics (future enhancement)
    data_quality_score: Mapped[float | None] = mapped_column(
        Float(precision=2), nullable=True
    )  # For backtesting

    # Metadata (additional info as JSON)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("win_rate >= 0 AND win_rate <= 100", name="check_win_rate_range"),
        CheckConstraint("status IN ('ACTIVE', 'CLOSED')", name="check_session_status_valid"),
        CheckConstraint(
            "trading_type IN ('scalping', 'day_trading', 'swing_trading', 'position_trading')",
            name="check_trading_type_valid",
        ),
        CheckConstraint("total_trades >= 0", name="check_total_trades_positive"),
        CheckConstraint("winning_trades >= 0", name="check_winning_trades_positive"),
        CheckConstraint("losing_trades >= 0", name="check_losing_trades_positive"),
        Index("idx_session_account_status", "account_id", "status"),
        Index("idx_session_start_time", "start_time"),
        Index("idx_session_trading_type", "trading_type"),
    )

    @validates("status")
    def validate_status(self, key, value):
        """Validate session status."""
        if value not in ("ACTIVE", "CLOSED"):
            raise ValueError("Session status must be ACTIVE or CLOSED")
        return value

    @validates("trading_type")
    def validate_trading_type(self, key, value):
        """Validate trading type."""
        valid_types = ("scalping", "day_trading", "swing_trading", "position_trading")
        if value not in valid_types:
            raise ValueError(f"Trading type must be one of {valid_types}")
        return value

    def close_session(self, ending_balance: float):
        """Close trading session."""
        self.status = "CLOSED"
        self.end_time = datetime.now(UTC).replace(tzinfo=None)
        self.ending_balance = ending_balance
        self.updated_at = datetime.now(UTC).replace(tzinfo=None)

    def update_aggregations(
        self,
        pnl: float,
        is_winner: bool,
        gross_profit: float = 0.0,
        gross_loss: float = 0.0,
    ):
        """Update session aggregations when a position closes."""
        self.total_trades += 1
        self.total_pnl_usd += pnl

        if is_winner:
            self.winning_trades += 1
            self.gross_profit += gross_profit
        else:
            self.losing_trades += 1
            self.gross_loss += abs(gross_loss)

        # Recalculate win rate
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100

        # Recalculate profit factor
        if self.gross_loss > 0:
            self.profit_factor = self.gross_profit / abs(self.gross_loss)
        else:
            self.profit_factor = self.gross_profit if self.gross_profit > 0 else 0.0

        # Update averages
        if self.winning_trades > 0:
            self.average_win = self.gross_profit / self.winning_trades
        if self.losing_trades > 0:
            self.average_loss = self.gross_loss / self.losing_trades

        self.updated_at = datetime.now(UTC).replace(tzinfo=None)

    def calculate_session_duration(self) -> float | None:
        """Calculate session duration in hours."""
        if self.end_time:
            duration = self.end_time - self.start_time
            return duration.total_seconds() / 3600  # Convert to hours
        return None

    def __repr__(self) -> str:
        return (
            f"<TradingSession(id={self.session_id}, account={self.account_id}, "
            f"status={self.status}, pnl=${self.total_pnl_usd:.2f}, "
            f"trades={self.total_trades}, win_rate={self.win_rate:.1f}%)>"
        )


class ConfigSnapshot(Base):
    """
    Configuration Snapshot Model - Configuration versioning.

    Stores configuration snapshots with SHA256 hash as primary key.
    Enables configuration tracking, comparison, and audit trail.
    """

    __tablename__ = "config_snapshots"

    # Primary key (SHA256 hash of config)
    config_hash: Mapped[str] = mapped_column(
        String(64), primary_key=True, index=True
    )  # SHA256 hash

    # Configuration data (full config as JSON)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # development/production/backtest

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Constraints
    __table_args__ = (
        Index("idx_config_created_at", "created_at"),
        Index("idx_config_environment", "environment"),
    )

    def get_config_value(self, key_path: str, default=None):
        """
        Get configuration value by dot-notation path.

        Args:
            key_path: Dot-separated path (e.g., "risk.max_risk_per_trade")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        value = self.config_json

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def compare_with(self, other_config: dict) -> dict:
        """
        Compare this config with another config.

        Args:
            other_config: Configuration dictionary to compare with

        Returns:
            Dictionary with differences
        """
        differences = {
            "added": [],
            "removed": [],
            "modified": [],
        }

        # Find added and modified keys
        for key in other_config:
            if key not in self.config_json:
                differences["added"].append(key)
            elif self.config_json[key] != other_config[key]:
                differences["modified"].append(
                    {
                        "key": key,
                        "old_value": self.config_json[key],
                        "new_value": other_config[key],
                    }
                )

        # Find removed keys
        for key in self.config_json:
            if key not in other_config:
                differences["removed"].append(key)

        return differences

    def __repr__(self) -> str:
        return (
            f"<ConfigSnapshot(hash={self.config_hash[:12]}..., "
            f"env={self.environment}, created={self.created_at.strftime('%Y-%m-%d')})>"
        )
