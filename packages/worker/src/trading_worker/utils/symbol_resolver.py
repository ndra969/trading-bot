"""Symbol resolution: asset class detection and broker→internal symbol conversion.

Separates symbol-to-asset-class mapping from the main bot orchestrator.
Caches asset class data from SymbolMapper to avoid repeated lookups.
"""

from typing import Any

from trading_core.utils.logger import get_logger

logger = get_logger(__name__)


class SymbolResolver:
    """Resolves trading symbols to asset classes and broker formats.

    Determines asset class via these strategies (in order):
        1. Exact match in symbol_mapper.asset_classes config
        2. Recursive lookup via broker→internal symbol conversion
        3. Pattern matching on symbol substring (USD, JPY, XAU, BTC, etc.)
        4. Fallback to "forex_major"
    """

    def __init__(self, symbol_mapper: Any = None, active_broker: str | None = None):
        """Initialize resolver.

        Args:
            symbol_mapper: SymbolMapper instance for broker conversion (optional)
            active_broker: Active broker name for reverse mapping lookup
        """
        self.symbol_mapper = symbol_mapper
        self.active_broker = active_broker
        self._asset_classes_cache: dict[str, list[str]] | None = None

    @property
    def _asset_classes(self) -> dict[str, list[str]]:
        """Lazy-load asset class mappings from symbol_mapper."""
        if self._asset_classes_cache is None and self.symbol_mapper is not None:
            self._asset_classes_cache = self.symbol_mapper.asset_classes
        return self._asset_classes_cache or {}

    def get_asset_class(self, symbol: str) -> str:
        """Determine asset class from symbol.

        Returns one of: "forex_major", "forex_jpy", "commodities", "crypto",
        "index", or the raw class name from config. Falls back to "forex_major"
        on any error (safe default).
        """
        try:
            # 1. Try exact match in config
            asset_class = self._lookup_in_config(symbol)
            if asset_class:
                return asset_class

            # 2. Try via broker→internal symbol conversion (avoid infinite recursion)
            internal_symbol = self.convert_broker_to_internal_symbol(symbol)
            if internal_symbol != symbol:
                asset_class = self._lookup_in_config(internal_symbol)
                if asset_class:
                    return asset_class

            # 3. Pattern matching fallback
            return self._classify_by_pattern(symbol)

        except Exception as e:
            logger.error(f"Error determining asset class for {symbol}: {e}")
            return "forex_major"  # Safe default

    def _lookup_in_config(self, symbol: str) -> str | None:
        """Look up symbol in configured asset class mappings."""
        for asset_class, symbols in self._asset_classes.items():
            if symbol not in symbols:
                continue
            if asset_class == "commodities":
                return "commodities"
            if asset_class == "forex":
                return "forex_jpy" if symbol.endswith("JPY") else "forex_major"
            if asset_class == "crypto":
                return "crypto"
            if asset_class == "index":
                return "index"
            return asset_class
        return None

    @staticmethod
    def _classify_by_pattern(symbol: str) -> str:
        """Classify symbol by pattern matching on substrings."""
        if any(c in symbol for c in ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]):
            return "forex_jpy" if "JPY" in symbol else "forex_major"
        if any(c in symbol for c in ["XAU", "XAG", "WTI", "BRENT"]):
            return "commodities"
        if any(c in symbol for c in ["BTC", "ETH", "LTC", "BCH", "XRP"]):
            return "crypto"
        if any(c in symbol for c in ["US30", "SPX", "NAS", "UK100", "GER", "JPN", "CHN"]):
            return "index"
        return "forex_major"

    def convert_broker_to_internal_symbol(self, symbol: str) -> str:
        """Convert broker-specific symbol back to internal format (e.g., EURUSDc → EURUSD).

        Strategy:
            1. Use symbol_mapper._reverse_mappings if available
            2. Strip common broker suffixes ('c', 'm') and retry
            3. Fallback to normalized broker symbol

        Returns the input symbol unchanged if no mapper is configured.
        """
        try:
            if not self.symbol_mapper:
                return symbol

            normalized = self.symbol_mapper.normalize_symbol(symbol)
            broker_name = (self.active_broker or "").lower()
            reverse_map = getattr(self.symbol_mapper, "_reverse_mappings", {})

            # Try direct reverse lookup
            broker_map = reverse_map.get(broker_name, {})
            if normalized in broker_map:
                return broker_map[normalized]

            # Try after stripping common suffixes
            clean = normalized.rstrip("cm")
            if clean in broker_map:
                return broker_map[clean]

            return normalized

        except Exception as e:
            logger.debug(f"Symbol conversion failed for {symbol}: {e}")
            return symbol
