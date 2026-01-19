"""
Conservative Risk Manager - Week 15.5.4

Implements conservative risk management to stabilize system performance.

Key changes from standard risk manager:
- Reduced risk per trade: 1.0% → 0.5%
- Reduced max positions: 5 → 3
- Reduced portfolio risk: 2.0% → 1.5%
- Recovery mode: Activated at 5% drawdown
"""

from dataclasses import dataclass

from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RiskParameters:
    """Risk management parameters."""

    max_risk_per_trade: float = 0.5  # % of account per trade
    max_portfolio_risk: float = 1.5  # % of account total risk
    max_daily_loss: float = 1.0  # % of account max daily loss
    max_total_positions: int = 3  # Max simultaneous positions
    max_positions_per_symbol: int = 1  # Max positions per symbol


@dataclass
class RecoveryMode:
    """Recovery mode configuration."""

    enabled: bool = True
    trigger_drawdown: float = 5.0  # Activate at 5% drawdown
    reduced_risk: float = 0.25  # Ultra-conservative 0.25%
    max_positions: int = 1  # Only 1 position at a time
    exit_drawdown: float = 3.0  # Exit when drawdown < 3%


class ConservativeRiskManager:
    """
    Conservative risk manager with reduced risk parameters and recovery mode.

    Features:
    - Conservative position sizing (0.5% risk per trade)
    - Limited exposure (max 3 positions)
    - Recovery mode for drawdown protection
    - Emergency stop at 15% drawdown

    Usage:
        risk_mgr = ConservativeRiskManager(config)
        position_size = risk_mgr.calculate_position_size(account, symbol, entry, sl)
    """

    def __init__(self, config: dict = None):
        """
        Initialize conservative risk manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        risk_config = self.config.get("risk_management", {})

        # Load risk parameters (conservative defaults)
        self.max_risk_per_trade = risk_config.get("max_risk_per_trade", 0.5)
        self.max_portfolio_risk = risk_config.get("max_portfolio_risk", 1.5)
        self.max_daily_loss = risk_config.get("max_daily_loss", 1.0)
        self.max_total_positions = risk_config.get("max_total_positions", 3)
        self.max_positions_per_symbol = risk_config.get("max_positions_per_symbol", 1)

        # Load recovery mode config
        recovery_config = risk_config.get("recovery_mode", {})
        self.recovery_enabled = recovery_config.get("enabled", True)
        self.recovery_trigger_drawdown = recovery_config.get("trigger_drawdown", 5.0)
        self.recovery_reduced_risk = recovery_config.get("reduced_risk", 0.25)
        self.recovery_max_positions = recovery_config.get("max_positions", 1)
        self.recovery_exit_drawdown = recovery_config.get("exit_drawdown", 3.0)

        # Recovery mode state
        self.is_recovery_mode_active = False

        # Emergency stop
        self.emergency_stop_drawdown = 15.0

        logger.info(
            f"ConservativeRiskManager initialized: "
            f"risk={self.max_risk_per_trade}%, "
            f"max_positions={self.max_total_positions}, "
            f"recovery_mode={'enabled' if self.recovery_enabled else 'disabled'}"
        )

    def calculate_position_size(
        self,
        account: dict,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        pip_size: float = 0.0001,
        pip_value_per_lot: float = 10.0,
    ) -> float:
        """
        Calculate conservative position size.

        Args:
            account: Account dictionary with balance
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            pip_size: Pip size for symbol
            pip_value_per_lot: Value per pip per lot

        Returns:
            Position size in lots
        """
        balance = account.get("balance", 0.0)

        # Get active risk (normal or recovery mode)
        active_risk_percent = self.get_active_risk_per_trade()

        # Calculate risk amount
        risk_amount = balance * (active_risk_percent / 100)

        # Calculate stop loss distance in pips
        sl_distance = abs(entry_price - stop_loss) / pip_size

        # Calculate position size
        # Risk amount = Position size * SL distance * Pip value per lot
        # Position size = Risk amount / (SL distance * Pip value per lot)
        if sl_distance > 0 and pip_value_per_lot > 0:
            position_size = risk_amount / (sl_distance * pip_value_per_lot)
        else:
            position_size = 0.01  # Minimum

        # Round to 2 decimals
        position_size = round(position_size, 2)

        logger.debug(
            f"Position size calculated: {position_size} lots "
            f"(risk: {active_risk_percent}%, amount: ${risk_amount:.2f}, "
            f"SL: {sl_distance:.1f} pips)"
        )

        return position_size

    def get_active_risk_per_trade(self) -> float:
        """
        Get active risk per trade (normal or recovery mode).

        Returns:
            Risk percentage per trade
        """
        if self.is_recovery_mode_active and self.recovery_enabled:
            return self.recovery_reduced_risk
        else:
            return self.max_risk_per_trade

    def get_max_positions(self) -> int:
        """
        Get max positions (normal or recovery mode).

        Returns:
            Maximum number of positions
        """
        if self.is_recovery_mode_active and self.recovery_enabled:
            return self.recovery_max_positions
        else:
            return self.max_total_positions

    def should_activate_recovery_mode(self, current_drawdown: float) -> bool:
        """
        Check if recovery mode should be activated.

        Args:
            current_drawdown: Current drawdown percentage

        Returns:
            True if recovery mode should activate
        """
        if not self.recovery_enabled:
            return False

        return current_drawdown > self.recovery_trigger_drawdown

    def activate_recovery_mode(self) -> None:
        """Activate recovery mode."""
        if not self.is_recovery_mode_active:
            self.is_recovery_mode_active = True
            logger.warning(
                f"🚨 RECOVERY MODE ACTIVATED: "
                f"Risk reduced to {self.recovery_reduced_risk}%, "
                f"Max positions: {self.recovery_max_positions}"
            )

    def should_exit_recovery_mode(self, current_drawdown: float) -> bool:
        """
        Check if recovery mode should exit.

        Args:
            current_drawdown: Current drawdown percentage

        Returns:
            True if recovery mode should exit
        """
        if not self.is_recovery_mode_active:
            return False

        return current_drawdown < self.recovery_exit_drawdown

    def deactivate_recovery_mode(self) -> None:
        """Deactivate recovery mode."""
        if self.is_recovery_mode_active:
            self.is_recovery_mode_active = False
            logger.info(
                f"✅ RECOVERY MODE DEACTIVATED: "
                f"Returning to normal risk ({self.max_risk_per_trade}%)"
            )

    def is_emergency_stop_triggered(self, current_drawdown: float) -> bool:
        """
        Check if emergency stop is triggered.

        Args:
            current_drawdown: Current drawdown percentage

        Returns:
            True if emergency stop triggered (15% drawdown)
        """
        return current_drawdown > self.emergency_stop_drawdown

    def validate_parameters(self, params: RiskParameters) -> bool:
        """
        Validate risk parameters.

        Args:
            params: RiskParameters to validate

        Returns:
            True if parameters are valid
        """
        # Check risk per trade is reasonable (≤ 1%)
        if params.max_risk_per_trade > 1.0:
            logger.warning(f"Risk per trade too high: {params.max_risk_per_trade}%")
            return False

        # Check portfolio risk is reasonable (≤ 2%)
        if params.max_portfolio_risk > 2.0:
            logger.warning(f"Portfolio risk too high: {params.max_portfolio_risk}%")
            return False

        # Check max positions is reasonable (≤ 5)
        if params.max_total_positions > 5:
            logger.warning(f"Max positions too high: {params.max_total_positions}")
            return False

        return True

    def calculate_drawdown(self, starting_balance: float, current_equity: float) -> float:
        """
        Calculate current drawdown percentage.

        Args:
            starting_balance: Starting balance
            current_equity: Current equity

        Returns:
            Drawdown percentage
        """
        if starting_balance <= 0:
            return 0.0

        drawdown = ((starting_balance - current_equity) / starting_balance) * 100
        return max(0.0, drawdown)

    def update_recovery_mode(self, current_drawdown: float) -> None:
        """
        Update recovery mode based on current drawdown.

        Args:
            current_drawdown: Current drawdown percentage
        """
        if not self.recovery_enabled:
            return

        # Check if should activate
        if not self.is_recovery_mode_active:
            if self.should_activate_recovery_mode(current_drawdown):
                self.activate_recovery_mode()

        # Check if should deactivate
        else:
            if self.should_exit_recovery_mode(current_drawdown):
                self.deactivate_recovery_mode()

    def get_risk_summary(self) -> dict:
        """
        Get risk management summary.

        Returns:
            Dictionary with risk settings
        """
        return {
            "max_risk_per_trade": self.max_risk_per_trade,
            "max_portfolio_risk": self.max_portfolio_risk,
            "max_daily_loss": self.max_daily_loss,
            "max_total_positions": self.max_total_positions,
            "recovery_mode_active": self.is_recovery_mode_active,
            "active_risk_per_trade": self.get_active_risk_per_trade(),
            "active_max_positions": self.get_max_positions(),
        }

    def __str__(self) -> str:
        """String representation."""
        mode = "RECOVERY" if self.is_recovery_mode_active else "NORMAL"
        return (
            f"ConservativeRiskManager({mode}: "
            f"risk={self.get_active_risk_per_trade()}%, "
            f"max_pos={self.get_max_positions()})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
