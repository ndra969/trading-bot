"""
Pip Calculator - Asset-specific pip calculations.

Handles pip size and pip value calculations for different asset classes.
Uses SymbolMapper to get asset class from YAML configuration.
"""

from trading_core.utils.logger import get_logger

logger = get_logger(__name__)


class PipCalculator:
    """
    Calculates pips and USD values for different asset classes.

    Uses SymbolMapper to determine asset class from YAML configuration,
    ensuring consistency with broker symbol mappings.
    """

    # Standard pip value per lot for major pairs (at 1.0 exchange rate)
    # For most forex pairs, 1 pip = $10 per standard lot (100,000 units)
    STANDARD_PIP_VALUE = 10.0  # USD per pip per standard lot

    def __init__(self):
        """Initialize pip calculator."""
        # Lazy load SymbolMapper to avoid circular imports
        self._symbol_mapper = None
        logger.debug("PipCalculator initialized")

    @property
    def symbol_mapper(self):
        """Lazy load SymbolMapper."""
        if self._symbol_mapper is None:
            from trading_worker.connectors.symbol_mapper import SymbolMapper

            self._symbol_mapper = SymbolMapper()
        return self._symbol_mapper

    def get_pip_size(self, symbol: str) -> float:
        """
        Get pip size for a symbol using SymbolMapper (from YAML config).

        Args:
            symbol: Trading symbol

        Returns:
            Pip size for the symbol
        """
        return self.symbol_mapper.get_pip_size(symbol)

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
        # Get pip value per lot from SymbolMapper (from YAML config)
        pip_value_per_lot = self.symbol_mapper.get_pip_value_per_lot(symbol)

        # Calculate pip value for the given volume
        pip_value = pip_value_per_lot * volume
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
        Determine asset class from symbol using SymbolMapper (from YAML config).

        Args:
            symbol: Trading symbol

        Returns:
            Asset class identifier (forex_major, forex_jpy, commodities, crypto, index)
        """
        # Use SymbolMapper to get asset class from YAML config
        asset_class = self.symbol_mapper.get_asset_class(symbol)

        # Map YAML asset class names to internal format
        # YAML uses: forex, commodity, crypto, index
        # Internal uses: forex_major, forex_jpy, commodities, crypto, index
        if asset_class == "forex":
            # Further classify forex pairs
            normalized = self.symbol_mapper.normalize_symbol(symbol)
            if "JPY" in normalized:
                return "forex_jpy"
            else:
                return "forex_major"
        elif asset_class == "commodities":
            return "commodities"
        elif asset_class in ["crypto", "index"]:
            return asset_class
        else:
            # Default to forex major if not found
            logger.warning(
                f"Unknown asset class '{asset_class}' for {symbol}, defaulting to forex_major"
            )
            return "forex_major"

    def __str__(self) -> str:
        """String representation."""
        return "PipCalculator(uses SymbolMapper from YAML config)"

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
