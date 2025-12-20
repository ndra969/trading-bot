# Code Examples and Implementation Patterns

This guide provides comprehensive code examples, implementation patterns, and best practices for developing and extending the trading bot system.

## Core Implementation Patterns

### 1. Pip Calculation Functions

Critical functions for position sizing and profit calculations across different asset classes.

```python
# src/trading_bot/utils/pip_calculator.py
from typing import Dict, Optional
from enum import Enum

class AssetClass(Enum):
    FOREX_MAJOR = "forex_major"
    FOREX_JPY = "forex_jpy"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    INDICES = "indices"

class PipCalculator:
    """
    Centralized pip calculation system with asset-specific rules
    """

    # Critical pip values - DO NOT MODIFY without understanding impact
    PIP_VALUES = {
        AssetClass.FOREX_MAJOR: 0.0001,
        AssetClass.FOREX_JPY: 0.01,
        AssetClass.COMMODITIES: {
            "XAUUSD": 0.1,     # Gold
            "XAGUSD": 0.001,   # Silver
            "XBRUSD": 0.01,    # Brent Oil
            "XTIUSD": 0.01     # WTI Oil
        },
        AssetClass.CRYPTO: {
            "BTCUSD": 1.0,     # Bitcoin
            "ETHUSD": 0.1,     # Ethereum
            "ADAUSD": 0.0001,  # Cardano
            "DOTUSD": 0.001    # Polkadot
        },
        AssetClass.INDICES: {
            "US30": 1.0,       # Dow Jones
            "SPX500": 0.1,     # S&P 500
            "NAS100": 0.1,     # Nasdaq
            "GER40": 0.1,      # DAX
            "UK100": 0.1       # FTSE
        }
    }

    # Symbol to asset class mapping
    SYMBOL_MAPPING = {
        # Forex Major
        "EURUSD": AssetClass.FOREX_MAJOR,
        "GBPUSD": AssetClass.FOREX_MAJOR,
        "USDCHF": AssetClass.FOREX_MAJOR,
        "USDCAD": AssetClass.FOREX_MAJOR,
        "AUDUSD": AssetClass.FOREX_MAJOR,
        "NZDUSD": AssetClass.FOREX_MAJOR,

        # Forex JPY
        "USDJPY": AssetClass.FOREX_JPY,
        "EURJPY": AssetClass.FOREX_JPY,
        "GBPJPY": AssetClass.FOREX_JPY,
        "AUDJPY": AssetClass.FOREX_JPY,

        # Commodities
        "XAUUSD": AssetClass.COMMODITIES,
        "XAGUSD": AssetClass.COMMODITIES,
        "XBRUSD": AssetClass.COMMODITIES,
        "XTIUSD": AssetClass.COMMODITIES,

        # Crypto
        "BTCUSD": AssetClass.CRYPTO,
        "ETHUSD": AssetClass.CRYPTO,
        "ADAUSD": AssetClass.CRYPTO,
        "DOTUSD": AssetClass.CRYPTO,

        # Indices
        "US30": AssetClass.INDICES,
        "SPX500": AssetClass.INDICES,
        "NAS100": AssetClass.INDICES,
        "GER40": AssetClass.INDICES,
        "UK100": AssetClass.INDICES
    }

    @classmethod
    def get_asset_class(cls, symbol: str) -> Optional[AssetClass]:
        """Get asset class for symbol"""
        return cls.SYMBOL_MAPPING.get(symbol)

    @classmethod
    def get_pip_value(cls, symbol: str) -> float:
        """
        Get pip value for specific symbol

        CRITICAL: This function directly affects position sizing and profit calculations
        """
        asset_class = cls.get_asset_class(symbol)
        if not asset_class:
            raise ValueError(f"Unknown symbol: {symbol}")

        pip_config = cls.PIP_VALUES[asset_class]

        # Handle simple pip values (forex major/jpy)
        if isinstance(pip_config, (int, float)):
            return float(pip_config)

        # Handle symbol-specific pip values (commodities, crypto, indices)
        if isinstance(pip_config, dict):
            if symbol in pip_config:
                return float(pip_config[symbol])
            else:
                raise ValueError(f"No pip value configured for {symbol}")

        raise ValueError(f"Invalid pip configuration for {asset_class}")

    @classmethod
    def calculate_profit_pips(cls, symbol: str, entry_price: float,
                            current_price: float, direction: str) -> float:
        """
        Calculate profit/loss in pips

        Args:
            symbol: Trading symbol
            entry_price: Position entry price
            current_price: Current market price
            direction: "BUY" or "SELL"

        Returns:
            Profit in pips (positive = profit, negative = loss)
        """
        pip_value = cls.get_pip_value(symbol)

        if direction.upper() == "BUY":
            price_diff = current_price - entry_price
        else:  # SELL
            price_diff = entry_price - current_price

        return price_diff / pip_value

    @classmethod
    def calculate_distance_pips(cls, symbol: str, price1: float, price2: float) -> float:
        """Calculate distance between two prices in pips"""
        pip_value = cls.get_pip_value(symbol)
        return abs(price1 - price2) / pip_value

    @classmethod
    def calculate_price_from_pips(cls, symbol: str, base_price: float,
                                pips: float, direction: str = "up") -> float:
        """
        Calculate price level from base price + pips

        Args:
            symbol: Trading symbol
            base_price: Base price level
            pips: Number of pips to add/subtract
            direction: "up" or "down"

        Returns:
            Calculated price level
        """
        pip_value = cls.get_pip_value(symbol)
        price_change = pips * pip_value

        if direction.lower() == "up":
            return base_price + price_change
        else:
            return base_price - price_change

    @classmethod
    def validate_pip_calculation(cls, symbol: str, expected_pips: float,
                                price1: float, price2: float,
                                tolerance: float = 0.1) -> bool:
        """
        Validate pip calculation for testing purposes

        Args:
            symbol: Trading symbol
            expected_pips: Expected pip difference
            price1: First price
            price2: Second price
            tolerance: Allowed tolerance in pips

        Returns:
            True if calculation is within tolerance
        """
        calculated_pips = cls.calculate_distance_pips(symbol, price1, price2)
        return abs(calculated_pips - expected_pips) <= tolerance

# Usage examples
if __name__ == "__main__":
    # Example 1: Calculate profit for EURUSD trade
    symbol = "EURUSD"
    entry_price = 1.0850
    current_price = 1.0870
    direction = "BUY"

    profit_pips = PipCalculator.calculate_profit_pips(symbol, entry_price, current_price, direction)
    print(f"EURUSD BUY trade profit: {profit_pips} pips")  # Expected: 20.0 pips

    # Example 2: Calculate stop loss level
    sl_pips = 15
    sl_price = PipCalculator.calculate_price_from_pips(symbol, entry_price, sl_pips, "down")
    print(f"Stop loss at {sl_pips} pips: {sl_price}")  # Expected: 1.0835

    # Example 3: Gold (XAUUSD) calculation
    gold_entry = 2000.5
    gold_current = 2010.5
    gold_profit = PipCalculator.calculate_profit_pips("XAUUSD", gold_entry, gold_current, "BUY")
    print(f"XAUUSD profit: {gold_profit} pips")  # Expected: 100.0 pips

    # Example 4: Validation
    is_valid = PipCalculator.validate_pip_calculation("EURUSD", 20.0, 1.0850, 1.0870)
    print(f"Validation result: {is_valid}")  # Expected: True
```

### 2. Position Management Implementation

Comprehensive position management with asset-specific rules and lifecycle handling.

```python
# src/trading_bot/position/position_manager.py
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

class PositionStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BREAKEVEN = "breakeven"
    TRAILING = "trailing"
    PARTIAL_CLOSED = "partial_closed"
    CLOSED = "closed"
    FAILED = "failed"

class PositionEvent(Enum):
    OPENED = "opened"
    BREAKEVEN_TRIGGERED = "breakeven_triggered"
    TRAILING_ACTIVATED = "trailing_activated"
    PARTIAL_CLOSE = "partial_close"
    STOP_HIT = "stop_hit"
    TARGET_HIT = "target_hit"
    MANUAL_CLOSE = "manual_close"

@dataclass
class PositionConfig:
    """Asset-specific position management configuration"""
    symbol: str
    asset_class: str
    pip_value: float

    # Breakeven settings
    breakeven_trigger_pips: float
    breakeven_buffer_pips: float
    breakeven_enabled: bool = True

    # Trailing settings
    trailing_start_pips: float
    trailing_distance_pips: float
    trailing_acceleration: float = 1.0
    trailing_max_distance: float = 100.0

    # Partial close settings
    partial_close_levels: List[float] = None
    partial_close_percentages: List[float] = None
    partial_close_enabled: bool = True

    # Risk settings
    max_risk_per_trade: float = 0.005
    min_volume: float = 0.01
    max_volume: float = 10.0

class AdvancedPositionManager:
    """
    Advanced position manager with asset-specific rules and lifecycle management
    """

    def __init__(self, mt5_connector, database: AsyncSession, config_manager, event_bus):
        self.mt5 = mt5_connector
        self.db = database
        self.config = config_manager
        self.event_bus = event_bus

        # Active positions tracking
        self.active_positions: Dict[int, Position] = {}

        # Position monitoring task
        self.monitoring_task = None
        self.is_monitoring = False

    async def initialize(self):
        """Initialize position manager"""
        # Load active positions from database
        await self._load_active_positions()

        # Start position monitoring
        await self._start_monitoring()

    async def _load_active_positions(self):
        """Load active positions from database"""
        from sqlalchemy import select

        result = await self.db.execute(
            select(Position).where(Position.status.in_(['active', 'breakeven', 'trailing', 'partial_closed']))
        )

        positions = result.scalars().all()

        for position in positions:
            self.active_positions[position.ticket] = position

        self.logger.info(f"Loaded {len(positions)} active positions")

    async def open_position(self, signal: TradingSignal) -> Tuple[bool, Optional[Position]]:
        """
        Open new position with comprehensive validation and setup
        """
        try:
            # 1. Get asset-specific configuration
            position_config = await self._get_position_config(signal.symbol)

            # 2. Calculate position size
            position_size = await self._calculate_position_size(signal, position_config)

            if position_size < position_config.min_volume:
                self.logger.warning(f"Position size {position_size} below minimum {position_config.min_volume}")
                return False, None

            # 3. Validate position limits
            if not await self._validate_position_limits(signal.symbol, position_size):
                self.logger.warning(f"Position limits exceeded for {signal.symbol}")
                return False, None

            # 4. Execute trade through MT5
            order_result = await self.mt5.place_order({
                'symbol': signal.symbol,
                'direction': signal.direction,
                'volume': position_size,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'magic_number': signal.magic_number,
                'comment': f"Bot_{signal.strategy_name}"
            })

            if not order_result['success']:
                self.logger.error(f"Failed to open position: {order_result.get('error')}")
                return False, None

            # 5. Create position object
            position = Position(
                ticket=order_result['ticket'],
                symbol=signal.symbol,
                direction=signal.direction,
                volume=position_size,
                entry_price=order_result['price'],
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                strategy_name=signal.strategy_name,
                confidence_score=signal.confidence,
                status=PositionStatus.ACTIVE,
                opened_at=datetime.utcnow(),
                config=position_config
            )

            # 6. Save to database
            self.db.add(position)
            await self.db.commit()

            # 7. Add to active positions
            self.active_positions[position.ticket] = position

            # 8. Setup position monitoring
            await self._setup_position_monitoring(position)

            # 9. Publish event
            await self.event_bus.publish(Event(
                event_type=EventType.TRADE_OPENED,
                data=position.to_dict(),
                source='position_manager'
            ))

            self.logger.info(f"Opened position {position.ticket}: {signal.symbol} {signal.direction}")
            return True, position

        except Exception as e:
            self.logger.error(f"Error opening position: {e}")
            return False, None

    async def _calculate_position_size(self, signal: TradingSignal, config: PositionConfig) -> float:
        """
        Calculate position size based on risk management rules
        """
        # Get account balance
        account_info = await self.mt5.get_account_info()
        account_balance = account_info['balance']

        # Calculate risk amount
        risk_amount = account_balance * config.max_risk_per_trade

        # Calculate stop loss distance in pips
        sl_distance_pips = PipCalculator.calculate_distance_pips(
            signal.symbol, signal.entry_price, signal.stop_loss
        )

        # Calculate monetary value per pip for 1 lot
        pip_value_per_lot = self._calculate_pip_value_per_lot(signal.symbol)

        # Calculate position size
        position_size = risk_amount / (sl_distance_pips * pip_value_per_lot)

        # Apply volume limits
        position_size = max(config.min_volume, min(position_size, config.max_volume))

        # Round to broker's volume step (usually 0.01)
        volume_step = 0.01
        position_size = round(position_size / volume_step) * volume_step

        return position_size

    async def _setup_position_monitoring(self, position: Position):
        """Setup monitoring for position events"""
        if position.config.breakeven_enabled:
            await self._monitor_breakeven(position)

    async def _monitor_breakeven(self, position: Position):
        """Monitor position for breakeven trigger"""
        while position.status in [PositionStatus.ACTIVE] and position.ticket in self.active_positions:
            try:
                # Get current price
                current_price = await self.mt5.get_current_price(position.symbol)

                # Calculate current profit in pips
                profit_pips = PipCalculator.calculate_profit_pips(
                    position.symbol, position.entry_price, current_price, position.direction
                )

                # Check breakeven trigger
                if profit_pips >= position.config.breakeven_trigger_pips:
                    await self._trigger_breakeven(position)
                    break

                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                self.logger.error(f"Error monitoring breakeven for {position.ticket}: {e}")
                await asyncio.sleep(30)  # Wait longer on error

    async def _trigger_breakeven(self, position: Position):
        """Trigger breakeven for position"""
        try:
            # Calculate breakeven price
            breakeven_price = PipCalculator.calculate_price_from_pips(
                position.symbol,
                position.entry_price,
                position.config.breakeven_buffer_pips,
                "up" if position.direction == "BUY" else "down"
            )

            # Modify stop loss to breakeven
            modify_result = await self.mt5.modify_position(
                position.ticket,
                stop_loss=breakeven_price
            )

            if modify_result['success']:
                # Update position
                position.stop_loss = breakeven_price
                position.status = PositionStatus.BREAKEVEN
                position.breakeven_triggered_at = datetime.utcnow()

                await self.db.commit()

                # Start trailing monitoring if configured
                if position.config.trailing_start_pips > 0:
                    await self._monitor_trailing(position)

                # Publish event
                await self.event_bus.publish(Event(
                    event_type=EventType.BREAKEVEN_TRIGGERED,
                    data={
                        'ticket': position.ticket,
                        'symbol': position.symbol,
                        'breakeven_price': breakeven_price,
                        'profit_pips': PipCalculator.calculate_profit_pips(
                            position.symbol, position.entry_price,
                            await self.mt5.get_current_price(position.symbol),
                            position.direction
                        )
                    },
                    source='position_manager'
                ))

                self.logger.info(f"Breakeven triggered for {position.ticket} at {breakeven_price}")
            else:
                self.logger.error(f"Failed to modify stop loss for breakeven: {modify_result.get('error')}")

        except Exception as e:
            self.logger.error(f"Error triggering breakeven for {position.ticket}: {e}")

    async def _monitor_trailing(self, position: Position):
        """Monitor position for trailing stop updates"""
        last_trailing_price = position.stop_loss

        while (position.status in [PositionStatus.BREAKEVEN, PositionStatus.TRAILING] and
               position.ticket in self.active_positions):
            try:
                # Get current price
                current_price = await self.mt5.get_current_price(position.symbol)

                # Calculate current profit in pips
                profit_pips = PipCalculator.calculate_profit_pips(
                    position.symbol, position.entry_price, current_price, position.direction
                )

                # Check if we should start trailing
                if (position.status == PositionStatus.BREAKEVEN and
                    profit_pips >= position.config.trailing_start_pips):

                    position.status = PositionStatus.TRAILING
                    position.trailing_activated_at = datetime.utcnow()
                    await self.db.commit()

                    # Publish trailing activated event
                    await self.event_bus.publish(Event(
                        event_type=EventType.TRAILING_ACTIVATED,
                        data={'ticket': position.ticket, 'symbol': position.symbol},
                        source='position_manager'
                    ))

                # Update trailing stop if position is trailing
                if position.status == PositionStatus.TRAILING:
                    new_trailing_price = self._calculate_trailing_stop(position, current_price)

                    # Only update if new trailing stop is better
                    if self._is_trailing_stop_better(position, new_trailing_price, last_trailing_price):
                        modify_result = await self.mt5.modify_position(
                            position.ticket,
                            stop_loss=new_trailing_price
                        )

                        if modify_result['success']:
                            position.stop_loss = new_trailing_price
                            last_trailing_price = new_trailing_price
                            await self.db.commit()

                            self.logger.debug(f"Updated trailing stop for {position.ticket}: {new_trailing_price}")

                await asyncio.sleep(5)  # Check every 5 seconds for trailing

            except Exception as e:
                self.logger.error(f"Error monitoring trailing for {position.ticket}: {e}")
                await asyncio.sleep(30)

    def _calculate_trailing_stop(self, position: Position, current_price: float) -> float:
        """Calculate new trailing stop price"""
        distance_pips = position.config.trailing_distance_pips

        # Apply acceleration if configured
        if position.config.trailing_acceleration > 1.0:
            profit_pips = PipCalculator.calculate_profit_pips(
                position.symbol, position.entry_price, current_price, position.direction
            )
            # Reduce distance as profit increases
            acceleration_factor = min(position.config.trailing_acceleration,
                                    1.0 + (profit_pips / 100.0) * 0.1)
            distance_pips = distance_pips / acceleration_factor

        # Apply maximum distance limit
        distance_pips = min(distance_pips, position.config.trailing_max_distance)

        # Calculate trailing stop price
        if position.direction == "BUY":
            return current_price - (distance_pips * PipCalculator.get_pip_value(position.symbol))
        else:
            return current_price + (distance_pips * PipCalculator.get_pip_value(position.symbol))

    def _is_trailing_stop_better(self, position: Position, new_price: float, old_price: float) -> bool:
        """Check if new trailing stop is better than old one"""
        if position.direction == "BUY":
            return new_price > old_price  # Higher is better for BUY
        else:
            return new_price < old_price  # Lower is better for SELL

    async def close_position(self, ticket: int, reason: str = "manual") -> bool:
        """Close position manually"""
        if ticket not in self.active_positions:
            self.logger.warning(f"Position {ticket} not found in active positions")
            return False

        position = self.active_positions[ticket]

        try:
            # Close position through MT5
            close_result = await self.mt5.close_position(ticket)

            if close_result['success']:
                # Update position
                position.status = PositionStatus.CLOSED
                position.closed_at = datetime.utcnow()
                position.close_price = close_result['close_price']
                position.profit = close_result['profit']
                position.close_reason = reason

                await self.db.commit()

                # Remove from active positions
                del self.active_positions[ticket]

                # Publish event
                await self.event_bus.publish(Event(
                    event_type=EventType.TRADE_CLOSED,
                    data=position.to_dict(),
                    source='position_manager'
                ))

                self.logger.info(f"Closed position {ticket}: {position.symbol} profit: {position.profit}")
                return True
            else:
                self.logger.error(f"Failed to close position {ticket}: {close_result.get('error')}")
                return False

        except Exception as e:
            self.logger.error(f"Error closing position {ticket}: {e}")
            return False

    async def get_position_summary(self, ticket: int) -> Optional[Dict]:
        """Get comprehensive position summary"""
        if ticket not in self.active_positions:
            return None

        position = self.active_positions[ticket]

        try:
            current_price = await self.mt5.get_current_price(position.symbol)

            profit_pips = PipCalculator.calculate_profit_pips(
                position.symbol, position.entry_price, current_price, position.direction
            )

            # Calculate unrealized profit
            unrealized_profit = profit_pips * self._calculate_pip_value_per_lot(position.symbol) * position.volume

            return {
                'ticket': position.ticket,
                'symbol': position.symbol,
                'direction': position.direction,
                'volume': position.volume,
                'entry_price': position.entry_price,
                'current_price': current_price,
                'stop_loss': position.stop_loss,
                'take_profit': position.take_profit,
                'profit_pips': profit_pips,
                'unrealized_profit': unrealized_profit,
                'status': position.status.value,
                'strategy': position.strategy_name,
                'confidence': position.confidence_score,
                'opened_at': position.opened_at,
                'duration': datetime.utcnow() - position.opened_at,
                'breakeven_triggered': position.breakeven_triggered_at is not None,
                'trailing_active': position.status == PositionStatus.TRAILING
            }

        except Exception as e:
            self.logger.error(f"Error getting position summary for {ticket}: {e}")
            return None

    async def _start_monitoring(self):
        """Start position monitoring task"""
        if self.monitoring_task is None or self.monitoring_task.done():
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def _monitoring_loop(self):
        """Main monitoring loop for all positions"""
        while self.is_monitoring:
            try:
                # Monitor all active positions
                for ticket, position in list(self.active_positions.items()):
                    await self._check_position_status(position)

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)

    async def cleanup(self):
        """Cleanup position manager"""
        self.is_monitoring = False

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
```

### 3. Market Hours Validation

Complete implementation for market hours validation across different asset classes.

```python
# src/trading_bot/utils/market_hours.py
from datetime import datetime, time, timedelta
import pytz
from typing import Dict, List, Optional, Tuple
import yaml
from enum import Enum

class MarketSession(Enum):
    SYDNEY = "sydney"
    TOKYO = "tokyo"
    LONDON = "london"
    NEW_YORK = "new_york"
    CLOSED = "closed"

class MarketHoursValidator:
    """
    Comprehensive market hours validation for all asset classes
    """

    def __init__(self, config_path: str = "config/market_hours.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Server timezone (MT5 usually uses GMT/UTC)
        self.server_tz = pytz.UTC

        # Trading holidays by year
        self.holidays = self._load_holidays()

        # Asset class mapping
        self.asset_mapping = self.config.get('asset_class_mapping', {})

    def _load_holidays(self) -> Dict[int, List[datetime]]:
        """Load trading holidays"""
        return {
            2024: [
                datetime(2024, 1, 1),   # New Year
                datetime(2024, 3, 29),  # Good Friday
                datetime(2024, 4, 1),   # Easter Monday
                datetime(2024, 5, 27),  # Spring Bank Holiday
                datetime(2024, 8, 26),  # Summer Bank Holiday
                datetime(2024, 12, 25), # Christmas
                datetime(2024, 12, 26), # Boxing Day
            ],
            2025: [
                datetime(2025, 1, 1),   # New Year
                datetime(2025, 4, 18),  # Good Friday
                datetime(2025, 4, 21),  # Easter Monday
                datetime(2025, 5, 26),  # Spring Bank Holiday
                datetime(2025, 8, 25),  # Summer Bank Holiday
                datetime(2025, 12, 25), # Christmas
                datetime(2025, 12, 26), # Boxing Day
            ]
        }

    def is_trading_allowed(self, symbol: str, current_time: Optional[datetime] = None) -> bool:
        """
        Comprehensive check if trading is allowed for symbol
        """
        if current_time is None:
            current_time = datetime.now(self.server_tz)

        # Get asset class
        asset_class = self.get_asset_class(symbol)
        if not asset_class:
            return False

        # Get market configuration
        market_config = self.config['asset_trading_hours'].get(asset_class)
        if not market_config:
            return False

        # Handle symbol-specific overrides
        if symbol in market_config:
            market_config = market_config[symbol]
        elif 'inherits' in market_config:
            parent_config = self.config['asset_trading_hours'][market_config['inherits']]
            market_config = {**parent_config, **market_config}
            market_config.pop('inherits', None)

        # Run all validation checks
        validation_results = [
            self._is_trading_day(current_time, market_config),
            self._is_within_trading_hours(current_time, market_config),
            not self._is_holiday(current_time),
            self._is_outside_buffer_periods(current_time, market_config),
            not self._is_avoid_period(current_time, market_config)
        ]

        return all(validation_results)

    def get_asset_class(self, symbol: str) -> Optional[str]:
        """Get asset class for symbol"""
        return self.asset_mapping.get(symbol)

    def _is_trading_day(self, dt: datetime, market_config: Dict) -> bool:
        """Check if current day is a trading day"""
        weekday_name = dt.strftime('%A').lower()

        trading_days = market_config.get('trading_days', [])
        excluded_days = market_config.get('excluded_days', [])

        return weekday_name in trading_days and weekday_name not in excluded_days

    def _is_within_trading_hours(self, dt: datetime, market_config: Dict) -> bool:
        """Check if current time is within trading hours"""
        start_time = market_config.get('start_time')
        end_time = market_config.get('end_time')

        if not start_time or not end_time:
            return True  # 24/7 trading

        current_time_str = dt.strftime('%H:%M')

        # Handle overnight sessions (e.g., Forex Sunday evening to Friday evening)
        if start_time <= end_time:
            # Normal day session
            return start_time <= current_time_str <= end_time
        else:
            # Overnight session (crosses midnight)
            return current_time_str >= start_time or current_time_str <= end_time

    def _is_holiday(self, dt: datetime) -> bool:
        """Check if current date is a trading holiday"""
        year = dt.year
        if year not in self.holidays:
            return False

        date_only = dt.date()
        holiday_dates = [h.date() for h in self.holidays[year]]
        return date_only in holiday_dates

    def _is_outside_buffer_periods(self, dt: datetime, market_config: Dict) -> bool:
        """Check if current time is outside buffer periods"""
        buffer_before_close = market_config.get('buffer_before_close', 0)
        buffer_after_open = market_config.get('buffer_after_open', 0)

        if buffer_before_close == 0 and buffer_after_open == 0:
            return True

        # Get trading hours
        start_time_str = market_config.get('start_time')
        end_time_str = market_config.get('end_time')

        if not start_time_str or not end_time_str:
            return True

        # Parse times
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()

        # Combine with current date
        current_date = dt.date()
        market_open = datetime.combine(current_date, start_time).replace(tzinfo=self.server_tz)
        market_close = datetime.combine(current_date, end_time).replace(tzinfo=self.server_tz)

        # Handle overnight sessions
        if start_time > end_time:
            if dt.time() >= start_time:
                # Current time is in today's session that started yesterday
                market_close += timedelta(days=1)
            else:
                # Current time is in yesterday's session that continues today
                market_open -= timedelta(days=1)

        # Calculate buffer times
        buffer_start = market_open + timedelta(minutes=buffer_after_open)
        buffer_end = market_close - timedelta(minutes=buffer_before_close)

        return buffer_start <= dt <= buffer_end

    def _is_avoid_period(self, dt: datetime, market_config: Dict) -> bool:
        """Check if current time is in an avoid period"""
        avoid_periods = market_config.get('avoid_periods', [])

        for period in avoid_periods:
            if self._is_in_avoid_period(dt, period):
                return True

        return False

    def _is_in_avoid_period(self, dt: datetime, period: Dict) -> bool:
        """Check if datetime is within specific avoid period"""
        period_type = period.get('type', 'date_range')

        if period_type == 'date_range':
            start_date = period.get('start_date')
            end_date = period.get('end_date')

            if start_date and end_date:
                # Handle MM-DD format
                if '-' in start_date and len(start_date) == 5:
                    start_month, start_day = map(int, start_date.split('-'))
                    end_month, end_day = map(int, end_date.split('-'))

                    current_month_day = (dt.month, dt.day)
                    start_month_day = (start_month, start_day)
                    end_month_day = (end_month, end_day)

                    # Handle year-crossing periods (e.g., Christmas to New Year)
                    if start_month_day <= end_month_day:
                        return start_month_day <= current_month_day <= end_month_day
                    else:
                        return current_month_day >= start_month_day or current_month_day <= end_month_day

        return False

    def get_current_session(self, symbol: str, current_time: Optional[datetime] = None) -> MarketSession:
        """Get current trading session for symbol"""
        if current_time is None:
            current_time = datetime.now(self.server_tz)

        asset_class = self.get_asset_class(symbol)
        if not asset_class:
            return MarketSession.CLOSED

        # Forex sessions (24/5 trading)
        if asset_class in ['forex_major', 'forex_jpy']:
            return self._get_forex_session(current_time)

        # Other assets follow their specific schedules
        if not self.is_trading_allowed(symbol, current_time):
            return MarketSession.CLOSED

        # Default to London session for other assets during trading hours
        return MarketSession.LONDON

    def _get_forex_session(self, dt: datetime) -> MarketSession:
        """Get current forex session"""
        current_hour = dt.hour

        # Session times (GMT/UTC)
        sessions = [
            (22, 7, MarketSession.SYDNEY),    # 22:00 - 07:00
            (0, 9, MarketSession.TOKYO),      # 00:00 - 09:00
            (8, 17, MarketSession.LONDON),    # 08:00 - 17:00
            (13, 22, MarketSession.NEW_YORK)  # 13:00 - 22:00
        ]

        # Check which session we're in (sessions can overlap)
        active_sessions = []
        for start, end, session in sessions:
            if start <= end:
                if start <= current_hour < end:
                    active_sessions.append(session)
            else:  # Overnight session
                if current_hour >= start or current_hour < end:
                    active_sessions.append(session)

        # Priority order for overlapping sessions
        session_priority = [
            MarketSession.NEW_YORK,
            MarketSession.LONDON,
            MarketSession.TOKYO,
            MarketSession.SYDNEY
        ]

        for session in session_priority:
            if session in active_sessions:
                return session

        return MarketSession.CLOSED

    def get_session_activity_level(self, symbol: str, current_time: Optional[datetime] = None) -> str:
        """Get activity level for current session"""
        session = self.get_current_session(symbol, current_time)

        if session == MarketSession.CLOSED:
            return "closed"

        # Activity levels by session
        activity_levels = {
            MarketSession.SYDNEY: "low",
            MarketSession.TOKYO: "medium",
            MarketSession.LONDON: "high",
            MarketSession.NEW_YORK: "very_high"
        }

        return activity_levels.get(session, "medium")

    def get_next_trading_session(self, symbol: str) -> Optional[Tuple[datetime, MarketSession]]:
        """Get next trading session start time"""
        current_time = datetime.now(self.server_tz)

        # Check next 7 days
        for days_ahead in range(7):
            check_date = current_time + timedelta(days=days_ahead)

            # Check hourly for the next session
            for hour in range(24):
                check_time = check_date.replace(hour=hour, minute=0, second=0, microsecond=0)

                if check_time <= current_time:
                    continue

                if self.is_trading_allowed(symbol, check_time):
                    session = self.get_current_session(symbol, check_time)
                    if session != MarketSession.CLOSED:
                        return check_time, session

        return None

    def get_trading_status_summary(self, symbol: str) -> Dict:
        """Get comprehensive trading status summary"""
        current_time = datetime.now(self.server_tz)

        is_allowed = self.is_trading_allowed(symbol, current_time)
        current_session = self.get_current_session(symbol, current_time)
        activity_level = self.get_session_activity_level(symbol, current_time)

        summary = {
            'symbol': symbol,
            'asset_class': self.get_asset_class(symbol),
            'current_time': current_time.isoformat(),
            'trading_allowed': is_allowed,
            'current_session': current_session.value,
            'activity_level': activity_level,
            'status_message': self._get_status_message(symbol, is_allowed, current_session)
        }

        # Add next session if market is closed
        if not is_allowed:
            next_session = self.get_next_trading_session(symbol)
            if next_session:
                next_time, next_session_type = next_session
                summary['next_session'] = {
                    'start_time': next_time.isoformat(),
                    'session_type': next_session_type.value
                }

        return summary

    def _get_status_message(self, symbol: str, is_allowed: bool, session: MarketSession) -> str:
        """Get human-readable status message"""
        if is_allowed:
            return f"✅ {symbol}: Trading allowed ({session.value} session)"
        else:
            next_session = self.get_next_trading_session(symbol)
            if next_session:
                next_time, next_session_type = next_session
                return f"🕐 {symbol}: Market closed. Next session: {next_time.strftime('%Y-%m-%d %H:%M %Z')} ({next_session_type.value})"
            else:
                return f"❌ {symbol}: Market closed"

# Usage examples
if __name__ == "__main__":
    validator = MarketHoursValidator()

    # Example 1: Check if EURUSD trading is allowed
    eurusd_allowed = validator.is_trading_allowed("EURUSD")
    print(f"EURUSD trading allowed: {eurusd_allowed}")

    # Example 2: Get current session
    current_session = validator.get_current_session("EURUSD")
    print(f"Current session: {current_session.value}")

    # Example 3: Get comprehensive status
    status = validator.get_trading_status_summary("XAUUSD")
    print(f"XAUUSD status: {status}")

    # Example 4: Check multiple symbols
    symbols = ["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD"]
    for symbol in symbols:
        summary = validator.get_trading_status_summary(symbol)
        print(f"{symbol}: {summary['status_message']}")
```

### 4. Configuration Management

Advanced configuration management with validation and optimization.

```python
# src/trading_bot/config/config_manager.py
import yaml
import hashlib
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

class ConfigurationManager:
    """
    Advanced configuration management with validation, versioning, and optimization
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.current_config = {}
        self.config_hash = ""
        self.validation_rules = self._load_validation_rules()

    async def load_configuration(self, environment: str = "development") -> Dict[str, Any]:
        """
        Load hierarchical configuration based on environment
        """
        config = {}

        # Configuration loading order (lowest to highest priority)
        config_files = [
            "default.yaml",
            f"{environment}.yaml",
            "strategy_parameters.yaml",
            "trading_parameters.yaml",
            "risk_parameters.yaml",
            "windows.yaml"  # if applicable
        ]

        for config_file in config_files:
            file_path = self.config_dir / config_file
            if file_path.exists():
                with open(file_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config = self._deep_merge(config, file_config)

        # Override with environment variables
        config = self._apply_environment_overrides(config)

        # Validate configuration
        validation_result = await self._validate_configuration(config)
        if not validation_result.is_valid:
            raise ValueError(f"Configuration validation failed: {validation_result.errors}")

        # Calculate configuration hash
        self.config_hash = self._calculate_config_hash(config)
        self.current_config = config

        return config

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_environment_overrides(self, config: Dict) -> Dict:
        """Apply environment variable overrides"""
        import os

        # Define environment variable mappings
        env_mappings = {
            'TRADING_BOT_RISK_PER_TRADE': 'trading.risk_per_trade',
            'TRADING_BOT_MAX_POSITIONS': 'trading.max_concurrent_positions',
            'TRADING_BOT_DB_URL': 'database.url',
            'TRADING_BOT_MT5_PATH': 'windows.mt5.installation_paths.0',
            'TELEGRAM_BOT_TOKEN': 'telegram.bot_token',
            'TELEGRAM_CHAT_ID': 'telegram.chat_id'
        }

        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                self._set_nested_value(config, config_path, env_value)

        return config

    def _set_nested_value(self, config: Dict, path: str, value: Any):
        """Set nested configuration value using dot notation"""
        keys = path.split('.')
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Convert string values to appropriate types
        final_key = keys[-1]
        if isinstance(value, str):
            # Try to convert to appropriate type
            if value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif '.' in value and value.replace('.', '').isdigit():
                value = float(value)

        current[final_key] = value

    async def _validate_configuration(self, config: Dict) -> 'ValidationResult':
        """Validate configuration against rules"""
        errors = []
        warnings = []

        for rule_path, rule in self.validation_rules.items():
            try:
                value = self._get_nested_value(config, rule_path)

                # Type validation
                expected_type = rule.get('type')
                if expected_type and not isinstance(value, expected_type):
                    errors.append(f"{rule_path}: Expected {expected_type.__name__}, got {type(value).__name__}")
                    continue

                # Range validation
                min_val = rule.get('min')
                max_val = rule.get('max')

                if min_val is not None and value < min_val:
                    errors.append(f"{rule_path}: Value {value} below minimum {min_val}")

                if max_val is not None and value > max_val:
                    errors.append(f"{rule_path}: Value {value} above maximum {max_val}")

                # Warning thresholds
                warn_min = rule.get('warn_min')
                warn_max = rule.get('warn_max')

                if warn_min is not None and value < warn_min:
                    warnings.append(f"{rule_path}: Value {value} below recommended minimum {warn_min}")

                if warn_max is not None and value > warn_max:
                    warnings.append(f"{rule_path}: Value {value} above recommended maximum {warn_max}")

            except KeyError:
                if rule.get('required', False):
                    errors.append(f"{rule_path}: Required configuration missing")
            except Exception as e:
                errors.append(f"{rule_path}: Validation error - {str(e)}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _get_nested_value(self, config: Dict, path: str) -> Any:
        """Get nested configuration value using dot notation"""
        keys = path.split('.')
        current = config

        for key in keys:
            current = current[key]  # Will raise KeyError if not found

        return current

    def _load_validation_rules(self) -> Dict:
        """Load configuration validation rules"""
        return {
            "trading.risk_per_trade": {
                "type": float,
                "min": 0.001,
                "max": 0.05,
                "warn_min": 0.002,
                "warn_max": 0.02,
                "required": True,
                "description": "Risk per trade as percentage of account"
            },
            "trading.max_concurrent_positions": {
                "type": int,
                "min": 1,
                "max": 20,
                "warn_max": 10,
                "required": True,
                "description": "Maximum concurrent positions"
            },
            "multi_timeframe.minimum_trend_strength": {
                "type": (int, float),
                "min": 1,
                "max": 10,
                "required": True,
                "description": "Minimum trend strength for signal generation"
            },
            "confluence_weights.foundation": {
                "type": float,
                "min": 0.1,
                "max": 1.0,
                "warn_min": 0.3,
                "required": True,
                "description": "Foundation layer weight in confluence calculation"
            },
            "position_management.forex_major.breakeven_trigger_pips": {
                "type": (int, float),
                "min": 5,
                "max": 100,
                "warn_min": 10,
                "warn_max": 50,
                "required": True,
                "description": "Breakeven trigger in pips for forex major pairs"
            }
        }

    def _calculate_config_hash(self, config: Dict) -> str:
        """Calculate MD5 hash of configuration for change tracking"""
        config_json = json.dumps(config, sort_keys=True, default=str)
        return hashlib.md5(config_json.encode()).hexdigest()

    async def backup_configuration(self, version_name: str, database: AsyncSession):
        """Backup current configuration to database"""
        backup_data = {
            'version_name': version_name,
            'config_hash': self.config_hash,
            'config_data': self.current_config,
            'created_at': datetime.utcnow(),
            'environment': self.current_config.get('app', {}).get('environment', 'unknown')
        }

        # Save to database (implement ConfigBackup model)
        from models import ConfigBackup

        backup = ConfigBackup(**backup_data)
        database.add(backup)
        await database.commit()

        return backup.id

    async def optimize_configuration(self, strategy_name: str, database: AsyncSession) -> Dict:
        """
        Analyze performance and suggest configuration optimizations
        """
        # Get recent performance data
        performance_data = await self._get_strategy_performance(strategy_name, database, days=30)

        if not performance_data or performance_data['total_trades'] < 10:
            return {'error': 'Insufficient data for optimization'}

        suggestions = []

        # Risk per trade optimization
        current_risk = self.current_config.get('trading', {}).get('risk_per_trade', 0.005)
        win_rate = performance_data['win_rate']
        profit_factor = performance_data['profit_factor']

        if win_rate > 0.7 and profit_factor > 1.5:
            # High performance - suggest increasing risk
            suggested_risk = min(current_risk * 1.2, 0.01)
            suggestions.append({
                'parameter': 'trading.risk_per_trade',
                'current_value': current_risk,
                'suggested_value': suggested_risk,
                'reason': f'High win rate ({win_rate:.1%}) and profit factor ({profit_factor:.2f}) suggest risk can be increased',
                'impact': 'Potentially higher profits with acceptable risk increase'
            })
        elif win_rate < 0.5 or profit_factor < 1.2:
            # Poor performance - suggest decreasing risk
            suggested_risk = max(current_risk * 0.8, 0.002)
            suggestions.append({
                'parameter': 'trading.risk_per_trade',
                'current_value': current_risk,
                'suggested_value': suggested_risk,
                'reason': f'Low win rate ({win_rate:.1%}) or profit factor ({profit_factor:.2f}) suggest risk reduction',
                'impact': 'Reduced losses during poor performance periods'
            })

        # Confluence threshold optimization
        current_threshold = self.current_config.get('multi_timeframe', {}).get('minimum_trend_strength', 4)
        avg_confluence = performance_data.get('avg_confluence_score', 0)

        if avg_confluence < 60 and win_rate < 0.6:
            # Low confluence scores with poor performance
            suggested_threshold = current_threshold + 1
            suggestions.append({
                'parameter': 'multi_timeframe.minimum_trend_strength',
                'current_value': current_threshold,
                'suggested_value': suggested_threshold,
                'reason': f'Low average confluence ({avg_confluence:.1f}%) with poor win rate suggests higher threshold needed',
                'impact': 'Fewer but higher quality signals'
            })

        return {
            'strategy': strategy_name,
            'analysis_period': '30 days',
            'current_performance': performance_data,
            'suggestions': suggestions,
            'optimization_timestamp': datetime.utcnow().isoformat()
        }

    async def _get_strategy_performance(self, strategy_name: str, database: AsyncSession, days: int) -> Dict:
        """Get strategy performance data for optimization"""
        from sqlalchemy import select, func
        from models import Trade
        from datetime import datetime, timedelta

        from_date = datetime.utcnow() - timedelta(days=days)

        result = await database.execute(
            select(
                func.count(Trade.id).label('total_trades'),
                func.sum(func.case((Trade.profit > 0, 1), else_=0)).label('winning_trades'),
                func.avg(Trade.profit).label('avg_profit'),
                func.sum(Trade.profit).label('total_profit'),
                func.avg(Trade.confidence_score).label('avg_confluence_score')
            ).where(
                Trade.strategy_name == strategy_name,
                Trade.opened_at >= from_date
            )
        )

        stats = result.first()

        if not stats or stats.total_trades == 0:
            return {}

        win_rate = stats.winning_trades / stats.total_trades

        # Calculate profit factor
        winning_trades_profit = await database.execute(
            select(func.sum(Trade.profit)).where(
                Trade.strategy_name == strategy_name,
                Trade.opened_at >= from_date,
                Trade.profit > 0
            )
        )
        losing_trades_profit = await database.execute(
            select(func.sum(Trade.profit)).where(
                Trade.strategy_name == strategy_name,
                Trade.opened_at >= from_date,
                Trade.profit < 0
            )
        )

        gross_profit = winning_trades_profit.scalar() or 0
        gross_loss = abs(losing_trades_profit.scalar() or 0)
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        return {
            'total_trades': stats.total_trades,
            'winning_trades': stats.winning_trades,
            'win_rate': win_rate,
            'avg_profit': float(stats.avg_profit or 0),
            'total_profit': float(stats.total_profit or 0),
            'profit_factor': profit_factor,
            'avg_confluence_score': float(stats.avg_confluence_score or 0)
        }

class ValidationResult:
    """Configuration validation result"""

    def __init__(self, is_valid: bool, errors: List[str], warnings: List[str]):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings

# Usage example
if __name__ == "__main__":
    async def main():
        config_manager = ConfigurationManager()

        # Load configuration
        config = await config_manager.load_configuration("production")

        # Backup configuration
        # backup_id = await config_manager.backup_configuration("before_optimization", database)

        # Optimize configuration
        # optimization_result = await config_manager.optimize_configuration("supply_demand", database)
        # print(json.dumps(optimization_result, indent=2))

        print("Configuration loaded successfully!")
        print(f"Config hash: {config_manager.config_hash}")

    asyncio.run(main())
```

### 5. Error Handling and Logging

Comprehensive error handling and structured logging implementation.

```python
# src/trading_bot/utils/error_handling.py
import traceback
import asyncio
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum
from loguru import logger
import sys

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    MARKET_DATA = "market_data"
    TRADING_EXECUTION = "trading_execution"
    STRATEGY_ANALYSIS = "strategy_analysis"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    SYSTEM = "system"

class TradingBotError(Exception):
    """Base exception for trading bot errors"""

    def __init__(self, message: str, category: ErrorCategory, severity: ErrorSeverity,
                 context: Optional[Dict] = None, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.utcnow()

class MarketDataError(TradingBotError):
    """Market data related errors"""

    def __init__(self, message: str, symbol: str = None, timeframe: str = None, **kwargs):
        context = {'symbol': symbol, 'timeframe': timeframe}
        super().__init__(message, ErrorCategory.MARKET_DATA, ErrorSeverity.MEDIUM, context, **kwargs)

class TradingExecutionError(TradingBotError):
    """Trading execution related errors"""

    def __init__(self, message: str, symbol: str = None, ticket: int = None, **kwargs):
        context = {'symbol': symbol, 'ticket': ticket}
        super().__init__(message, ErrorCategory.TRADING_EXECUTION, ErrorSeverity.HIGH, context, **kwargs)

class ConfigurationError(TradingBotError):
    """Configuration related errors"""

    def __init__(self, message: str, config_path: str = None, **kwargs):
        context = {'config_path': config_path}
        super().__init__(message, ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH, context, **kwargs)

class ErrorHandler:
    """
    Comprehensive error handling and logging system
    """

    def __init__(self, notification_manager=None):
        self.notification_manager = notification_manager
        self.error_callbacks = {}
        self.setup_logging()

    def setup_logging(self):
        """Setup structured logging with loguru"""
        # Remove default logger
        logger.remove()

        # Add console logging with colors
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
            colorize=True
        )

        # Add file logging
        logger.add(
            "logs/trading_bot_{time:YYYY-MM-DD}.log",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation="1 day",
            retention="30 days",
            compression="zip"
        )

        # Add error file logging
        logger.add(
            "logs/errors_{time:YYYY-MM-DD}.log",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
            rotation="1 day",
            retention="90 days"
        )

    def register_error_callback(self, error_category: ErrorCategory, callback: Callable):
        """Register callback for specific error category"""
        if error_category not in self.error_callbacks:
            self.error_callbacks[error_category] = []
        self.error_callbacks[error_category].append(callback)

    async def handle_error(self, error: Exception, context: Optional[Dict] = None) -> bool:
        """
        Handle error with comprehensive logging and notification

        Returns:
            bool: True if error was handled successfully, False otherwise
        """
        try:
            # Convert to TradingBotError if needed
            if not isinstance(error, TradingBotError):
                trading_error = self._convert_to_trading_error(error, context)
            else:
                trading_error = error
                if context:
                    trading_error.context.update(context)

            # Log the error
            await self._log_error(trading_error)

            # Send notification if configured
            if self.notification_manager and trading_error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                await self._send_error_notification(trading_error)

            # Execute registered callbacks
            await self._execute_error_callbacks(trading_error)

            # Handle critical errors
            if trading_error.severity == ErrorSeverity.CRITICAL:
                await self._handle_critical_error(trading_error)

            return True

        except Exception as handler_error:
            # Error in error handler - log to console
            logger.critical(f"Error handler failed: {handler_error}")
            logger.critical(f"Original error: {error}")
            return False

    def _convert_to_trading_error(self, error: Exception, context: Optional[Dict]) -> TradingBotError:
        """Convert generic exception to TradingBotError"""
        error_type = type(error).__name__
        message = str(error)

        # Determine category and severity based on error type and context
        if "connection" in message.lower() or "timeout" in message.lower():
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.MEDIUM
        elif "database" in message.lower() or "sql" in message.lower():
            category = ErrorCategory.DATABASE
            severity = ErrorSeverity.HIGH
        elif "config" in message.lower():
            category = ErrorCategory.CONFIGURATION
            severity = ErrorSeverity.HIGH
        else:
            category = ErrorCategory.SYSTEM
            severity = ErrorSeverity.MEDIUM

        return TradingBotError(
            message=f"{error_type}: {message}",
            category=category,
            severity=severity,
            context=context,
            original_error=error
        )

    async def _log_error(self, error: TradingBotError):
        """Log error with structured information"""
        extra_info = {
            "category": error.category.value,
            "severity": error.severity.value,
            "context": error.context,
            "timestamp": error.timestamp.isoformat()
        }

        if error.original_error:
            extra_info["original_error"] = str(error.original_error)
            extra_info["traceback"] = traceback.format_exception(
                type(error.original_error),
                error.original_error,
                error.original_error.__traceback__
            )

        # Log with appropriate level
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(error.message, **extra_info)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(error.message, **extra_info)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(error.message, **extra_info)
        else:
            logger.info(error.message, **extra_info)

    async def _send_error_notification(self, error: TradingBotError):
        """Send error notification via Telegram"""
        if not self.notification_manager:
            return

        try:
            notification_data = {
                'error_type': error.category.value,
                'severity': error.severity.value,
                'message': error.message,
                'context': error.context,
                'timestamp': error.timestamp
            }

            await self.notification_manager.send_notification(
                'system_events.error_occurred',
                notification_data
            )

        except Exception as notification_error:
            logger.error(f"Failed to send error notification: {notification_error}")

    async def _execute_error_callbacks(self, error: TradingBotError):
        """Execute registered error callbacks"""
        callbacks = self.error_callbacks.get(error.category, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error)
                else:
                    callback(error)
            except Exception as callback_error:
                logger.error(f"Error callback failed: {callback_error}")

    async def _handle_critical_error(self, error: TradingBotError):
        """Handle critical errors that may require system shutdown"""
        logger.critical(f"CRITICAL ERROR DETECTED: {error.message}")

        # Implement emergency procedures based on error category
        if error.category == ErrorCategory.TRADING_EXECUTION:
            # Close all positions if trading execution is compromised
            logger.critical("Trading execution compromised - emergency position closure may be required")

        elif error.category == ErrorCategory.DATABASE:
            # Database issues may require system restart
            logger.critical("Database error detected - system stability at risk")

        # Consider implementing automated system shutdown for critical errors
        # This should be configurable and used with extreme caution

def safe_async_call(func: Callable, error_handler: ErrorHandler, *args, **kwargs):
    """
    Decorator for safe async function calls with error handling
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            await error_handler.handle_error(e, {
                'function': func.__name__,
                'args': str(args)[:100],  # Limit args length
                'kwargs': str(kwargs)[:100]
            })
            return None
    return wrapper

def error_boundary(error_handler: ErrorHandler, category: ErrorCategory = ErrorCategory.SYSTEM):
    """
    Decorator for error boundary around functions
    """
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    await error_handler.handle_error(e, {
                        'function': func.__name__,
                        'category': category.value
                    })
                    raise
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    asyncio.create_task(error_handler.handle_error(e, {
                        'function': func.__name__,
                        'category': category.value
                    }))
                    raise
            return sync_wrapper
    return decorator

# Usage examples
if __name__ == "__main__":
    async def main():
        error_handler = ErrorHandler()

        # Example 1: Handle specific trading error
        try:
            raise TradingExecutionError(
                "Failed to place order",
                symbol="EURUSD",
                ticket=123456
            )
        except Exception as e:
            await error_handler.handle_error(e)

        # Example 2: Register error callback
        async def trading_error_callback(error: TradingBotError):
            print(f"Trading error callback triggered: {error.message}")

        error_handler.register_error_callback(
            ErrorCategory.TRADING_EXECUTION,
            trading_error_callback
        )

        # Example 3: Use error boundary decorator
        @error_boundary(error_handler, ErrorCategory.STRATEGY_ANALYSIS)
        async def risky_strategy_function():
            # Simulate strategy analysis that might fail
            raise ValueError("Strategy analysis failed")

        try:
            await risky_strategy_function()
        except:
            pass  # Error already handled by boundary

    asyncio.run(main())
```

This comprehensive code examples guide provides production-ready implementations for all critical components of the trading bot system, including proper error handling, logging, and best practices for modern Python development.
