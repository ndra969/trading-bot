# Asset Configuration Guide

This guide provides comprehensive information about asset-specific configurations, pip calculations, position management rules, and trading hours for different asset classes.

## Asset Classification System

The trading bot categorizes all tradable instruments into distinct asset classes, each with specific characteristics and trading rules.

### Asset Class Overview

```python
ASSET_CLASSES = {
    "forex_major": {
        "description": "Major currency pairs with USD",
        "characteristics": ["High liquidity", "Tight spreads", "24/5 trading"],
        "symbols": ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]
    },
    "forex_jpy": {
        "description": "Japanese Yen pairs with different pip calculation",
        "characteristics": ["Different pip value", "High volatility", "Asia session activity"],
        "symbols": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY"]
    },
    "commodities": {
        "description": "Precious metals and energy commodities",
        "characteristics": ["Higher volatility", "Economic sensitivity", "Limited hours"],
        "symbols": ["XAUUSD", "XAGUSD", "XBRUSD", "XTIUSD"]
    },
    "crypto": {
        "description": "Cryptocurrency pairs",
        "characteristics": ["24/7 trading", "High volatility", "Large pip values"],
        "symbols": ["BTCUSD", "ETHUSD", "ADAUSD", "DOTUSD"]
    },
    "indices": {
        "description": "Stock market indices",
        "characteristics": ["Market hours dependent", "Economic correlation"],
        "symbols": ["US30", "SPX500", "NAS100", "GER40", "UK100"]
    }
}
```

## Pip Calculation System

### Critical Pip Value Rules

**CRITICAL**: Each asset category has different pip calculations that directly affect position sizing, profit calculations, and risk management.

```python
# Core pip values by asset class - CRITICAL for position sizing
PIP_VALUES = {
    "forex_major": {
        "pip": 0.0001,
        "description": "Standard 4-decimal place currencies",
        "examples": {
            "EURUSD": "1.0850 -> 1.0851 = 1 pip",
            "GBPUSD": "1.2650 -> 1.2651 = 1 pip"
        }
    },
    "forex_jpy": {
        "pip": 0.01,
        "description": "Japanese Yen pairs use 2-decimal places",
        "examples": {
            "USDJPY": "150.50 -> 150.51 = 1 pip",
            "EURJPY": "160.25 -> 160.26 = 1 pip"
        }
    },
    "commodities": {
        "pip": {
            "XAUUSD": 0.1,     # Gold: $2000.5 -> $2000.6 = 1 pip
            "XAGUSD": 0.001,   # Silver: $25.500 -> $25.501 = 1 pip
            "XBRUSD": 0.01,    # Brent Oil: $75.50 -> $75.51 = 1 pip
            "XTIUSD": 0.01     # WTI Oil: $70.25 -> $70.26 = 1 pip
        },
        "description": "Varies by commodity type"
    },
    "crypto": {
        "pip": {
            "BTCUSD": 1.0,     # Bitcoin: $50000 -> $50001 = 1 pip
            "ETHUSD": 0.1,     # Ethereum: $3000.0 -> $3000.1 = 1 pip
            "ADAUSD": 0.0001,  # Cardano: $0.5000 -> $0.5001 = 1 pip
            "DOTUSD": 0.001    # Polkadot: $5.000 -> $5.001 = 1 pip
        },
        "description": "Varies significantly by crypto pair"
    },
    "indices": {
        "pip": {
            "US30": 1.0,       # Dow Jones: 35000 -> 35001 = 1 pip
            "SPX500": 0.1,     # S&P 500: 4500.0 -> 4500.1 = 1 pip
            "NAS100": 0.1,     # Nasdaq: 15000.0 -> 15000.1 = 1 pip
            "GER40": 0.1,      # DAX: 16000.0 -> 16000.1 = 1 pip
            "UK100": 0.1       # FTSE: 7500.0 -> 7500.1 = 1 pip
        },
        "description": "Index-specific pip calculations"
    }
}
```

### Pip Calculation Implementation

```python
class AssetPipCalculator:
    """
    Centralized pip calculation system for all asset classes
    """

    def __init__(self):
        self.pip_values = PIP_VALUES
        self.asset_mapping = self._build_asset_mapping()

    def _build_asset_mapping(self) -> Dict[str, str]:
        """Build symbol to asset class mapping"""
        mapping = {}
        for asset_class, config in ASSET_CLASSES.items():
            for symbol in config["symbols"]:
                mapping[symbol] = asset_class
        return mapping

    def get_asset_class(self, symbol: str) -> Optional[str]:
        """Get asset class for symbol"""
        return self.asset_mapping.get(symbol)

    def get_pip_value(self, symbol: str) -> float:
        """Get pip value for specific symbol"""
        asset_class = self.get_asset_class(symbol)
        if not asset_class:
            raise ValueError(f"Unknown symbol: {symbol}")

        pip_config = self.pip_values[asset_class]["pip"]

        # Handle simple pip values
        if isinstance(pip_config, (int, float)):
            return float(pip_config)

        # Handle symbol-specific pip values
        if isinstance(pip_config, dict):
            if symbol in pip_config:
                return float(pip_config[symbol])
            else:
                raise ValueError(f"No pip value configured for {symbol}")

        raise ValueError(f"Invalid pip configuration for {asset_class}")

    def calculate_profit_pips(self, symbol: str, entry_price: float,
                            current_price: float, direction: str) -> float:
        """Calculate profit/loss in pips"""
        pip_value = self.get_pip_value(symbol)

        if direction.upper() == "BUY":
            price_diff = current_price - entry_price
        else:  # SELL
            price_diff = entry_price - current_price

        return price_diff / pip_value

    def calculate_monetary_value(self, symbol: str, pips: float,
                               lot_size: float = 1.0) -> float:
        """Calculate monetary value of pip movement"""
        asset_class = self.get_asset_class(symbol)
        pip_value = self.get_pip_value(symbol)

        # Standard lot sizes by asset class
        standard_lots = {
            "forex_major": 100000,
            "forex_jpy": 100000,
            "commodities": {"XAUUSD": 100, "XAGUSD": 5000, "XBRUSD": 1000, "XTIUSD": 1000},
            "crypto": {"BTCUSD": 1, "ETHUSD": 1, "ADAUSD": 1, "DOTUSD": 1},
            "indices": {"US30": 1, "SPX500": 1, "NAS100": 1, "GER40": 1, "UK100": 1}
        }

        lot_config = standard_lots[asset_class]
        if isinstance(lot_config, dict):
            contract_size = lot_config.get(symbol, 1)
        else:
            contract_size = lot_config

        return pips * pip_value * contract_size * lot_size

    def validate_pip_calculation(self, symbol: str, expected_pips: float,
                                entry_price: float, target_price: float,
                                direction: str) -> bool:
        """Validate pip calculation for testing"""
        calculated_pips = self.calculate_profit_pips(
            symbol, entry_price, target_price, direction
        )
        tolerance = 0.1  # Allow 0.1 pip tolerance
        return abs(calculated_pips - expected_pips) <= tolerance
```

## Position Management by Asset Class

### Asset-Specific Position Rules

```yaml
# config/asset_position_management.yaml
position_management:
  forex_major:
    # Base configuration
    pip_value: 0.0001
    min_sl_pips: 15
    max_sl_pips: 50
    risk_per_trade: 0.005

    # Breakeven settings
    breakeven:
      trigger_pips: 15
      buffer_pips: 0.5
      enabled: true

    # Trailing stop settings
    trailing:
      start_pips_from_sl: 20
      distance_pips: 15
      acceleration_factor: 1.2
      max_distance_pips: 50

    # Partial close settings
    partial_close:
      enabled: true
      levels: [20, 40, 60]  # pips from entry
      percentages: [0.25, 0.25, 0.5]
      min_remaining_volume: 0.01

    # Risk limits
    risk_limits:
      max_positions: 5
      max_exposure_per_symbol: 0.02
      correlation_limit: 0.70

  forex_jpy:
    pip_value: 0.01
    min_sl_pips: 15
    max_sl_pips: 50
    risk_per_trade: 0.005

    breakeven:
      trigger_pips: 18    # Slightly higher due to volatility
      buffer_pips: 0.8
      enabled: true

    trailing:
      start_pips_from_sl: 25
      distance_pips: 18
      acceleration_factor: 1.1
      max_distance_pips: 60

    partial_close:
      enabled: true
      levels: [25, 50, 75]
      percentages: [0.25, 0.25, 0.5]
      min_remaining_volume: 0.01

    risk_limits:
      max_positions: 4    # Lower due to higher volatility
      max_exposure_per_symbol: 0.015
      correlation_limit: 0.65

  commodities:
    # Gold-specific settings
    XAUUSD:
      pip_value: 0.1
      min_sl_pips: 80
      max_sl_pips: 200
      risk_per_trade: 0.003

      breakeven:
        trigger_pips: 150
        buffer_pips: 5
        enabled: true

      trailing:
        start_pips_from_sl: 200
        distance_pips: 100
        acceleration_factor: 1.3
        max_distance_pips: 300

      partial_close:
        enabled: true
        levels: [100, 200, 300]
        percentages: [0.25, 0.25, 0.5]

    # Silver-specific settings
    XAGUSD:
      pip_value: 0.001
      min_sl_pips: 100
      max_sl_pips: 300
      risk_per_trade: 0.003

      breakeven:
        trigger_pips: 200
        buffer_pips: 10

      trailing:
        start_pips_from_sl: 250
        distance_pips: 150

    risk_limits:
      max_positions: 3
      max_exposure_per_symbol: 0.01
      correlation_limit: 0.60

  crypto:
    # Bitcoin settings
    BTCUSD:
      pip_value: 1.0
      min_sl_pips: 300
      max_sl_pips: 800
      risk_per_trade: 0.002

      breakeven:
        trigger_pips: 400
        buffer_pips: 20

      trailing:
        start_pips_from_sl: 500
        distance_pips: 300
        acceleration_factor: 1.5

      partial_close:
        enabled: true
        levels: [300, 600, 900]
        percentages: [0.30, 0.30, 0.40]

    # Ethereum settings
    ETHUSD:
      pip_value: 0.1
      min_sl_pips: 250
      max_sl_pips: 600
      risk_per_trade: 0.002

    risk_limits:
      max_positions: 2
      max_exposure_per_symbol: 0.008
      correlation_limit: 0.50

  indices:
    # US30 (Dow Jones) settings
    US30:
      pip_value: 1.0
      min_sl_pips: 100
      max_sl_pips: 400
      risk_per_trade: 0.004

      breakeven:
        trigger_pips: 150
        buffer_pips: 10

      trailing:
        start_pips_from_sl: 200
        distance_pips: 120

    risk_limits:
      max_positions: 3
      max_exposure_per_symbol: 0.015
      correlation_limit: 0.75
```

### Position Management Implementation

```python
class AssetSpecificPositionManager:
    """
    Position manager with asset-specific rules and calculations
    """

    def __init__(self, config_path: str = "config/asset_position_management.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['position_management']

        self.pip_calculator = AssetPipCalculator()

    def get_asset_config(self, symbol: str) -> Dict:
        """Get asset-specific configuration"""
        asset_class = self.pip_calculator.get_asset_class(symbol)

        if asset_class in self.config:
            asset_config = self.config[asset_class]

            # Check for symbol-specific overrides
            if symbol in asset_config:
                # Merge asset class config with symbol-specific config
                base_config = {k: v for k, v in asset_config.items() if k != symbol}
                symbol_config = asset_config[symbol]

                # Symbol config overrides asset class config
                return {**base_config, **symbol_config}
            else:
                return asset_config

        raise ValueError(f"No configuration found for asset class: {asset_class}")

    async def calculate_position_size(self, symbol: str, entry_price: float,
                                    stop_loss: float, account_balance: float) -> float:
        """Calculate position size based on asset-specific risk"""
        config = self.get_asset_config(symbol)
        risk_per_trade = config['risk_per_trade']

        # Calculate risk in pips
        risk_pips = self.pip_calculator.calculate_profit_pips(
            symbol, entry_price, stop_loss, "BUY"  # Direction doesn't matter for distance
        )
        risk_pips = abs(risk_pips)

        # Calculate monetary risk per pip
        monetary_risk_per_pip = self.pip_calculator.calculate_monetary_value(
            symbol, 1.0, 1.0  # 1 pip, 1 lot
        )

        # Calculate maximum risk amount
        max_risk_amount = account_balance * risk_per_trade

        # Calculate position size
        position_size = max_risk_amount / (risk_pips * monetary_risk_per_pip)

        # Apply asset-specific limits
        min_volume = config.get('min_volume', 0.01)
        max_volume = config.get('max_volume', 10.0)

        return max(min_volume, min(position_size, max_volume))

    async def should_trigger_breakeven(self, symbol: str, position) -> bool:
        """Check if breakeven should be triggered"""
        config = self.get_asset_config(symbol)
        breakeven_config = config.get('breakeven', {})

        if not breakeven_config.get('enabled', False):
            return False

        # Calculate current profit in pips
        current_pips = self.pip_calculator.calculate_profit_pips(
            symbol, position.entry_price, position.current_price, position.direction
        )

        trigger_pips = breakeven_config['trigger_pips']
        return current_pips >= trigger_pips

    async def calculate_breakeven_price(self, symbol: str, position) -> float:
        """Calculate breakeven price with buffer"""
        config = self.get_asset_config(symbol)
        breakeven_config = config.get('breakeven', {})

        buffer_pips = breakeven_config.get('buffer_pips', 0)
        pip_value = self.pip_calculator.get_pip_value(symbol)

        if position.direction.upper() == "BUY":
            return position.entry_price + (buffer_pips * pip_value)
        else:
            return position.entry_price - (buffer_pips * pip_value)

    async def should_start_trailing(self, symbol: str, position) -> bool:
        """Check if trailing stop should be activated"""
        config = self.get_asset_config(symbol)
        trailing_config = config.get('trailing', {})

        if not trailing_config.get('enabled', True):
            return False

        # Check if we've moved enough pips from stop loss
        current_pips = self.pip_calculator.calculate_profit_pips(
            symbol, position.entry_price, position.current_price, position.direction
        )

        start_pips = trailing_config['start_pips_from_sl']
        return current_pips >= start_pips

    async def calculate_trailing_stop(self, symbol: str, position) -> float:
        """Calculate new trailing stop price"""
        config = self.get_asset_config(symbol)
        trailing_config = config.get('trailing', {})

        distance_pips = trailing_config['distance_pips']
        pip_value = self.pip_calculator.get_pip_value(symbol)

        if position.direction.upper() == "BUY":
            return position.current_price - (distance_pips * pip_value)
        else:
            return position.current_price + (distance_pips * pip_value)

    async def get_partial_close_levels(self, symbol: str) -> List[Dict]:
        """Get partial close levels for symbol"""
        config = self.get_asset_config(symbol)
        partial_config = config.get('partial_close', {})

        if not partial_config.get('enabled', False):
            return []

        levels = partial_config['levels']
        percentages = partial_config['percentages']

        return [
            {'pips': level, 'percentage': percentage}
            for level, percentage in zip(levels, percentages)
        ]

    async def validate_position_limits(self, symbol: str, proposed_volume: float) -> bool:
        """Validate position against asset-specific limits"""
        config = self.get_asset_config(symbol)
        risk_limits = config.get('risk_limits', {})

        # Check maximum positions for asset class
        asset_class = self.pip_calculator.get_asset_class(symbol)
        current_positions = await self.get_active_positions_count(asset_class)
        max_positions = risk_limits.get('max_positions', 10)

        if current_positions >= max_positions:
            return False

        # Check maximum exposure per symbol
        current_exposure = await self.get_symbol_exposure(symbol)
        max_exposure = risk_limits.get('max_exposure_per_symbol', 0.05)

        if (current_exposure + proposed_volume) > max_exposure:
            return False

        return True
```

## Trading Hours by Asset Class

### Comprehensive Trading Hours Configuration

```yaml
# config/asset_trading_hours.yaml
asset_trading_hours:
  forex_major:
    trading_days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
    excluded_days: ["saturday", "sunday"]

    # 24/5 trading (Sunday 17:00 EST to Friday 17:00 EST)
    start_time: "22:00"  # Sunday 22:00 GMT (17:00 EST)
    end_time: "22:00"    # Friday 22:00 GMT (17:00 EST)

    # Buffer periods to avoid spread widening
    buffer_before_close: 60    # 1 hour before close
    buffer_after_open: 30      # 30 minutes after open

    # Session-specific settings
    sessions:
      sydney:
        start: "22:00"
        end: "07:00"
        description: "Low volatility Asian session"

      tokyo:
        start: "00:00"
        end: "09:00"
        description: "Asian session with JPY activity"

      london:
        start: "08:00"
        end: "17:00"
        description: "European session - high activity"

      new_york:
        start: "13:00"
        end: "22:00"
        description: "US session - highest volatility"

    # Avoid trading during low liquidity
    avoid_periods:
      - name: "Christmas Week"
        start_date: "12-24"
        end_date: "01-02"
      - name: "Summer Doldrums"
        start_date: "07-15"
        end_date: "08-15"
        reduced_activity: true

  forex_jpy:
    # Inherits from forex_major but with specific sessions
    inherits: "forex_major"

    # JPY pairs are most active during Asian session
    preferred_sessions: ["tokyo", "london_tokyo_overlap"]

    sessions:
      london_tokyo_overlap:
        start: "08:00"
        end: "09:00"
        description: "High volatility overlap period"

  commodities:
    # Gold and Silver trading hours
    XAUUSD:
      trading_days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
      start_time: "00:00"  # Monday 00:00 GMT
      end_time: "21:00"    # Friday 21:00 GMT

      buffer_before_close: 120  # 2 hours (spread widens)
      buffer_after_open: 60     # 1 hour

      # Gold-specific sessions
      sessions:
        asian:
          start: "00:00"
          end: "08:00"
          activity: "medium"

        london_am_fix:
          start: "10:30"
          end: "10:30"
          activity: "high"
          description: "London AM Gold Fix"

        london_pm_fix:
          start: "15:00"
          end: "15:00"
          activity: "high"
          description: "London PM Gold Fix"

        us_session:
          start: "13:00"
          end: "21:00"
          activity: "high"

      # Avoid during major economic events
      avoid_events:
        - "FOMC_meetings"
        - "NFP_releases"
        - "inflation_data"

    XAGUSD:
      inherits: "XAUUSD"
      # Silver follows gold but with higher volatility buffers
      buffer_before_close: 180  # 3 hours

    # Oil trading hours
    XBRUSD:
      trading_days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
      start_time: "01:00"   # Monday 01:00 GMT
      end_time: "21:00"     # Friday 21:00 GMT

      buffer_before_close: 120
      buffer_after_open: 60

      sessions:
        asian:
          start: "01:00"
          end: "08:00"
          activity: "low"

        european:
          start: "08:00"
          end: "16:00"
          activity: "medium"

        us_session:
          start: "14:30"
          end: "21:00"
          activity: "high"
          description: "US trading session with EIA data"

  crypto:
    # 24/7 trading for all crypto pairs
    trading_days: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    excluded_days: []

    start_time: "00:00"
    end_time: "23:59"

    buffer_before_close: 0
    buffer_after_open: 0

    # Crypto has different activity patterns
    sessions:
      asian_quiet:
        start: "00:00"
        end: "08:00"
        activity: "low"

      european_wakup:
        start: "08:00"
        end: "16:00"
        activity: "medium"

      us_active:
        start: "16:00"
        end: "00:00"
        activity: "high"
        description: "Most active crypto trading period"

    # Crypto-specific considerations
    considerations:
      - "Weekend trading available but lower volume"
      - "US session typically most active"
      - "Major news events can cause 24/7 volatility"

  indices:
    # Each index has specific trading hours
    US30:
      trading_days: ["monday", "tuesday", "wednesday", "thursday", "friday"]

      # Dow Jones futures trading
      start_time: "00:00"  # Sunday 18:00 EST (Monday 00:00 GMT)
      end_time: "22:00"    # Friday 17:00 EST (Friday 22:00 GMT)

      buffer_before_close: 30
      buffer_after_open: 30

      # US market hours
      cash_market_hours:
        start: "14:30"  # 9:30 EST
        end: "21:00"    # 4:00 EST
        description: "NYSE trading hours - highest activity"

      # Avoid during market holidays
      market_holidays:
        - "New Year's Day"
        - "Independence Day"
        - "Thanksgiving"
        - "Christmas Day"

    SPX500:
      inherits: "US30"
      description: "S&P 500 Index futures"

    NAS100:
      inherits: "US30"
      description: "Nasdaq 100 futures"
      # Tech-heavy index, may have extended activity

    GER40:
      trading_days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
      start_time: "01:00"  # Monday 01:00 GMT
      end_time: "22:00"    # Friday 22:00 GMT

      cash_market_hours:
        start: "08:00"   # 9:00 CET
        end: "16:30"     # 17:30 CET
        description: "XETRA trading hours"

    UK100:
      trading_days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
      start_time: "01:00"  # Monday 01:00 GMT
      end_time: "21:00"    # Friday 21:00 GMT

      cash_market_hours:
        start: "08:00"   # 8:00 GMT
        end: "16:30"     # 16:30 GMT
        description: "LSE trading hours"

# Holiday calendar by region
holiday_calendar:
  global:
    - name: "New Year's Day"
      date: "01-01"
      affects: ["all"]

    - name: "Christmas Day"
      date: "12-25"
      affects: ["all"]

  us:
    - name: "Independence Day"
      date: "07-04"
      affects: ["indices", "commodities"]

    - name: "Thanksgiving"
      date: "11-28"  # 4th Thursday of November
      affects: ["indices"]
      early_close: "18:00"  # 1:00 PM EST

  uk:
    - name: "Boxing Day"
      date: "12-26"
      affects: ["forex_major", "indices"]

  eu:
    - name: "Good Friday"
      date: "variable"  # Calculated each year
      affects: ["forex_major", "indices"]
```

### Trading Hours Validator Implementation

```python
class AssetTradingHoursValidator:
    """
    Comprehensive trading hours validation for all asset classes
    """

    def __init__(self, config_path: str = "config/asset_trading_hours.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.pip_calculator = AssetPipCalculator()
        self.server_tz = pytz.UTC

    def is_trading_allowed(self, symbol: str, current_time: Optional[datetime] = None) -> bool:
        """
        Comprehensive trading hours validation for specific symbol
        """
        if current_time is None:
            current_time = datetime.now(self.server_tz)

        # Get asset-specific trading hours
        hours_config = self._get_trading_hours_config(symbol)

        if not hours_config:
            return False

        # Check all validation criteria
        checks = [
            self._is_trading_day(current_time, hours_config),
            self._is_within_trading_hours(current_time, hours_config),
            not self._is_holiday(current_time, symbol),
            self._is_outside_buffer_periods(current_time, hours_config),
            not self._is_avoid_period(current_time, hours_config)
        ]

        return all(checks)

    def _get_trading_hours_config(self, symbol: str) -> Optional[Dict]:
        """Get trading hours configuration for symbol"""
        asset_class = self.pip_calculator.get_asset_class(symbol)

        if asset_class not in self.config['asset_trading_hours']:
            return None

        asset_config = self.config['asset_trading_hours'][asset_class]

        # Check for symbol-specific configuration
        if symbol in asset_config:
            return asset_config[symbol]

        # Check for inheritance
        if 'inherits' in asset_config:
            parent_config = self.config['asset_trading_hours'][asset_config['inherits']]
            # Merge parent with current config
            merged_config = {**parent_config, **asset_config}
            merged_config.pop('inherits', None)
            return merged_config

        return asset_config

    def get_current_session(self, symbol: str, current_time: Optional[datetime] = None) -> Optional[str]:
        """Get current trading session for symbol"""
        if current_time is None:
            current_time = datetime.now(self.server_tz)

        hours_config = self._get_trading_hours_config(symbol)
        if not hours_config or 'sessions' not in hours_config:
            return None

        current_time_str = current_time.strftime('%H:%M')

        for session_name, session_config in hours_config['sessions'].items():
            start_time = session_config['start']
            end_time = session_config['end']

            # Handle overnight sessions
            if start_time <= end_time:
                if start_time <= current_time_str <= end_time:
                    return session_name
            else:
                if current_time_str >= start_time or current_time_str <= end_time:
                    return session_name

        return None

    def get_session_activity_level(self, symbol: str, current_time: Optional[datetime] = None) -> str:
        """Get activity level for current session"""
        session = self.get_current_session(symbol, current_time)
        if not session:
            return "closed"

        hours_config = self._get_trading_hours_config(symbol)
        session_config = hours_config['sessions'][session]

        return session_config.get('activity', 'medium')

    def get_next_high_activity_session(self, symbol: str) -> Optional[Dict]:
        """Get next high activity trading session"""
        hours_config = self._get_trading_hours_config(symbol)
        if not hours_config or 'sessions' not in hours_config:
            return None

        current_time = datetime.now(self.server_tz)

        # Find next high activity session
        for session_name, session_config in hours_config['sessions'].items():
            if session_config.get('activity') == 'high':
                session_start = self._calculate_next_session_time(
                    session_config['start'], current_time
                )

                return {
                    'name': session_name,
                    'start_time': session_start,
                    'description': session_config.get('description', ''),
                    'activity': session_config['activity']
                }

        return None

    def should_avoid_trading(self, symbol: str, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """Check if trading should be avoided with reason"""
        if current_time is None:
            current_time = datetime.now(self.server_tz)

        hours_config = self._get_trading_hours_config(symbol)

        # Check for avoid periods
        if self._is_avoid_period(current_time, hours_config):
            return True, "Low liquidity period"

        # Check for low activity sessions
        session_activity = self.get_session_activity_level(symbol, current_time)
        if session_activity == "low":
            return True, f"Low activity session: {self.get_current_session(symbol, current_time)}"

        # Check for major economic events (if configured)
        if self._is_major_event_time(symbol, current_time):
            return True, "Major economic event scheduled"

        return False, ""

    def get_trading_summary(self, symbol: str) -> Dict:
        """Get comprehensive trading status summary"""
        current_time = datetime.now(self.server_tz)

        return {
            'symbol': symbol,
            'asset_class': self.pip_calculator.get_asset_class(symbol),
            'trading_allowed': self.is_trading_allowed(symbol, current_time),
            'current_session': self.get_current_session(symbol, current_time),
            'activity_level': self.get_session_activity_level(symbol, current_time),
            'should_avoid': self.should_avoid_trading(symbol, current_time),
            'next_high_activity': self.get_next_high_activity_session(symbol),
            'time_checked': current_time.isoformat()
        }
```

## Risk Management by Asset Class

### Asset-Specific Risk Rules

```python
class AssetRiskManager:
    """
    Risk management with asset-specific rules and correlations
    """

    def __init__(self, config):
        self.config = config
        self.pip_calculator = AssetPipCalculator()

        # Asset correlation matrix
        self.correlation_matrix = {
            "forex_major": {
                "EURUSD": {"GBPUSD": 0.75, "USDCHF": -0.85, "AUDUSD": 0.65},
                "GBPUSD": {"EURUSD": 0.75, "USDCHF": -0.70, "AUDUSD": 0.60},
                "USDCHF": {"EURUSD": -0.85, "GBPUSD": -0.70, "USDJPY": 0.50}
            },
            "commodities": {
                "XAUUSD": {"XAGUSD": 0.80, "XBRUSD": 0.30},
                "XAGUSD": {"XAUUSD": 0.80, "XBRUSD": 0.25}
            },
            "crypto": {
                "BTCUSD": {"ETHUSD": 0.70, "ADAUSD": 0.60},
                "ETHUSD": {"BTCUSD": 0.70, "ADAUSD": 0.75}
            }
        }

    async def validate_asset_risk(self, symbol: str, proposed_position: Dict) -> RiskValidationResult:
        """Validate risk for specific asset class"""
        asset_class = self.pip_calculator.get_asset_class(symbol)

        # Get asset-specific risk limits
        asset_config = await self._get_asset_risk_config(asset_class)

        # Validate position size
        size_validation = await self._validate_position_size(symbol, proposed_position, asset_config)
        if not size_validation.is_valid:
            return size_validation

        # Validate correlation risk
        correlation_validation = await self._validate_correlation_risk(symbol, proposed_position)
        if not correlation_validation.is_valid:
            return correlation_validation

        # Validate asset class exposure
        exposure_validation = await self._validate_asset_exposure(asset_class, proposed_position)

        return exposure_validation

    async def _get_asset_risk_config(self, asset_class: str) -> Dict:
        """Get risk configuration for asset class"""
        risk_configs = {
            "forex_major": {
                "max_risk_per_trade": 0.005,
                "max_positions": 5,
                "max_class_exposure": 0.15,
                "correlation_limit": 0.70
            },
            "forex_jpy": {
                "max_risk_per_trade": 0.004,  # Lower due to volatility
                "max_positions": 4,
                "max_class_exposure": 0.12,
                "correlation_limit": 0.65
            },
            "commodities": {
                "max_risk_per_trade": 0.003,
                "max_positions": 3,
                "max_class_exposure": 0.10,
                "correlation_limit": 0.60
            },
            "crypto": {
                "max_risk_per_trade": 0.002,  # Highest volatility
                "max_positions": 2,
                "max_class_exposure": 0.08,
                "correlation_limit": 0.50
            },
            "indices": {
                "max_risk_per_trade": 0.004,
                "max_positions": 3,
                "max_class_exposure": 0.12,
                "correlation_limit": 0.75
            }
        }

        return risk_configs.get(asset_class, risk_configs["forex_major"])

    async def calculate_asset_class_exposure(self, asset_class: str) -> float:
        """Calculate current exposure for asset class"""
        active_positions = await self.get_active_positions()

        total_exposure = 0.0
        account_balance = await self.get_account_balance()

        for position in active_positions:
            if self.pip_calculator.get_asset_class(position.symbol) == asset_class:
                position_value = position.volume * position.current_price
                total_exposure += position_value

        return total_exposure / account_balance

    async def get_correlation_risk(self, symbol1: str, symbol2: str) -> float:
        """Get correlation risk between two symbols"""
        asset_class1 = self.pip_calculator.get_asset_class(symbol1)
        asset_class2 = self.pip_calculator.get_asset_class(symbol2)

        # Different asset classes have lower correlation
        if asset_class1 != asset_class2:
            base_correlation = 0.20  # Base cross-asset correlation
        else:
            # Same asset class - check correlation matrix
            if asset_class1 in self.correlation_matrix:
                correlations = self.correlation_matrix[asset_class1]
                if symbol1 in correlations and symbol2 in correlations[symbol1]:
                    base_correlation = abs(correlations[symbol1][symbol2])
                else:
                    base_correlation = 0.40  # Default same-class correlation
            else:
                base_correlation = 0.30

        return base_correlation
```

This comprehensive asset configuration guide provides all the necessary information for proper asset-specific trading rules, pip calculations, position management, and risk controls across different asset classes.
