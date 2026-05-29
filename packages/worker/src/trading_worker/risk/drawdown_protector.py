"""
Drawdown Protector - Protects against excessive drawdown.

Features:
- Real-time drawdown calculation
- Warning at 10% drawdown
- Emergency stop at 15% drawdown
- Automatic position closure on emergency
"""

from datetime import datetime

from trading_core.utils.logger import get_logger

logger = get_logger(__name__)


class DrawdownProtector:
    """
    Protects portfolio from excessive drawdown.

    Monitors drawdown and triggers warnings/emergency stops.

    Levels:
    - Warning: 10% drawdown
    - Emergency: 15% drawdown (stops all trading)
    """

    def __init__(self, config: dict = None):
        """
        Initialize drawdown protector.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Drawdown thresholds
        self.warning_threshold_pct = self.config.get("risk_management", {}).get(
            "drawdown_warning_percent", 10.0
        )
        self.emergency_threshold_pct = self.config.get("risk_management", {}).get(
            "drawdown_emergency_percent", 15.0
        )

        # Portfolio tracking
        self.peak_balance: float = 0.0
        self.current_balance: float = 0.0
        self.starting_balance: float = 0.0

        # State tracking
        self.warning_triggered: bool = False
        self.emergency_triggered: bool = False
        self.warning_timestamp: datetime | None = None
        self.emergency_timestamp: datetime | None = None

        logger.info(
            f"DrawdownProtector initialized: "
            f"Warning: {self.warning_threshold_pct}%, "
            f"Emergency: {self.emergency_threshold_pct}%"
        )

    def initialize_balance(self, balance: float) -> None:
        """
        Initialize balance tracking.

        Args:
            balance: Starting balance
        """
        self.starting_balance = balance
        self.current_balance = balance
        self.peak_balance = balance
        self.warning_triggered = False
        self.emergency_triggered = False

        logger.info(f"Drawdown protector initialized with balance: ${balance:,.2f}")

    def update_balance(self, new_balance: float) -> None:
        """
        Update balance and check drawdown.

        Args:
            new_balance: New portfolio balance
        """
        self.current_balance = new_balance

        # Update peak balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
            # Reset warnings if recovering
            if self.warning_triggered:
                logger.info("Balance recovered above warning level")
                self.warning_triggered = False
                self.warning_timestamp = None
            if self.emergency_triggered:
                logger.info("Balance recovered above emergency level")
                self.emergency_triggered = False
                self.emergency_timestamp = None

        # Check drawdown levels
        drawdown_pct = self.get_drawdown_percent()

        # Check emergency threshold
        if not self.emergency_triggered and drawdown_pct >= self.emergency_threshold_pct:
            self.emergency_triggered = True
            self.emergency_timestamp = datetime.now()
            logger.critical(
                f"🚨 EMERGENCY STOP TRIGGERED! Drawdown: {drawdown_pct:.2f}% "
                f"(Peak: ${self.peak_balance:,.2f}, Current: ${new_balance:,.2f})"
            )

        # Check warning threshold
        elif not self.warning_triggered and drawdown_pct >= self.warning_threshold_pct:
            self.warning_triggered = True
            self.warning_timestamp = datetime.now()
            logger.warning(
                f"⚠️ DRAWDOWN WARNING! Drawdown: {drawdown_pct:.2f}% "
                f"(Peak: ${self.peak_balance:,.2f}, Current: ${new_balance:,.2f})"
            )

    def get_drawdown_percent(self) -> float:
        """
        Calculate current drawdown from peak.

        Returns:
            Drawdown percentage
        """
        if self.peak_balance <= 0:
            return 0.0

        drawdown = ((self.peak_balance - self.current_balance) / self.peak_balance) * 100
        return max(0.0, drawdown)

    def get_drawdown_amount(self) -> float:
        """
        Get drawdown amount in USD.

        Returns:
            Drawdown amount
        """
        return max(0.0, self.peak_balance - self.current_balance)

    def is_warning_triggered(self) -> bool:
        """
        Check if warning threshold is triggered.

        Returns:
            True if warning level reached
        """
        return self.warning_triggered

    def is_emergency_triggered(self) -> bool:
        """
        Check if emergency threshold is triggered.

        Returns:
            True if emergency level reached
        """
        return self.emergency_triggered

    def should_close_all_positions(self) -> bool:
        """
        Check if all positions should be closed.

        Returns:
            True if positions should be closed (emergency)
        """
        return self.emergency_triggered

    def get_drawdown_status(self) -> dict:
        """
        Get current drawdown status.

        Returns:
            Dictionary with drawdown information
        """
        return {
            "peak_balance": self.peak_balance,
            "current_balance": self.current_balance,
            "drawdown_pct": self.get_drawdown_percent(),
            "drawdown_amount": self.get_drawdown_amount(),
            "warning_triggered": self.warning_triggered,
            "emergency_triggered": self.emergency_triggered,
            "warning_threshold": self.warning_threshold_pct,
            "emergency_threshold": self.emergency_threshold_pct,
            "warning_timestamp": (
                self.warning_timestamp.isoformat() if self.warning_timestamp else None
            ),
            "emergency_timestamp": (
                self.emergency_timestamp.isoformat() if self.emergency_timestamp else None
            ),
        }

    def reset_protector(self) -> None:
        """Reset protector state (for testing or recovery)."""
        self.warning_triggered = False
        self.emergency_triggered = False
        self.warning_timestamp = None
        self.emergency_timestamp = None
        logger.info("Drawdown protector reset")

    def __str__(self) -> str:
        """String representation."""
        status = (
            "EMERGENCY"
            if self.emergency_triggered
            else ("WARNING" if self.warning_triggered else "OK")
        )
        return f"DrawdownProtector(DD: {self.get_drawdown_percent():.1f}%, Status: {status})"

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
