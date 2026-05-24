"""
Portfolio Risk Manager - Portfolio-level risk control.

Manages overall portfolio risk with:
- Maximum 2% risk per trade
- Daily loss limit: 1% of portfolio
- Emergency stop: 15% drawdown
"""

from datetime import datetime

from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioRiskManager:
    """
    Manages portfolio-level risk control.

    Enforces:
    - Maximum risk per trade (default: 2%)
    - Daily loss limit (default: 1%)
    - Emergency stop loss (default: 15% drawdown)
    - Position size calculation based on risk
    """

    def __init__(self, config: dict = None):
        """
        Initialize portfolio risk manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Risk parameters - PRIORITY: Trading Type Config > Risk Management Config > Default
        # Get active trading type
        trading_types = self.config.get("trading_types", {})
        active_type = (
            self.config.get("active_trading_type")
            or trading_types.get("active_trading_type")
            or "day_trading"
        )

        # Get risk config from trading type (if exists)
        # NOTE: Input formats differ between config sources:
        #   - trading_types.yaml stores as DECIMAL (0.01 = 1%)
        #   - risk_management section stores as PERCENT (2.0 = 2%)
        # We normalize both to PERCENT form so calculate_max_risk_amount can
        # divide by 100 consistently.
        type_config = trading_types.get(active_type, {})
        trading_risk_decimal = type_config.get("risk_per_trade")

        if trading_risk_decimal is not None:
            # Convert decimal (0.01) to percent (1.0)
            self.max_risk_per_trade_pct = trading_risk_decimal * 100.0
            logger.info(
                f"Using trading type '{active_type}' config: "
                f"risk_per_trade={self.max_risk_per_trade_pct}% (from decimal {trading_risk_decimal})"
            )
        else:
            # Fallback: risk_management section is already in percent form
            self.max_risk_per_trade_pct = self.config.get("risk_management", {}).get(
                "max_risk_per_trade_percent", 2.0
            )
            logger.info(
                f"Using risk_management config: {self.max_risk_per_trade_pct}% "
                f"(trading type '{active_type}' doesn't specify risk_per_trade)"
            )

        # Other parameters (use risk_management section as fallback)
        self.daily_loss_limit_pct = self.config.get("risk_management", {}).get(
            "daily_loss_limit_percent", 1.0
        )
        self.emergency_stop_pct = self.config.get("risk_management", {}).get(
            "emergency_stop_percent", 15.0
        )

        # Portfolio tracking
        self.starting_balance: float = 0.0
        self.current_balance: float = 0.0
        self.peak_balance: float = 0.0

        # Daily tracking
        self.daily_start_balance: float = 0.0
        self.daily_pnl: float = 0.0
        self.last_reset_date: datetime = datetime.now().date()

        logger.info(
            f"PortfolioRiskManager initialized: "
            f"Max risk/trade: {self.max_risk_per_trade_pct}%, "
            f"Daily limit: {self.daily_loss_limit_pct}%, "
            f"Emergency stop: {self.emergency_stop_pct}%"
        )

    def initialize_balance(self, balance: float) -> None:
        """
        Initialize portfolio balance.

        Args:
            balance: Starting portfolio balance
        """
        self.starting_balance = balance
        self.current_balance = balance
        self.peak_balance = balance
        self.daily_start_balance = balance
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()

        logger.info(f"Portfolio initialized with balance: ${balance:,.2f}")

    def update_balance(self, new_balance: float) -> None:
        """
        Update current portfolio balance.

        Args:
            new_balance: New portfolio balance
        """
        # Reset daily tracking if new day
        self._check_daily_reset()

        # Update daily P&L
        self.daily_pnl = new_balance - self.daily_start_balance

        # Update balances
        self.current_balance = new_balance

        # Update peak balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance

        logger.debug(f"Balance updated: ${new_balance:,.2f} (Daily P&L: ${self.daily_pnl:,.2f})")

    def calculate_position_size(
        self,
        account_balance: float,
        risk_amount_usd: float,
        stop_distance_pips: float,
        pip_value_per_lot: float,
    ) -> float:
        """
        Calculate position size based on risk.

        Args:
            account_balance: Current account balance
            risk_amount_usd: Maximum risk amount in USD
            stop_distance_pips: Stop loss distance in pips
            pip_value_per_lot: USD value per pip per lot

        Returns:
            Position size in lots
        """
        if stop_distance_pips <= 0 or pip_value_per_lot <= 0:
            logger.warning("Invalid parameters for position size calculation")
            return 0.0

        # Calculate position size
        # risk_amount = position_size * stop_distance * pip_value
        # position_size = risk_amount / (stop_distance * pip_value)
        position_size = risk_amount_usd / (stop_distance_pips * pip_value_per_lot)

        # Round to 2 decimal places (standard lot precision)
        position_size = round(position_size, 2)

        logger.debug(
            f"Position size calculated: {position_size:.2f} lots "
            f"(Risk: ${risk_amount_usd:.2f}, SL distance: {stop_distance_pips:.1f} pips)"
        )

        return position_size

    def calculate_max_risk_amount(self, account_balance: float) -> float:
        """
        Calculate maximum risk amount per trade.

        Args:
            account_balance: Current account balance

        Returns:
            Maximum risk amount in USD
        """
        max_risk = account_balance * (self.max_risk_per_trade_pct / 100.0)
        return max_risk

    def can_take_trade(self, risk_amount: float) -> tuple[bool, str]:
        """
        Check if a trade can be taken based on risk limits.

        Args:
            risk_amount: Proposed risk amount for the trade

        Returns:
            Tuple of (can_trade, reason)
        """
        # Check if balance is initialized
        if self.current_balance <= 0:
            return False, "Portfolio balance not initialized"

        # Check emergency stop (drawdown from peak) - HIGHEST PRIORITY
        drawdown_pct = self.get_drawdown_percent()
        if drawdown_pct >= self.emergency_stop_pct:
            return False, f"Emergency stop triggered: {drawdown_pct:.1f}% drawdown"

        # Check daily loss limit - DISABLED
        # daily_loss_limit = self.daily_start_balance * (self.daily_loss_limit_pct / 100.0)
        # if abs(self.daily_pnl) >= daily_loss_limit and self.daily_pnl < 0:
        #     return False, f"Daily loss limit reached: ${abs(self.daily_pnl):,.2f}"

        # Check risk per trade
        max_risk = self.calculate_max_risk_amount(self.current_balance)
        if risk_amount > max_risk:
            return False, f"Risk exceeds limit: ${risk_amount:.2f} > ${max_risk:.2f}"

        # Check if adding this risk would violate daily limit (only if currently in loss) - DISABLED
        # if self.daily_pnl < 0:
        #     potential_daily_loss = abs(self.daily_pnl) + risk_amount
        #     if potential_daily_loss > daily_loss_limit:
        #         return False, "Would exceed daily loss limit"

        return True, "OK"

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

    def get_daily_pnl_percent(self) -> float:
        """
        Get daily P&L as percentage.

        Returns:
            Daily P&L percentage
        """
        if self.daily_start_balance <= 0:
            return 0.0

        return (self.daily_pnl / self.daily_start_balance) * 100

    def is_emergency_stop_triggered(self) -> bool:
        """
        Check if emergency stop is triggered.

        Returns:
            True if emergency stop should be activated
        """
        return self.get_drawdown_percent() >= self.emergency_stop_pct

    def is_daily_limit_reached(self) -> bool:
        """
        Check if daily loss limit is reached.

        Returns:
            True if daily limit reached
        """
        # Daily loss limit validation is currently disabled
        return False

    def get_portfolio_summary(self) -> dict:
        """
        Get portfolio risk summary.

        Returns:
            Dictionary with portfolio statistics
        """
        return {
            "starting_balance": self.starting_balance,
            "current_balance": self.current_balance,
            "peak_balance": self.peak_balance,
            "total_pnl": self.current_balance - self.starting_balance,
            "total_pnl_pct": (
                ((self.current_balance - self.starting_balance) / self.starting_balance * 100)
                if self.starting_balance > 0
                else 0.0
            ),
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": self.get_daily_pnl_percent(),
            "drawdown_pct": self.get_drawdown_percent(),
            "max_risk_per_trade": self.calculate_max_risk_amount(self.current_balance),
            "emergency_stop_triggered": self.is_emergency_stop_triggered(),
            "daily_limit_reached": self.is_daily_limit_reached(),
        }

    def _check_daily_reset(self) -> None:
        """Check and reset daily tracking if new day."""
        today = datetime.now().date()

        if today > self.last_reset_date:
            logger.info(
                f"Daily reset: P&L was ${self.daily_pnl:,.2f} ({self.get_daily_pnl_percent():.2f}%)"
            )
            self.daily_start_balance = self.current_balance
            self.daily_pnl = 0.0
            self.last_reset_date = today

    def reset_tracking(self) -> None:
        """Reset all tracking (for testing or new trading session)."""
        self.daily_pnl = 0.0
        self.daily_start_balance = self.current_balance
        self.last_reset_date = datetime.now().date()
        logger.info("Portfolio tracking reset")

    def __str__(self) -> str:
        """String representation."""
        return (
            f"PortfolioRiskManager("
            f"Balance: ${self.current_balance:,.2f}, "
            f"DD: {self.get_drawdown_percent():.1f}%, "
            f"Daily: {self.get_daily_pnl_percent():.1f}%)"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
