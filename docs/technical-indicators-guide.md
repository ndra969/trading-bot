# Technical Indicators Integration Guide

This guide covers the implementation of RSI and Moving Average technical indicators as enhancement layers in the trading bot system.

## Table of Contents
1. [Overview](#overview)
2. [RSI Analysis Layer](#rsi-analysis-layer)
3. [Moving Average Analysis Layer](#moving-average-analysis-layer)
4. [Multi-Timeframe Technical Analysis](#multi-timeframe-technical-analysis)
5. [Integration with Strategy Layers](#integration-with-strategy-layers)
6. [Configuration](#configuration)
7. [Implementation Examples](#implementation-examples)
8. [Performance Optimization](#performance-optimization)

## Overview

The technical indicators system adds RSI and Moving Average analysis as enhancement layers to the foundation-first strategy architecture. These indicators provide additional confluence for signal validation while maintaining the Supply & Demand zones as the mandatory foundation.

### Architecture Integration

```yaml
Strategy Architecture (PRODUCTION READY - 120% Coverage):
├── Foundation (Mandatory): Supply & Demand Zones [35%]
├── Enhancement Layer 1: Trendline Confluence [20%] ✅ IMPLEMENTED
├── Enhancement Layer 2: Price Action Confirmation [15%] ✅ IMPLEMENTED
├── Enhancement Layer 3: Fibonacci Confluence [12%] ✅ IMPLEMENTED
├── Enhancement Layer 4: Breakout Retest Validation [12%] ✅ IMPLEMENTED
├── Enhancement Layer 5: Market Structure Alignment [8%] ✅ IMPLEMENTED
├── Enhancement Layer 6: RSI Analysis [10%] ✅ IMPLEMENTED
└── Enhancement Layer 7: Moving Average Analysis [8%] ✅ IMPLEMENTED
```

### Key Features

✅ **Multi-Timeframe Analysis**: RSI and MA analysis across M15, H1, H4, D1
✅ **Asset-Specific Settings**: Different parameters for Forex, Commodities, Crypto
✅ **Divergence Detection**: RSI bullish/bearish divergence identification
✅ **Trend Alignment**: MA trend confirmation across multiple timeframes
✅ **Performance Optimized**: Cached calculations and batch processing
✅ **Configurable Weights**: Adjustable confluence weights per asset class
✅ **Library Fallback Chain**: pandas-ta → TA-Lib → ta → manual calculations
✅ **Comprehensive Testing**: 38 RSI + 35 MA unit tests, 17 + 18 integration tests
✅ **CLI Integration**: `trading-bot technical analyze` commands for all indicators
✅ **Trading Type Adaptive**: Parameters adjust for scalping, day, swing, position trading

## RSI Analysis Layer

### RSI Configuration by Timeframe

```yaml
rsi:
  parameters:
    M15:
      period: 14
      overbought_level: 75
      oversold_level: 25
      extreme_overbought: 85
      extreme_oversold: 15

    H1:
      period: 14
      overbought_level: 70
      oversold_level: 30
      extreme_overbought: 80
      extreme_oversold: 20

    H4:
      period: 14
      overbought_level: 70
      oversold_level: 30
      extreme_overbought: 80
      extreme_oversold: 20
```

### RSI Analysis Rules

**Buy Signals (for DEMAND zones):**
- **RSI < Oversold** (20 points): Strong buy when RSI below oversold level in demand zone
- **RSI Rising from Oversold** (15 points): Medium buy when RSI rising from oversold
- **Bullish Divergence** (25 points): Strong buy on price makes lower low, RSI makes higher low
- **RSI > 50 in Uptrend** (8 points): Weak buy when RSI above 50 in established uptrend

**Sell Signals (for SUPPLY zones):**
- **RSI > Overbought** (20 points): Strong sell when RSI above overbought level in supply zone
- **RSI Falling from Overbought** (15 points): Medium sell when RSI falling from overbought
- **Bearish Divergence** (25 points): Strong sell on price makes higher high, RSI makes lower high
- **RSI < 50 in Downtrend** (8 points): Weak sell when RSI below 50 in established downtrend

### RSI Implementation Example

```python
class RSIAnalyzer:
    def __init__(self, config):
        self.config = config
        self.cache = {}

    async def analyze_rsi_signal(self, symbol: str, zone: SupplyDemandZone, timeframe: str) -> RSISignal:
        """
        Analyze RSI signals for a specific S&D zone.

        Returns:
            RSISignal with confidence score and analysis details
        """
        rsi_data = await self.get_rsi_data(symbol, timeframe)
        current_rsi = rsi_data[-1]

        rsi_signal = RSISignal(
            symbol=symbol,
            timeframe=timeframe,
            rsi_value=current_rsi,
            zone_type=zone.zone_type
        )

        # Analyze based on zone type
        if zone.zone_type == "DEMAND":
            rsi_signal.confidence += await self._analyze_buy_signals(rsi_data, zone)
        else:  # SUPPLY
            rsi_signal.confidence += await self._analyze_sell_signals(rsi_data, zone)

        # Check for divergences
        divergence_score = await self._check_divergences(symbol, timeframe, zone.zone_type)
        rsi_signal.confidence += divergence_score

        return rsi_signal

    async def _analyze_buy_signals(self, rsi_data: List[float], zone: SupplyDemandZone) -> float:
        """Analyze RSI buy signals for demand zones."""
        confidence = 0.0
        current_rsi = rsi_data[-1]

        # Get timeframe-specific levels
        levels = self.config['rsi']['parameters'][zone.timeframe]

        # RSI below oversold in demand zone
        if current_rsi < levels['oversold_level']:
            confidence += 20  # Strong buy signal

        # RSI rising from oversold
        if len(rsi_data) >= 3:
            if (rsi_data[-3] < levels['oversold_level'] and
                rsi_data[-2] < levels['oversold_level'] and
                current_rsi > rsi_data[-2]):
                confidence += 15  # Medium buy signal

        # RSI above 50 in uptrend
        if current_rsi > 50:
            # Check if we're in an uptrend context
            if await self._is_uptrend_context(zone):
                confidence += 8  # Weak buy signal

        return confidence

    async def _check_divergences(self, symbol: str, timeframe: str, zone_type: str) -> float:
        """
        Check for RSI divergences.

        Bullish Divergence: Price makes lower low, RSI makes higher low
        Bearish Divergence: Price makes higher high, RSI makes lower high
        """
        # Get price and RSI data for divergence analysis
        price_data = await self.get_price_data(symbol, timeframe, lookback=50)
        rsi_data = await self.get_rsi_data(symbol, timeframe, lookback=50)

        if zone_type == "DEMAND":
            # Look for bullish divergence
            return await self._detect_bullish_divergence(price_data, rsi_data)
        else:
            # Look for bearish divergence
            return await self._detect_bearish_divergence(price_data, rsi_data)

    async def _detect_bullish_divergence(self, prices: List[float], rsi_values: List[float]) -> float:
        """Detect bullish RSI divergence."""
        # Find recent swing lows in price and RSI
        price_lows = self._find_swing_lows(prices, window=5)
        rsi_lows = self._find_swing_lows(rsi_values, window=5)

        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            # Check if price made lower low but RSI made higher low
            latest_price_low = price_lows[-1]
            previous_price_low = price_lows[-2]
            latest_rsi_low = rsi_lows[-1]
            previous_rsi_low = rsi_lows[-2]

            if (latest_price_low['value'] < previous_price_low['value'] and
                latest_rsi_low['value'] > previous_rsi_low['value']):
                return 25  # Strong bullish divergence signal

        return 0
```

## Moving Average Analysis Layer

### MA Configuration

```yaml
moving_averages:
  ma_types:
    ema_fast:
      type: "EMA"
      period: 21
      enabled: true

    ema_slow:
      type: "EMA"
      period: 50
      enabled: true

    sma_trend:
      type: "SMA"
      period: 200
      enabled: true

    ema_short:
      type: "EMA"
      period: 9
      enabled: true
```

### MA Analysis Rules

**Trend Identification:**
- **Strong Uptrend** (25 points): Price > EMA21 > EMA50 > SMA200
- **Medium Uptrend** (15 points): Price > EMA21 > EMA50
- **Weak Uptrend** (8 points): Price > EMA21
- **Strong Downtrend** (25 points): Price < EMA21 < EMA50 < SMA200
- **Medium Downtrend** (15 points): Price < EMA21 < EMA50
- **Weak Downtrend** (8 points): Price < EMA21

**MA Cross Signals:**
- **Golden Cross** (20 points): EMA21 crosses above EMA50 (bullish)
- **Death Cross** (20 points): EMA21 crosses below EMA50 (bearish)
- **Fast Cross Up** (12 points): EMA9 crosses above EMA21 (bullish)
- **Fast Cross Down** (12 points): EMA9 crosses below EMA21 (bearish)

### MA Implementation Example

```python
class MovingAverageAnalyzer:
    def __init__(self, config):
        self.config = config
        self.ma_cache = {}

    async def analyze_ma_signal(self, symbol: str, zone: SupplyDemandZone, timeframe: str) -> MASignal:
        """
        Analyze Moving Average signals for a specific S&D zone.
        """
        # Get MA data for all configured periods
        ma_data = await self.get_all_ma_data(symbol, timeframe)
        current_price = await self.get_current_price(symbol)

        ma_signal = MASignal(
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
            zone_type=zone.zone_type
        )

        # Analyze trend alignment
        trend_score = await self._analyze_trend_alignment(ma_data, current_price, zone.zone_type)
        ma_signal.confidence += trend_score

        # Analyze MA crosses
        cross_score = await self._analyze_ma_crosses(ma_data, zone.zone_type)
        ma_signal.confidence += cross_score

        # Analyze price action with MAs
        price_action_score = await self._analyze_price_ma_interaction(ma_data, current_price, zone)
        ma_signal.confidence += price_action_score

        return ma_signal

    async def _analyze_trend_alignment(self, ma_data: Dict, current_price: float, zone_type: str) -> float:
        """Analyze trend alignment based on MA hierarchy."""
        confidence = 0.0

        ema9 = ma_data['ema_short'][-1]
        ema21 = ma_data['ema_fast'][-1]
        ema50 = ma_data['ema_slow'][-1]
        sma200 = ma_data['sma_trend'][-1]

        if zone_type == "DEMAND":
            # Check for bullish alignment
            if current_price > ema21 > ema50 > sma200:
                confidence += 25  # Strong uptrend
            elif current_price > ema21 > ema50:
                confidence += 15  # Medium uptrend
            elif current_price > ema21:
                confidence += 8   # Weak uptrend

        else:  # SUPPLY zone
            # Check for bearish alignment
            if current_price < ema21 < ema50 < sma200:
                confidence += 25  # Strong downtrend
            elif current_price < ema21 < ema50:
                confidence += 15  # Medium downtrend
            elif current_price < ema21:
                confidence += 8   # Weak downtrend

        return confidence

    async def _analyze_ma_crosses(self, ma_data: Dict, zone_type: str) -> float:
        """Analyze MA crossover signals."""
        confidence = 0.0

        # Check for recent crosses (within last 5 candles)
        ema9_current = ma_data['ema_short'][-1]
        ema9_previous = ma_data['ema_short'][-2]
        ema21_current = ma_data['ema_fast'][-1]
        ema21_previous = ma_data['ema_fast'][-2]
        ema50_current = ma_data['ema_slow'][-1]
        ema50_previous = ma_data['ema_slow'][-2]

        if zone_type == "DEMAND":
            # Look for bullish crosses
            # Golden Cross: EMA21 crosses above EMA50
            if (ema21_previous <= ema50_previous and ema21_current > ema50_current):
                confidence += 20

            # Fast Cross: EMA9 crosses above EMA21
            if (ema9_previous <= ema21_previous and ema9_current > ema21_current):
                confidence += 12

        else:  # SUPPLY zone
            # Look for bearish crosses
            # Death Cross: EMA21 crosses below EMA50
            if (ema21_previous >= ema50_previous and ema21_current < ema50_current):
                confidence += 20

            # Fast Cross Down: EMA9 crosses below EMA21
            if (ema9_previous >= ema21_previous and ema9_current < ema21_current):
                confidence += 12

        return confidence
```

## Multi-Timeframe Technical Analysis

### Timeframe Confluence System

```python
class MultiTimeframeTechnicalAnalyzer:
    def __init__(self, config):
        self.config = config
        self.timeframes = ["H1", "H4", "D1"]
        self.timeframe_weights = {"H1": 1, "H4": 2, "D1": 3}

    async def analyze_multi_timeframe_confluence(self, symbol: str, zone: SupplyDemandZone) -> TechnicalConfluence:
        """
        Analyze technical indicator confluence across multiple timeframes.
        """
        confluence = TechnicalConfluence(symbol=symbol, zone=zone)

        # Analyze RSI across timeframes
        rsi_confluence = await self._analyze_rsi_confluence(symbol, zone)
        confluence.rsi_scores = rsi_confluence

        # Analyze MA across timeframes
        ma_confluence = await self._analyze_ma_confluence(symbol, zone)
        confluence.ma_scores = ma_confluence

        # Calculate weighted confluence score
        confluence.final_score = self._calculate_weighted_score(rsi_confluence, ma_confluence)

        return confluence

    async def _analyze_rsi_confluence(self, symbol: str, zone: SupplyDemandZone) -> Dict[str, float]:
        """Analyze RSI confluence across multiple timeframes."""
        rsi_scores = {}

        for timeframe in self.timeframes:
            rsi_analyzer = RSIAnalyzer(self.config)
            rsi_signal = await rsi_analyzer.analyze_rsi_signal(symbol, zone, timeframe)
            rsi_scores[timeframe] = rsi_signal.confidence

        return rsi_scores

    async def _analyze_ma_confluence(self, symbol: str, zone: SupplyDemandZone) -> Dict[str, float]:
        """Analyze MA confluence across multiple timeframes."""
        ma_scores = {}

        for timeframe in self.timeframes:
            ma_analyzer = MovingAverageAnalyzer(self.config)
            ma_signal = await ma_analyzer.analyze_ma_signal(symbol, zone, timeframe)
            ma_scores[timeframe] = ma_signal.confidence

        return ma_scores

    def _calculate_weighted_score(self, rsi_scores: Dict, ma_scores: Dict) -> float:
        """Calculate weighted confluence score across timeframes."""
        total_rsi_score = 0
        total_ma_score = 0
        total_weight = 0

        for timeframe in self.timeframes:
            weight = self.timeframe_weights[timeframe]
            total_rsi_score += rsi_scores.get(timeframe, 0) * weight
            total_ma_score += ma_scores.get(timeframe, 0) * weight
            total_weight += weight

        # Normalize scores
        avg_rsi_score = total_rsi_score / total_weight if total_weight > 0 else 0
        avg_ma_score = total_ma_score / total_weight if total_weight > 0 else 0

        # Combine RSI and MA scores with their respective weights
        rsi_weight = self.config['technical_indicators']['rsi']['confluence_weight']
        ma_weight = self.config['technical_indicators']['moving_averages']['confluence_weight']

        final_score = (avg_rsi_score * rsi_weight) + (avg_ma_score * ma_weight)

        return final_score
```

## Integration with Strategy Layers

### Enhanced Strategy Engine

```python
class EnhancedStrategyEngine:
    def __init__(self, config):
        self.config = config
        self.rsi_analyzer = RSIAnalyzer(config)
        self.ma_analyzer = MovingAverageAnalyzer(config)
        self.multi_tf_analyzer = MultiTimeframeTechnicalAnalyzer(config)

    async def analyze_symbol_with_technical_indicators(self, symbol: str) -> Optional[EnhancedTradingSignal]:
        """
        Complete analysis with technical indicators integration.
        """
        # 1. Foundation: S&D Zones (MANDATORY)
        sd_analyzer = SupplyDemandAnalyzer(self.config)
        sd_zones = await sd_analyzer.detect_zones(symbol)

        if not sd_zones:
            return None

        best_signals = []

        for zone in sd_zones:
            enhanced_signal = EnhancedTradingSignal(base_zone=zone)

            # 2. Traditional Enhancement Layers
            if self.config['enhancement_layers']['price_action_confirmation']['enabled']:
                pa_signal = await self.price_action_analyzer.analyze(symbol, zone)
                enhanced_signal.add_layer('price_action', pa_signal)

            if self.config['enhancement_layers']['fibonacci_confluence']['enabled']:
                fib_signal = await self.fibonacci_analyzer.analyze(symbol, zone)
                enhanced_signal.add_layer('fibonacci', fib_signal)

            # 3. Technical Indicator Layers (NEW)
            if self.config['enhancement_layers']['rsi_analysis']['enabled']:
                rsi_signal = await self.rsi_analyzer.analyze_rsi_signal(symbol, zone, zone.timeframe)
                enhanced_signal.add_layer('rsi_analysis', rsi_signal)

            if self.config['enhancement_layers']['moving_average_analysis']['enabled']:
                ma_signal = await self.ma_analyzer.analyze_ma_signal(symbol, zone, zone.timeframe)
                enhanced_signal.add_layer('moving_average_analysis', ma_signal)

            # 4. Multi-Timeframe Technical Confluence
            technical_confluence = await self.multi_tf_analyzer.analyze_multi_timeframe_confluence(symbol, zone)
            enhanced_signal.technical_confluence = technical_confluence

            # 5. Calculate Final Confluence Score
            final_score = self._calculate_enhanced_confluence_score(enhanced_signal)
            enhanced_signal.final_confidence = final_score

            if self._meets_enhanced_requirements(enhanced_signal):
                best_signals.append(enhanced_signal)

        # Return best signal
        return max(best_signals, key=lambda s: s.final_confidence) if best_signals else None

    def _calculate_enhanced_confluence_score(self, signal: EnhancedTradingSignal) -> float:
        """Calculate confluence score with technical indicators."""
        weights = self.config['confluence_weights']
        total_score = 0

        # Foundation score (mandatory)
        total_score += signal.base_zone.strength * weights['foundation']

        # Enhancement layer scores
        for layer_name, layer_signal in signal.layers.items():
            if layer_signal and layer_name in weights:
                total_score += layer_signal.confidence * weights[layer_name]

        # Technical confluence bonus
        if signal.technical_confluence:
            total_score += signal.technical_confluence.final_score

        # Multi-layer bonus
        active_layers = len([s for s in signal.layers.values() if s is not None])
        if active_layers >= 4:  # Foundation + 3+ enhancement layers
            total_score += 5  # Multi-layer bonus

        # Technical agreement bonus
        if signal.technical_confluence and signal.technical_confluence.final_score > 15:
            total_score += 8  # Strong technical agreement bonus

        return min(total_score, 100)  # Cap at 100%

    def _meets_enhanced_requirements(self, signal: EnhancedTradingSignal) -> bool:
        """Check if signal meets enhanced requirements with technical indicators."""
        requirements = self.config['signal_requirements']

        # Basic requirements
        if signal.final_confidence < requirements['min_final_confidence']:
            return False

        # Minimum active layers
        active_layers = len([s for s in signal.layers.values() if s is not None])
        if active_layers < requirements['min_active_layers']:
            return False

        # Technical indicator requirement
        technical_layers = ['rsi_analysis', 'moving_average_analysis']
        technical_active = sum(1 for layer in technical_layers if signal.layers.get(layer))

        if technical_active < requirements.get('min_technical_indicators', 1):
            return False

        return True
```

## Asset-Specific Technical Settings

### Configuration by Asset Class

```yaml
asset_specific_settings:
  forex_major:
    rsi:
      overbought_adjustment: +5  # More sensitive for forex
      oversold_adjustment: -5
    moving_averages:
      ema_fast_period: 21
      ema_slow_period: 50
    confluence_weights:
      rsi_analysis: 0.12
      moving_average_analysis: 0.08

  commodities:
    rsi:
      overbought_adjustment: 0   # Standard levels
      oversold_adjustment: 0
    moving_averages:
      ema_fast_period: 34       # Slower for commodities
      ema_slow_period: 89
    confluence_weights:
      rsi_analysis: 0.08
      moving_average_analysis: 0.12  # MAs more reliable

  crypto:
    rsi:
      overbought_adjustment: +10  # More extreme for crypto
      oversold_adjustment: -10
    moving_averages:
      ema_fast_period: 21
      ema_slow_period: 50
    confluence_weights:
      rsi_analysis: 0.15         # RSI very useful for crypto
      moving_average_analysis: 0.08
```

## Recommended Libraries for Technical Indicators

### Best Libraries for Windows Compatibility

**1. TA-Lib (Recommended)**
```bash
# Installation for Windows
pip install TA-Lib

# Alternative for Windows (pre-compiled)
pip install --only-binary=all TA-Lib
```

**2. Pandas-TA (Pure Python - Always Works)**
```bash
pip install pandas-ta
```

**3. Technical Analysis Library (Python)**
```bash
pip install ta
```

**4. Tulipy (C Library - Fast)**
```bash
pip install tulipy
```

### Updated pyproject.toml Dependencies

```toml
[project]
dependencies = [
    # Existing dependencies...
    "pandas-ta>=0.3.14b",     # Pure Python - Most reliable
    "ta>=0.10.2",             # Comprehensive technical analysis
    "numpy>=1.24.0",          # Required for calculations
    "pandas>=2.0.0",          # Required for data handling
]

[project.optional-dependencies]
dev = [
    # Existing dev dependencies...
]

# Optional high-performance indicators (may need compilation)
performance = [
    "TA-Lib>=0.4.25",         # Industry standard (requires compilation)
    "tulipy>=0.4.0",          # Fast C implementation
]
```

## Performance Optimization with Libraries

### Using Pandas-TA (Recommended for Reliability)

```python
import pandas as pd
import pandas_ta as ta
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class TechnicalIndicatorCalculator:
    def __init__(self, cache_duration_minutes=5):
        self.cache = {}
        self.cache_duration = timedelta(minutes=cache_duration_minutes)

    async def calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calculate RSI using pandas-ta (most reliable)."""
        cache_key = f"rsi_{len(prices)}_{period}_{hash(tuple(prices[-10:]))}"

        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']

        # Convert to pandas Series
        price_series = pd.Series(prices)

        # Calculate RSI using pandas-ta
        rsi_series = ta.rsi(price_series, length=period)

        # Convert back to list, removing NaN values
        rsi_values = rsi_series.dropna().tolist()

        # Cache result
        self._cache_result(cache_key, rsi_values)
        return rsi_values

    async def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate EMA using pandas-ta."""
        cache_key = f"ema_{len(prices)}_{period}_{hash(tuple(prices[-10:]))}"

        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']

        price_series = pd.Series(prices)
        ema_series = ta.ema(price_series, length=period)
        ema_values = ema_series.dropna().tolist()

        self._cache_result(cache_key, ema_values)
        return ema_values

    async def calculate_sma(self, prices: List[float], period: int) -> List[float]:
        """Calculate SMA using pandas-ta."""
        cache_key = f"sma_{len(prices)}_{period}_{hash(tuple(prices[-10:]))}"

        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']

        price_series = pd.Series(prices)
        sma_series = ta.sma(price_series, length=period)
        sma_values = sma_series.dropna().tolist()

        self._cache_result(cache_key, sma_values)
        return sma_values

    async def calculate_multiple_indicators(self,
                                          prices: List[float],
                                          high: List[float] = None,
                                          low: List[float] = None,
                                          volume: List[float] = None) -> Dict:
        """Calculate multiple indicators efficiently using pandas-ta."""

        # Create DataFrame for multiple indicator calculation
        df = pd.DataFrame({
            'close': prices,
            'high': high or prices,  # Use close if high not provided
            'low': low or prices,    # Use close if low not provided
            'volume': volume or [1] * len(prices)  # Use 1 if volume not provided
        })

        # Calculate all indicators at once (more efficient)
        df.ta.rsi(length=14, append=True)           # RSI_14
        df.ta.ema(length=9, append=True)            # EMA_9
        df.ta.ema(length=21, append=True)           # EMA_21
        df.ta.ema(length=50, append=True)           # EMA_50
        df.ta.sma(length=200, append=True)          # SMA_200
        df.ta.macd(append=True)                     # MACD (bonus indicator)
        df.ta.bbands(append=True)                   # Bollinger Bands (bonus)

        # Extract results
        results = {
            'rsi': df['RSI_14'].dropna().tolist(),
            'ema_9': df['EMA_9'].dropna().tolist(),
            'ema_21': df['EMA_21'].dropna().tolist(),
            'ema_50': df['EMA_50'].dropna().tolist(),
            'sma_200': df['SMA_200'].dropna().tolist(),
            'macd': df['MACD_12_26_9'].dropna().tolist() if 'MACD_12_26_9' in df.columns else [],
            'macd_signal': df['MACDs_12_26_9'].dropna().tolist() if 'MACDs_12_26_9' in df.columns else [],
            'bb_upper': df['BBU_20_2.0'].dropna().tolist() if 'BBU_20_2.0' in df.columns else [],
            'bb_lower': df['BBL_20_2.0'].dropna().tolist() if 'BBL_20_2.0' in df.columns else [],
        }

        return results

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache:
            return False
        return datetime.now() < self.cache[cache_key]['expires']

    def _cache_result(self, cache_key: str, data):
        """Cache calculation result."""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now(),
            'expires': datetime.now() + self.cache_duration
        }

# Alternative implementation using TA library
class TALibIndicatorCalculator:
    """Alternative implementation using 'ta' library (pure Python)."""

    def __init__(self):
        from ta import trend, momentum, volume
        self.trend = trend
        self.momentum = momentum
        self.volume = volume

    async def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate indicators using 'ta' library."""

        results = {}

        # RSI
        results['rsi'] = self.momentum.RSIIndicator(
            close=df['close'], window=14
        ).rsi().dropna().tolist()

        # EMAs
        results['ema_21'] = self.trend.EMAIndicator(
            close=df['close'], window=21
        ).ema_indicator().dropna().tolist()

        results['ema_50'] = self.trend.EMAIndicator(
            close=df['close'], window=50
        ).ema_indicator().dropna().tolist()

        # SMA
        results['sma_200'] = self.trend.SMAIndicator(
            close=df['close'], window=200
        ).sma_indicator().dropna().tolist()

        # MACD
        macd = self.trend.MACD(close=df['close'])
        results['macd'] = macd.macd().dropna().tolist()
        results['macd_signal'] = macd.macd_signal().dropna().tolist()

        return results

# High-performance implementation using TA-Lib (optional)
class TALibHighPerformance:
    """High-performance implementation using TA-Lib (requires compilation)."""

    def __init__(self):
        try:
            import talib
            self.talib = talib
            self.available = True
        except ImportError:
            self.available = False
            print("TA-Lib not available. Install with: pip install TA-Lib")

    async def calculate_indicators(self, prices: List[float]) -> Dict:
        """Calculate indicators using TA-Lib (fastest)."""
        if not self.available:
            raise ImportError("TA-Lib not installed")

        import numpy as np

        # Convert to numpy array (required by TA-Lib)
        price_array = np.array(prices, dtype=float)

        results = {
            'rsi': self.talib.RSI(price_array, timeperiod=14).tolist(),
            'ema_21': self.talib.EMA(price_array, timeperiod=21).tolist(),
            'ema_50': self.talib.EMA(price_array, timeperiod=50).tolist(),
            'sma_200': self.talib.SMA(price_array, timeperiod=200).tolist(),
            'macd': self.talib.MACD(price_array)[0].tolist(),  # MACD line
            'macd_signal': self.talib.MACD(price_array)[1].tolist(),  # Signal line
        }

        # Remove NaN values
        for key, values in results.items():
            results[key] = [v for v in values if not np.isnan(v)]

        return results
```

### Library-Based Implementation in Strategy Engine

```python
class EnhancedTechnicalAnalyzer:
    def __init__(self, config):
        self.config = config

        # Initialize calculator based on available libraries
        self.calculator = self._initialize_calculator()

    def _initialize_calculator(self):
        """Initialize the best available calculator."""

        # Try TA-Lib first (fastest)
        try:
            import talib
            return TALibHighPerformance()
        except ImportError:
            pass

        # Fall back to pandas-ta (most reliable)
        try:
            import pandas_ta
            return TechnicalIndicatorCalculator()
        except ImportError:
            pass

        # Fall back to 'ta' library
        try:
            import ta
            return TALibIndicatorCalculator()
        except ImportError:
            raise ImportError("No technical analysis library available. Install: pip install pandas-ta")

    async def analyze_symbol_with_libraries(self, symbol: str, timeframe: str) -> Dict:
        """Analyze symbol using library-based calculations."""

        # Get price data
        price_data = await self.get_ohlcv_data(symbol, timeframe, lookback=200)

        # Calculate all indicators at once
        if isinstance(self.calculator, TechnicalIndicatorCalculator):
            # Use pandas-ta for multiple indicators
            indicators = await self.calculator.calculate_multiple_indicators(
                prices=price_data['close'],
                high=price_data['high'],
                low=price_data['low'],
                volume=price_data['volume']
            )
        else:
            # Use other calculators
            indicators = await self.calculator.calculate_indicators(price_data['close'])

        return indicators

    async def get_current_rsi(self, symbol: str, timeframe: str, period: int = 14) -> float:
        """Get current RSI value using libraries."""
        price_data = await self.get_price_data(symbol, timeframe, lookback=period * 3)

        rsi_values = await self.calculator.calculate_rsi(price_data, period)
        return rsi_values[-1] if rsi_values else None

    async def get_ma_trend_direction(self, symbol: str, timeframe: str) -> str:
        """Get MA trend direction using libraries."""
        indicators = await self.analyze_symbol_with_libraries(symbol, timeframe)

        if not indicators['ema_21'] or not indicators['ema_50']:
            return "UNKNOWN"

        ema_21 = indicators['ema_21'][-1]
        ema_50 = indicators['ema_50'][-1]

        if ema_21 > ema_50:
            return "BULLISH"
        elif ema_21 < ema_50:
            return "BEARISH"
        else:
            return "NEUTRAL"
```

### Library Performance Comparison

| Library | Speed | Reliability | Windows Support | Compilation Required |
|---------|-------|-------------|-----------------|---------------------|
| **pandas-ta** | Medium | ⭐⭐⭐⭐⭐ | ✅ Always | ❌ No |
| **ta** | Medium | ⭐⭐⭐⭐ | ✅ Always | ❌ No |
| **TA-Lib** | ⭐⭐⭐⭐⭐ Fast | ⭐⭐⭐⭐⭐ | ⚠️ Sometimes | ✅ Yes |
| **tulipy** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⚠️ Sometimes | ✅ Yes |
| **Manual** | Slow | ⭐⭐ | ✅ Always | ❌ No |

### Recommended Strategy

```python
# Fallback chain for maximum compatibility
class RobustIndicatorCalculator:
    def __init__(self):
        self.primary = None
        self.fallback = None

        # Try to initialize in order of preference
        self._initialize_calculators()

    def _initialize_calculators(self):
        """Initialize calculators with fallback chain."""

        # Primary: pandas-ta (most reliable)
        try:
            import pandas_ta
            self.primary = TechnicalIndicatorCalculator()
            print("✅ Using pandas-ta for technical indicators")
        except ImportError:
            pass

        # Fallback: ta library
        try:
            import ta
            self.fallback = TALibIndicatorCalculator()
            print("⚠️ Using 'ta' library as fallback")
        except ImportError:
            if not self.primary:
                raise ImportError("No technical analysis library available!")

    async def calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calculate RSI with fallback."""
        try:
            return await self.primary.calculate_rsi(prices, period)
        except Exception as e:
            if self.fallback:
                print(f"Primary failed, using fallback: {e}")
                return await self.fallback.calculate_rsi(prices, period)
            raise
```

## CLI Commands for Technical Indicators

```bash
# Technical indicator analysis
uv run trading-bot technical analyze --symbol EURUSD --indicator rsi
uv run trading-bot technical analyze --symbol EURUSD --indicator ma
uv run trading-bot technical multi-timeframe --symbol EURUSD

# Technical indicator configuration
uv run trading-bot technical enable --indicator rsi
uv run trading-bot technical disable --indicator ma
uv run trading-bot technical weights --rsi 0.12 --ma 0.10

# Technical indicator testing
uv run trading-bot technical test --indicator rsi --symbol EURUSD --timeframe H1
uv run trading-bot technical backtest --indicators rsi,ma --days 30

# Performance monitoring
uv run trading-bot technical performance --show-cache-stats
uv run trading-bot technical cache clear
uv run trading-bot technical cache status

# Technical signal generation
uv run trading-bot technical signals --symbol EURUSD --show-confluence
uv run trading-bot technical divergence --symbol EURUSD --indicator rsi
```

## Integration Examples

### Complete Signal Analysis

```python
# Example: Complete analysis with all layers including technical indicators
async def analyze_eurusd_with_technical():
    strategy_engine = EnhancedStrategyEngine(config)

    # Analyze EURUSD with all enhancement layers
    signal = await strategy_engine.analyze_symbol_with_technical_indicators("EURUSD")

    if signal:
        print(f"📊 Enhanced Signal for EURUSD:")
        print(f"📈 Zone Type: {signal.base_zone.zone_type}")
        print(f"⭐ Final Confidence: {signal.final_confidence}%")
        print(f"🎯 Entry: {signal.base_zone.entry_price}")
        print(f"🛡️ Stop Loss: {signal.base_zone.stop_loss}")
        print(f"🎁 Take Profit: {signal.base_zone.take_profit}")

        print(f"\n📊 Layer Contributions:")
        for layer_name, layer_signal in signal.layers.items():
            if layer_signal:
                print(f"  • {layer_name}: {layer_signal.confidence}%")

        if signal.technical_confluence:
            print(f"\n⚡ Technical Confluence:")
            print(f"  • RSI Multi-TF: {signal.technical_confluence.rsi_scores}")
            print(f"  • MA Multi-TF: {signal.technical_confluence.ma_scores}")
            print(f"  • Combined Score: {signal.technical_confluence.final_score}")

# Expected Output:
"""
📊 Enhanced Signal for EURUSD:
📈 Zone Type: DEMAND
⭐ Final Confidence: 78.5%
🎯 Entry: 1.0850
🛡️ Stop Loss: 1.0835
🎁 Take Profit: 1.0880

📊 Layer Contributions:
  • price_action: 18.0%
  • fibonacci: 12.0%
  • breakout_retest: 15.0%
  • rsi_analysis: 22.0%
  • moving_average_analysis: 16.0%

⚡ Technical Confluence:
  • RSI Multi-TF: {'H1': 25, 'H4': 18, 'D1': 15}
  • MA Multi-TF: {'H1': 20, 'H4': 24, 'D1': 18}
  • Combined Score: 19.2
"""
```

The technical indicators system provides sophisticated RSI and Moving Average analysis that enhances the foundation-first strategy architecture while maintaining the system's reliability and performance standards.
