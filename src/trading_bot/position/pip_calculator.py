"""
Pip Calculator - Asset-specific pip calculations.

Handles pip size and pip value calculations for different asset classes.
"""

from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class PipCalculator:
    """
    Calculates pips and USD values for different asset classes.

    Pip sizes by asset class:
    - Forex Major Pairs: 0.0001 (EURUSD, GBPUSD, etc.)
    - Forex JPY Pairs: 0.01 (USDJPY, EURJPY, etc.)
    - Commodities (Gold): 0.1 (XAUUSD)
    - Crypto: 1.0 (BTCUSD, ETHUSD)
    """

    # Pip sizes by asset class
    PIP_SIZES = {
        "forex_major": 0.0001,
        "forex_jpy": 0.01,
        "commodities": 0.1,
        "crypto": 1.0,
    }

    # Standard pip value per lot for major pairs (at 1.0 exchange rate)
    # For most forex pairs, 1 pip = $10 per standard lot (100,000 units)
    STANDARD_PIP_VALUE = 10.0  # USD per pip per standard lot

    def __init__(self):
        """Initialize pip calculator."""
        logger.debug("PipCalculator initialized")

    def get_pip_size(self, symbol: str) -> float:
        """
        Get pip size for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Pip size for the symbol
        """
        asset_class = self._determine_asset_class(symbol)
        return self.PIP_SIZES[asset_class]

    def calculate_pips(
        self, symbol: str, entry_price: float, current_price: float, position_type: str
    ) -> float:
        """
        Calculate profit/loss in pips.

        Args:
            symbol: Trading symbol
            entry_price: Position entry price
            current_price: Current market price
            position_type: "BUY" or "SELL"

        Returns:
            Profit/loss in pips
        """
        pip_size = self.get_pip_size(symbol)

        if position_type == "BUY":
            # BUY: profit when price goes up
            price_diff = current_price - entry_price
        else:  # SELL
            # SELL: profit when price goes down
            price_diff = entry_price - current_price

        # Convert price difference to pips
        pips = price_diff / pip_size
        return pips

    def calculate_pip_value(self, symbol: str, volume: float) -> float:
        """
        Calculate USD value per pip for a position.

        Args:
            symbol: Trading symbol
            volume: Position volume (lot size)

        Returns:
            USD value per pip
        """
        asset_class = self._determine_asset_class(symbol)

        # Base pip value per standard lot
        base_pip_value = self.STANDARD_PIP_VALUE

        # Adjust for asset class
        if asset_class == "forex_jpy":
            # JPY pairs have different pip value calculation
            # 1 pip for JPY = 0.01, so value is 100x higher
            base_pip_value = self.STANDARD_PIP_VALUE
        elif asset_class == "commodities":
            # Gold: 1 pip = 0.1, value varies by contract size
            # Standard gold lot = 100 oz, 1 pip = $10
            base_pip_value = 10.0
        elif asset_class == "crypto":
            # Crypto: 1 pip = $1, value = volume
            base_pip_value = 1.0

        # Calculate pip value for the given volume
        pip_value = base_pip_value * volume
        return pip_value

    def calculate_usd_amount(
        self, symbol: str, entry_price: float, target_price: float, volume: float
    ) -> float:
        """
        Calculate USD amount for a price movement.

        Args:
            symbol: Trading symbol
            entry_price: Starting price
            target_price: Target price
            volume: Position volume (lot size)

        Returns:
            USD amount for the price movement
        """
        pip_size = self.get_pip_size(symbol)
        price_diff = abs(target_price - entry_price)
        pips = price_diff / pip_size
        pip_value = self.calculate_pip_value(symbol, volume)
        return pips * pip_value

    def calculate_risk_reward_usd(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        volume: float,
    ) -> tuple[float, float, float]:
        """
        Calculate risk and reward in USD.

        Args:
            symbol: Trading symbol
            entry_price: Position entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            volume: Position volume (lot size)

        Returns:
            Tuple of (risk_usd, reward_usd, risk_reward_ratio)
        """
        risk_usd = self.calculate_usd_amount(symbol, entry_price, stop_loss, volume)
        reward_usd = self.calculate_usd_amount(symbol, entry_price, take_profit, volume)

        risk_reward_ratio = reward_usd / risk_usd if risk_usd > 0 else 0.0

        return risk_usd, reward_usd, risk_reward_ratio

    def _determine_asset_class(self, symbol: str) -> str:
        """
        Determine asset class from symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Asset class identifier
        """
        symbol = symbol.upper()

        # Check for JPY pairs
        if "JPY" in symbol:
            return "forex_jpy"

        # Check for commodities (Gold)
        if symbol in ["XAUUSD", "GOLD", "XAGUSD", "SILVER"]:
            return "commodities"

        # Check for crypto
        if symbol in ["BTCUSD", "ETHUSD", "BTCUSDT", "ETHUSDT"]:
            return "crypto"

        # Default to forex major
        return "forex_major"

    def __str__(self) -> str:
        """String representation."""
        return "PipCalculator(forex: 0.0001, jpy: 0.01, gold: 0.1, crypto: 1.0)"

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
