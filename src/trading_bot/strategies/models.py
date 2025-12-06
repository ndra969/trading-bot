"""
Data models for trading strategies.

Contains signal and result models used across all strategies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SignalDirection(str, Enum):
    """Trading signal direction."""

    BUY = "BUY"
    SELL = "SELL"


class SignalStatus(str, Enum):
    """Trading signal status."""

    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


@dataclass
class StrategyResult:
    """
    Individual strategy analysis result.

    Represents the output from a single strategy's analysis of a symbol.
    """

    strategy_name: str
    symbol: str
    score: float  # 0-100 confidence score
    direction: SignalDirection | None = None
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    timeframe: str = "H1"

    def __post_init__(self):
        """Validate result after initialization."""
        if not 0 <= self.score <= 100:
            raise ValueError(f"Score must be between 0-100, got {self.score}")

        if self.direction and not isinstance(self.direction, SignalDirection):
            self.direction = SignalDirection(self.direction)

    @property
    def has_signal(self) -> bool:
        """Check if result contains a trading signal."""
        return (
            self.direction is not None
            and self.entry_price is not None
            and self.stop_loss is not None
        )

    @property
    def risk_reward_ratio(self) -> float | None:
        """Calculate risk/reward ratio."""
        if not self.has_signal or self.take_profit is None:
            return None

        if self.direction == SignalDirection.BUY:
            risk = self.entry_price - self.stop_loss
            reward = self.take_profit - self.entry_price
        else:  # SELL
            risk = self.stop_loss - self.entry_price
            reward = self.entry_price - self.take_profit

        if risk <= 0:
            return None

        return reward / risk

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "score": self.score,
            "direction": self.direction.value if self.direction else None,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "has_signal": self.has_signal,
            "risk_reward_ratio": self.risk_reward_ratio,
        }


@dataclass
class TradingSignal:
    """
    Unified trading signal from aggregated strategies.

    Represents a final actionable trading signal after confluence analysis.
    """

    signal_id: str
    symbol: str
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    confluence_score: float  # Weighted score from all strategies
    risk_reward_ratio: float
    strategy_scores: dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    timeframe: str = "H1"
    status: SignalStatus = SignalStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate signal after initialization."""
        if not 0 <= self.confluence_score <= 100:
            raise ValueError(f"Confluence score must be between 0-100, got {self.confluence_score}")

        if self.risk_reward_ratio < 0:
            raise ValueError(f"Risk/reward ratio must be positive, got {self.risk_reward_ratio}")

        if not isinstance(self.direction, SignalDirection):
            self.direction = SignalDirection(self.direction)

        if not isinstance(self.status, SignalStatus):
            self.status = SignalStatus(self.status)

        # Validate prices
        if self.entry_price <= 0 or self.stop_loss <= 0 or self.take_profit <= 0:
            raise ValueError("All prices must be positive")

        # Validate price logic for BUY
        if self.direction == SignalDirection.BUY:
            if self.stop_loss >= self.entry_price:
                raise ValueError("BUY signal: stop_loss must be below entry_price")
            if self.take_profit <= self.entry_price:
                raise ValueError("BUY signal: take_profit must be above entry_price")

        # Validate price logic for SELL
        if self.direction == SignalDirection.SELL:
            if self.stop_loss <= self.entry_price:
                raise ValueError("SELL signal: stop_loss must be above entry_price")
            if self.take_profit >= self.entry_price:
                raise ValueError("SELL signal: take_profit must be below entry_price")

    @property
    def risk_pips(self) -> float:
        """Calculate risk in pips."""
        if self.direction == SignalDirection.BUY:
            return abs(self.entry_price - self.stop_loss)
        else:  # SELL
            return abs(self.stop_loss - self.entry_price)

    @property
    def reward_pips(self) -> float:
        """Calculate reward in pips."""
        if self.direction == SignalDirection.BUY:
            return abs(self.take_profit - self.entry_price)
        else:  # SELL
            return abs(self.entry_price - self.take_profit)

    def is_valid(self) -> bool:
        """Check if signal is valid and ready for execution."""
        return self.status == SignalStatus.VALIDATED or self.status == SignalStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "direction": self.direction.value,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "confluence_score": self.confluence_score,
            "risk_reward_ratio": self.risk_reward_ratio,
            "risk_pips": self.risk_pips,
            "reward_pips": self.reward_pips,
            "strategy_scores": self.strategy_scores,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "status": self.status.value,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Signal({self.direction.value} {self.symbol} @ {self.entry_price:.5f}, "
            f"SL: {self.stop_loss:.5f}, TP: {self.take_profit:.5f}, "
            f"R:R: {self.risk_reward_ratio:.2f}, Score: {self.confluence_score:.1f})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
