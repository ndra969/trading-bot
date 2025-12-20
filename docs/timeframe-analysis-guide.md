# Multi-Timeframe Analysis Guide

This guide provides comprehensive information about the sophisticated multi-timeframe analysis system, confluence scoring, and timeframe-specific configurations for different asset classes.

## Multi-Timeframe Analysis Overview

The trading bot implements a sophisticated multi-timeframe analysis system that validates trading signals across multiple time horizons to ensure high-probability setups with proper confluence.

### Core Philosophy

**Timeframe Confluence**: A trading signal is only considered valid when multiple timeframes align and confirm the same directional bias. This approach significantly reduces false signals and improves trade quality.

```python
# Multi-timeframe analysis hierarchy
TIMEFRAME_HIERARCHY = {
    "primary": "H1",     # Main analysis timeframe
    "secondary": "H4",   # Trend confirmation
    "tertiary": "D1",    # Major trend direction
    "execution": "M15"   # Entry refinement
}

# Timeframe weights for confluence scoring
TIMEFRAME_WEIGHTS = {
    "D1": 3,   # Daily trend - Highest priority (30% influence)
    "H4": 2,   # 4-hour trend - Medium priority (40% influence)
    "H1": 1,   # 1-hour trend - Lower priority (30% influence)
    "M15": 0.5 # Execution timeframe - Refinement only
}
```

## Default Timeframe Configuration

### Core System Configuration

```yaml
# config/multi_timeframe_config.yaml
multi_timeframe:
  enabled: true

  # Core timeframe settings
  primary_timeframe: "H1"      # Main analysis timeframe
  secondary_timeframe: "H4"    # Trend confirmation
  tertiary_timeframe: "D1"     # Major trend direction
  analysis_timeframes: ["M15", "H1", "H4", "D1"]  # All analyzed timeframes

  # Trend analysis weights
  trend_weights:
    D1: 3    # Daily trend - Highest priority
    H4: 2    # 4-hour trend - Medium priority
    H1: 1    # 1-hour trend - Lower priority
    M15: 0.5 # Execution refinement

  # Confluence requirements
  minimum_trend_strength: 4        # Combined weight threshold
  trend_alignment_weight: 0.45     # Overall trend influence in signal scoring
  min_timeframe_agreement: 2       # Minimum timeframes that must agree

  # Cache settings for performance
  cache_duration:
    M15: 300   # 5 minutes
    H1: 1800   # 30 minutes
    H4: 7200   # 2 hours
    D1: 14400  # 4 hours

  # Analysis depth
  lookback_periods:
    M15: 100   # 25 hours of data
    H1: 168    # 1 week of data
    H4: 168    # 4 weeks of data
    D1: 100    # ~3 months of data
```

### Timeframe-Specific Analysis Parameters

```python
# Structure detection parameters by timeframe
TIMEFRAME_SETTINGS = {
    "M15": {
        "lookback_periods": 50,
        "bos_confirmation_candles": 3,
        "choch_momentum_threshold": 0.3,
        "swing_detection_strength": 3,
        "min_fvg_size_pips": {
            "forex": 3,
            "commodities": 15,
            "crypto": 50,
            "indices": 10
        },
        "noise_filter": 0.2,
        "volume_threshold": 1.1
    },
    "H1": {
        "lookback_periods": 100,
        "bos_confirmation_candles": 5,
        "choch_momentum_threshold": 0.4,
        "swing_detection_strength": 5,
        "min_fvg_size_pips": {
            "forex": 8,
            "commodities": 30,
            "crypto": 100,
            "indices": 25
        },
        "noise_filter": 0.3,
        "volume_threshold": 1.2
    },
    "H4": {
        "lookback_periods": 200,
        "bos_confirmation_candles": 8,
        "choch_momentum_threshold": 0.5,
        "swing_detection_strength": 8,
        "min_fvg_size_pips": {
            "forex": 15,
            "commodities": 60,
            "crypto": 200,
            "indices": 50
        },
        "noise_filter": 0.4,
        "volume_threshold": 1.3
    },
    "D1": {
        "lookback_periods": 100,
        "bos_confirmation_candles": 10,
        "choch_momentum_threshold": 0.6,
        "swing_detection_strength": 12,
        "min_fvg_size_pips": {
            "forex": 30,
            "commodities": 150,
            "crypto": 500,
            "indices": 100
        },
        "noise_filter": 0.5,
        "volume_threshold": 1.5
    }
}
```

## Confluence Scoring System

### Multi-Timeframe Confluence Weights

```python
# Confluence components and their weights
CONFLUENCE_WEIGHTS = {
    "trend_alignment": 0.35,        # Cross-timeframe trend agreement
    "structure_confluence": 0.25,   # BOS/CHoCH alignment across timeframes
    "order_block_proximity": 0.20,  # Order block validation
    "fvg_alignment": 0.10,          # Fair Value Gap confluence
    "liquidity_context": 0.10       # Liquidity pool analysis
}

# Minimum confluence requirements
MIN_CONFLUENCE_SCORE = 0.65          # 65% minimum for trade execution
HIGH_CONFLUENCE_THRESHOLD = 0.80     # 80% for high-confidence trades
PERFECT_CONFLUENCE_THRESHOLD = 0.90  # 90% for exceptional setups

# Timeframe agreement bonuses
AGREEMENT_BONUSES = {
    "two_timeframes": 5.0,    # +5% when 2 timeframes agree
    "three_timeframes": 10.0, # +10% when 3 timeframes agree
    "four_timeframes": 15.0,  # +15% when all 4 timeframes agree
    "perfect_alignment": 20.0 # +20% when all factors align perfectly
}
```

### Confluence Scoring Implementation

```python
class MultiTimeframeConfluenceScorer:
    """
    Advanced confluence scoring system for multi-timeframe analysis
    """

    def __init__(self, config):
        self.config = config
        self.weights = CONFLUENCE_WEIGHTS
        self.timeframe_weights = config['trend_weights']
        self.agreement_bonuses = AGREEMENT_BONUSES

    async def calculate_confluence_score(self, symbol: str, timeframe_analyses: Dict) -> ConfluenceResult:
        """
        Calculate comprehensive confluence score across all timeframes
        """
        # 1. Trend Alignment Score
        trend_score = await self._calculate_trend_alignment_score(timeframe_analyses)

        # 2. Structure Confluence Score
        structure_score = await self._calculate_structure_confluence_score(timeframe_analyses)

        # 3. Order Block Proximity Score
        orderblock_score = await self._calculate_orderblock_proximity_score(symbol, timeframe_analyses)

        # 4. Fair Value Gap Alignment Score
        fvg_score = await self._calculate_fvg_alignment_score(symbol, timeframe_analyses)

        # 5. Liquidity Context Score
        liquidity_score = await self._calculate_liquidity_context_score(symbol, timeframe_analyses)

        # Calculate base confluence score
        base_score = (
            trend_score * self.weights['trend_alignment'] +
            structure_score * self.weights['structure_confluence'] +
            orderblock_score * self.weights['order_block_proximity'] +
            fvg_score * self.weights['fvg_alignment'] +
            liquidity_score * self.weights['liquidity_context']
        )

        # Apply agreement bonuses
        agreement_bonus = await self._calculate_agreement_bonus(timeframe_analyses)

        # Final confluence score (capped at 100%)
        final_score = min(base_score + agreement_bonus, 100.0)

        return ConfluenceResult(
            symbol=symbol,
            base_score=base_score,
            agreement_bonus=agreement_bonus,
            final_score=final_score,
            component_scores={
                'trend_alignment': trend_score,
                'structure_confluence': structure_score,
                'orderblock_proximity': orderblock_score,
                'fvg_alignment': fvg_score,
                'liquidity_context': liquidity_score
            },
            timeframe_agreement=await self._get_timeframe_agreement(timeframe_analyses),
            confidence_level=self._get_confidence_level(final_score)
        )

    async def _calculate_trend_alignment_score(self, timeframe_analyses: Dict) -> float:
        """
        Calculate trend alignment score across timeframes
        """
        total_weight = 0
        aligned_weight = 0
        primary_trend = None

        # Determine primary trend from highest timeframe
        for timeframe in ['D1', 'H4', 'H1', 'M15']:
            if timeframe in timeframe_analyses:
                analysis = timeframe_analyses[timeframe]
                trend = analysis.get('trend_direction')

                if primary_trend is None and trend != 'neutral':
                    primary_trend = trend

                weight = self.timeframe_weights.get(timeframe, 1)
                total_weight += weight

                # Add weight if trend aligns with primary trend
                if trend == primary_trend:
                    aligned_weight += weight
                elif trend == 'neutral':
                    aligned_weight += weight * 0.5  # Neutral contributes 50%

        if total_weight == 0:
            return 0.0

        alignment_ratio = aligned_weight / total_weight
        return alignment_ratio * 100.0

    async def _calculate_structure_confluence_score(self, timeframe_analyses: Dict) -> float:
        """
        Calculate structure confluence across timeframes (BOS/CHoCH alignment)
        """
        structure_signals = []

        for timeframe, analysis in timeframe_analyses.items():
            structure_data = analysis.get('market_structure', {})

            # BOS signals
            bos_signals = structure_data.get('bos_signals', [])
            for bos in bos_signals:
                if bos.get('confirmed'):
                    structure_signals.append({
                        'type': 'bos',
                        'direction': bos['direction'],
                        'timeframe': timeframe,
                        'strength': bos.get('strength', 50),
                        'weight': self.timeframe_weights.get(timeframe, 1)
                    })

            # CHoCH signals
            choch_signals = structure_data.get('choch_signals', [])
            for choch in choch_signals:
                if choch.get('confirmed'):
                    structure_signals.append({
                        'type': 'choch',
                        'direction': choch['direction'],
                        'timeframe': timeframe,
                        'strength': choch.get('strength', 50),
                        'weight': self.timeframe_weights.get(timeframe, 1)
                    })

        if not structure_signals:
            return 0.0

        # Calculate confluence based on signal alignment
        return self._calculate_signal_alignment(structure_signals)

    async def _calculate_orderblock_proximity_score(self, symbol: str, timeframe_analyses: Dict) -> float:
        """
        Calculate order block proximity and validation score
        """
        current_price = await self._get_current_price(symbol)
        orderblock_scores = []

        for timeframe, analysis in timeframe_analyses.items():
            orderblocks = analysis.get('order_blocks', [])

            for ob in orderblocks:
                if not ob.get('is_active'):
                    continue

                # Calculate distance from current price
                distance_pips = abs(current_price - ob['price']) / self._get_pip_value(symbol)

                # Score based on proximity (closer = higher score)
                proximity_score = max(0, 100 - (distance_pips / 10))  # 10 pips = 90% score

                # Weight by timeframe and order block strength
                weight = self.timeframe_weights.get(timeframe, 1)
                strength = ob.get('strength', 50)

                weighted_score = proximity_score * (strength / 100) * weight
                orderblock_scores.append(weighted_score)

        if not orderblock_scores:
            return 0.0

        # Return weighted average
        return sum(orderblock_scores) / len(orderblock_scores)

    async def _calculate_fvg_alignment_score(self, symbol: str, timeframe_analyses: Dict) -> float:
        """
        Calculate Fair Value Gap alignment score
        """
        current_price = await self._get_current_price(symbol)
        fvg_scores = []

        for timeframe, analysis in timeframe_analyses.items():
            fvgs = analysis.get('fair_value_gaps', [])

            for fvg in fvgs:
                if not fvg.get('is_active'):
                    continue

                # Check if current price is within or near FVG
                fvg_top = fvg['top_price']
                fvg_bottom = fvg['bottom_price']

                if fvg_bottom <= current_price <= fvg_top:
                    # Price is within FVG - perfect score
                    score = 100.0
                else:
                    # Calculate distance to nearest FVG boundary
                    distance_to_fvg = min(
                        abs(current_price - fvg_top),
                        abs(current_price - fvg_bottom)
                    )
                    distance_pips = distance_to_fvg / self._get_pip_value(symbol)

                    # Score decreases with distance
                    score = max(0, 100 - (distance_pips / 5))  # 5 pips = 80% score

                # Weight by timeframe and FVG quality
                weight = self.timeframe_weights.get(timeframe, 1)
                quality = fvg.get('quality_score', 50)

                weighted_score = score * (quality / 100) * weight
                fvg_scores.append(weighted_score)

        if not fvg_scores:
            return 0.0

        return sum(fvg_scores) / len(fvg_scores)

    async def _calculate_liquidity_context_score(self, symbol: str, timeframe_analyses: Dict) -> float:
        """
        Calculate liquidity context and sweep analysis score
        """
        current_price = await self._get_current_price(symbol)
        liquidity_scores = []

        for timeframe, analysis in timeframe_analyses.items():
            liquidity_data = analysis.get('liquidity_analysis', {})

            # Check for liquidity sweeps
            recent_sweeps = liquidity_data.get('recent_sweeps', [])
            for sweep in recent_sweeps:
                if sweep.get('confirmed'):
                    # Score based on sweep quality and recency
                    recency_score = max(0, 100 - (sweep.get('candles_ago', 0) * 5))
                    quality_score = sweep.get('quality', 50)

                    weight = self.timeframe_weights.get(timeframe, 1)
                    weighted_score = (recency_score + quality_score) / 2 * weight
                    liquidity_scores.append(weighted_score)

            # Check for liquidity pools
            liquidity_pools = liquidity_data.get('liquidity_pools', [])
            for pool in liquidity_pools:
                distance_pips = abs(current_price - pool['price']) / self._get_pip_value(symbol)

                # Score based on proximity to liquidity
                proximity_score = max(0, 100 - (distance_pips / 20))  # 20 pips = 50% score
                strength_score = pool.get('strength', 50)

                weight = self.timeframe_weights.get(timeframe, 1)
                weighted_score = (proximity_score + strength_score) / 2 * weight
                liquidity_scores.append(weighted_score)

        if not liquidity_scores:
            return 50.0  # Neutral score when no liquidity data

        return sum(liquidity_scores) / len(liquidity_scores)

    async def _calculate_agreement_bonus(self, timeframe_analyses: Dict) -> float:
        """
        Calculate bonus score for timeframe agreement
        """
        agreements = []

        # Check trend agreement
        trends = [analysis.get('trend_direction') for analysis in timeframe_analyses.values()]
        trend_agreement = len(set(trend for trend in trends if trend != 'neutral'))

        if trend_agreement == 1:  # All agree on direction
            agreements.append('trend')

        # Check structure agreement
        structure_directions = []
        for analysis in timeframe_analyses.values():
            structure = analysis.get('market_structure', {})
            if structure.get('overall_bias') != 'neutral':
                structure_directions.append(structure['overall_bias'])

        if len(set(structure_directions)) == 1 and structure_directions:
            agreements.append('structure')

        # Check signal agreement across timeframes
        signal_count = len([a for a in timeframe_analyses.values() if a.get('has_signal')])
        total_timeframes = len(timeframe_analyses)

        # Apply bonuses based on agreement level
        bonus = 0.0

        if signal_count >= 2:
            bonus += self.agreement_bonuses['two_timeframes']
        if signal_count >= 3:
            bonus += self.agreement_bonuses['three_timeframes']
        if signal_count == total_timeframes:
            bonus += self.agreement_bonuses['four_timeframes']

        # Perfect alignment bonus
        if len(agreements) >= 2 and signal_count == total_timeframes:
            bonus += self.agreement_bonuses['perfect_alignment']

        return bonus

    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level based on score"""
        if score >= PERFECT_CONFLUENCE_THRESHOLD:
            return "exceptional"
        elif score >= HIGH_CONFLUENCE_THRESHOLD:
            return "high"
        elif score >= MIN_CONFLUENCE_SCORE:
            return "acceptable"
        else:
            return "insufficient"
```

## Asset-Specific Timeframe Settings

### Forex Major Pairs Configuration

```yaml
# Forex major pairs timeframe settings
forex_major:
  primary_timeframe: "H1"
  analysis_timeframes: ["M15", "H1", "H4", "D1"]
  trend_timeframes: ["H1", "H4", "D1"]

  # Structure sensitivity by timeframe
  structure_sensitivity:
    M15: "high"     # Sensitive to short-term structure changes
    H1: "medium"    # Balanced structure detection
    H4: "low"       # Only major structure changes
    D1: "very_low"  # Only significant structure shifts

  # Confluence requirements
  min_timeframes_for_signal: 2
  preferred_confluence_score: 75.0

  # Session-specific adjustments
  session_adjustments:
    london_open:
      timeframe_weights:
        H1: 1.2  # Increase H1 weight during London open
        H4: 1.1

    new_york_open:
      timeframe_weights:
        H1: 1.3  # Higher H1 weight during NY open
        M15: 0.8 # Reduce M15 noise during high activity

  # Volatility-based timeframe selection
  volatility_adjustments:
    low_volatility:
      primary_timeframe: "H4"  # Use higher timeframe when volatility is low
      reduce_m15_weight: 0.5

    high_volatility:
      primary_timeframe: "M15" # Use lower timeframe when volatility is high
      increase_m15_weight: 1.5
```

### Commodities Configuration

```yaml
# Commodities (Gold, Silver, Oil) timeframe settings
commodities:
  primary_timeframe: "H4"     # Higher timeframe due to volatility
  analysis_timeframes: ["H1", "H4", "D1", "W1"]
  trend_timeframes: ["H4", "D1", "W1"]

  structure_sensitivity:
    H1: "medium"
    H4: "high"      # Primary structure detection
    D1: "medium"
    W1: "low"

  # Gold-specific settings
  XAUUSD:
    confluence_requirements:
      min_score: 70.0           # Higher threshold due to volatility
      min_timeframes: 3         # Require more timeframe agreement

    timeframe_weights:
      W1: 4   # Weekly trend very important for gold
      D1: 3
      H4: 2
      H1: 1

    # Economic event considerations
    event_adjustments:
      fomc_days:
        reduce_all_weights: 0.7  # Reduce confidence during FOMC
        avoid_trading: true

      nfp_days:
        increase_d1_weight: 1.3
        reduce_h1_weight: 0.8

  # Silver follows gold but with adjustments
  XAGUSD:
    inherits: "XAUUSD"
    confluence_requirements:
      min_score: 72.0           # Even higher due to higher volatility

  # Oil-specific settings
  XBRUSD:
    primary_timeframe: "H4"
    timeframe_weights:
      D1: 3
      H4: 2.5  # Slightly higher H4 weight
      H1: 1

    # Oil inventory considerations
    weekly_inventory:
      day: "wednesday"
      time: "15:30"
      adjustment: "increase_d1_weight"
```

### Cryptocurrency Configuration

```yaml
# Cryptocurrency timeframe settings
crypto:
  primary_timeframe: "H1"
  analysis_timeframes: ["M15", "H1", "H4", "D1"]
  trend_timeframes: ["H1", "H4", "D1"]

  structure_sensitivity:
    M15: "very_high"    # Crypto moves fast, capture quick structure changes
    H1: "high"
    H4: "medium"
    D1: "low"

  # Bitcoin-specific settings
  BTCUSD:
    confluence_requirements:
      min_score: 65.0           # Lower threshold due to 24/7 nature
      min_timeframes: 2

    timeframe_weights:
      D1: 2.5   # Slightly lower daily weight
      H4: 2
      H1: 1.5   # Higher H1 weight
      M15: 0.8

    # Weekend adjustments (lower volume)
    weekend_adjustments:
      reduce_all_weights: 0.8
      increase_min_score: 70.0

  # Ethereum follows Bitcoin with correlation consideration
  ETHUSD:
    inherits: "BTCUSD"
    correlation_with_btc: 0.75

    # Ethereum-specific events
    eth2_events:
      increase_d1_weight: 1.4
      increase_min_score: 70.0
```

### Index Configuration

```yaml
# Stock index timeframe settings
indices:
  primary_timeframe: "H1"
  analysis_timeframes: ["M15", "H1", "H4", "D1"]
  trend_timeframes: ["H1", "H4", "D1"]

  # Cash market vs futures considerations
  market_hours_adjustment:
    during_cash_hours:
      increase_h1_weight: 1.3
      increase_m15_weight: 1.2

    outside_cash_hours:
      reduce_m15_weight: 0.6
      increase_h4_weight: 1.2

  # US30 (Dow Jones) specific
  US30:
    confluence_requirements:
      min_score: 70.0
      min_timeframes: 2

    # Economic calendar integration
    economic_events:
      high_impact:
        - "NFP"
        - "FOMC"
        - "GDP"
        - "inflation_data"

      event_adjustments:
        before_event: "increase_d1_weight"
        during_event: "avoid_trading"
        after_event: "increase_h1_weight"

  # European indices
  GER40:
    market_hours: "08:00-16:30"  # XETRA hours
    timezone: "CET"

    ecb_adjustments:
      ecb_days: "increase_d1_weight"
      european_session: "increase_h1_weight"
```

## Multi-Timeframe Analysis Engine

### Core Analysis Engine Implementation

```python
class MultiTimeframeAnalysisEngine:
    """
    Comprehensive multi-timeframe analysis engine
    """

    def __init__(self, config):
        self.config = config
        self.confluence_scorer = MultiTimeframeConfluenceScorer(config)
        self.cache = TimeframeAnalysisCache()

        # Asset-specific configurations
        self.asset_configs = self._load_asset_configurations()

    async def analyze_symbol(self, symbol: str) -> MultiTimeframeAnalysisResult:
        """
        Complete multi-timeframe analysis for symbol
        """
        asset_class = self._get_asset_class(symbol)
        asset_config = self.asset_configs.get(asset_class, {})

        # Get timeframes for analysis
        analysis_timeframes = asset_config.get('analysis_timeframes', ['M15', 'H1', 'H4', 'D1'])

        # Analyze each timeframe
        timeframe_analyses = {}

        for timeframe in analysis_timeframes:
            # Check cache first
            cached_result = await self.cache.get(symbol, timeframe)

            if cached_result and not self._is_cache_stale(cached_result, timeframe):
                timeframe_analyses[timeframe] = cached_result
            else:
                # Perform fresh analysis
                analysis = await self._analyze_timeframe(symbol, timeframe, asset_config)
                timeframe_analyses[timeframe] = analysis

                # Cache the result
                await self.cache.set(symbol, timeframe, analysis)

        # Calculate confluence score
        confluence_result = await self.confluence_scorer.calculate_confluence_score(
            symbol, timeframe_analyses
        )

        # Determine overall signal
        overall_signal = await self._determine_overall_signal(
            symbol, timeframe_analyses, confluence_result, asset_config
        )

        return MultiTimeframeAnalysisResult(
            symbol=symbol,
            asset_class=asset_class,
            timeframe_analyses=timeframe_analyses,
            confluence_result=confluence_result,
            overall_signal=overall_signal,
            analysis_timestamp=datetime.utcnow()
        )

    async def _analyze_timeframe(self, symbol: str, timeframe: str, asset_config: Dict) -> TimeframeAnalysis:
        """
        Analyze single timeframe for symbol
        """
        # Get market data
        market_data = await self._get_market_data(symbol, timeframe)

        # Get timeframe-specific settings
        tf_settings = TIMEFRAME_SETTINGS.get(timeframe, TIMEFRAME_SETTINGS['H1'])

        # 1. Trend Analysis
        trend_analysis = await self._analyze_trend(market_data, tf_settings)

        # 2. Market Structure Analysis
        structure_analysis = await self._analyze_market_structure(market_data, tf_settings)

        # 3. Order Block Detection
        orderblock_analysis = await self._detect_order_blocks(market_data, tf_settings)

        # 4. Fair Value Gap Detection
        fvg_analysis = await self._detect_fair_value_gaps(market_data, tf_settings)

        # 5. Liquidity Analysis
        liquidity_analysis = await self._analyze_liquidity(market_data, tf_settings)

        # 6. Support/Resistance Levels
        sr_analysis = await self._analyze_support_resistance(market_data, tf_settings)

        return TimeframeAnalysis(
            symbol=symbol,
            timeframe=timeframe,
            trend_analysis=trend_analysis,
            structure_analysis=structure_analysis,
            orderblock_analysis=orderblock_analysis,
            fvg_analysis=fvg_analysis,
            liquidity_analysis=liquidity_analysis,
            sr_analysis=sr_analysis,
            analysis_timestamp=datetime.utcnow()
        )

    async def _analyze_trend(self, market_data: pd.DataFrame, settings: Dict) -> TrendAnalysis:
        """
        Comprehensive trend analysis for timeframe
        """
        # Multiple trend indicators
        ema_20 = market_data['close'].ewm(span=20).mean()
        ema_50 = market_data['close'].ewm(span=50).mean()
        ema_200 = market_data['close'].ewm(span=200).mean()

        # Trend strength calculation
        current_price = market_data['close'].iloc[-1]

        # EMA alignment score
        ema_alignment = 0
        if current_price > ema_20.iloc[-1] > ema_50.iloc[-1] > ema_200.iloc[-1]:
            ema_alignment = 100  # Perfect bullish alignment
        elif current_price < ema_20.iloc[-1] < ema_50.iloc[-1] < ema_200.iloc[-1]:
            ema_alignment = -100  # Perfect bearish alignment
        else:
            # Partial alignment calculation
            alignments = [
                1 if current_price > ema_20.iloc[-1] else -1,
                1 if ema_20.iloc[-1] > ema_50.iloc[-1] else -1,
                1 if ema_50.iloc[-1] > ema_200.iloc[-1] else -1
            ]
            ema_alignment = (sum(alignments) / 3) * 100

        # Trend momentum
        momentum = ((current_price - ema_200.iloc[-1]) / ema_200.iloc[-1]) * 100

        # Determine trend direction
        if ema_alignment > 30:
            trend_direction = "bullish"
        elif ema_alignment < -30:
            trend_direction = "bearish"
        else:
            trend_direction = "neutral"

        return TrendAnalysis(
            direction=trend_direction,
            strength=abs(ema_alignment),
            momentum=momentum,
            ema_alignment=ema_alignment,
            support_level=min(ema_20.iloc[-1], ema_50.iloc[-1]),
            resistance_level=max(ema_20.iloc[-1], ema_50.iloc[-1])
        )

    async def _determine_overall_signal(self, symbol: str, timeframe_analyses: Dict,
                                      confluence_result: ConfluenceResult, asset_config: Dict) -> OverallSignal:
        """
        Determine overall trading signal based on multi-timeframe analysis
        """
        # Check minimum confluence requirements
        min_score = asset_config.get('confluence_requirements', {}).get('min_score', MIN_CONFLUENCE_SCORE)
        min_timeframes = asset_config.get('confluence_requirements', {}).get('min_timeframes', 2)

        if confluence_result.final_score < min_score:
            return OverallSignal(
                signal_type="no_signal",
                direction="neutral",
                confidence=confluence_result.final_score,
                reason=f"Confluence score {confluence_result.final_score:.1f}% below minimum {min_score}%"
            )

        # Count agreeing timeframes
        agreeing_timeframes = len([
            tf for tf, analysis in timeframe_analyses.items()
            if analysis.get('has_signal', False)
        ])

        if agreeing_timeframes < min_timeframes:
            return OverallSignal(
                signal_type="no_signal",
                direction="neutral",
                confidence=confluence_result.final_score,
                reason=f"Only {agreeing_timeframes} timeframes agree, need {min_timeframes}"
            )

        # Determine signal direction from trend alignment
        bullish_weight = 0
        bearish_weight = 0

        for timeframe, analysis in timeframe_analyses.items():
            trend = analysis.get('trend_analysis', {})
            direction = trend.get('direction', 'neutral')
            strength = trend.get('strength', 0)
            weight = self.config['trend_weights'].get(timeframe, 1)

            if direction == 'bullish':
                bullish_weight += strength * weight
            elif direction == 'bearish':
                bearish_weight += strength * weight

        # Determine overall direction
        if bullish_weight > bearish_weight * 1.2:  # 20% bias to avoid neutral
            signal_direction = "bullish"
        elif bearish_weight > bullish_weight * 1.2:
            signal_direction = "bearish"
        else:
            signal_direction = "neutral"

        # Generate signal if direction is clear
        if signal_direction != "neutral":
            return OverallSignal(
                signal_type="trading_signal",
                direction=signal_direction,
                confidence=confluence_result.final_score,
                reason=f"Multi-timeframe confluence: {confluence_result.final_score:.1f}%",
                entry_timeframe=asset_config.get('primary_timeframe', 'H1'),
                confluence_breakdown=confluence_result.component_scores
            )
        else:
            return OverallSignal(
                signal_type="no_signal",
                direction="neutral",
                confidence=confluence_result.final_score,
                reason="No clear directional bias across timeframes"
            )
```

## Performance Optimization

### Caching Strategy

```python
class TimeframeAnalysisCache:
    """
    Intelligent caching system for timeframe analysis
    """

    def __init__(self):
        self.cache = {}
        self.cache_durations = {
            'M15': 300,    # 5 minutes
            'H1': 1800,    # 30 minutes
            'H4': 7200,    # 2 hours
            'D1': 14400    # 4 hours
        }

    async def get(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Get cached analysis if still valid"""
        cache_key = f"{symbol}_{timeframe}"

        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            cache_age = (datetime.utcnow() - cached_data['timestamp']).total_seconds()

            if cache_age < self.cache_durations.get(timeframe, 1800):
                return cached_data['analysis']

        return None

    async def set(self, symbol: str, timeframe: str, analysis: Dict):
        """Cache analysis result"""
        cache_key = f"{symbol}_{timeframe}"

        self.cache[cache_key] = {
            'analysis': analysis,
            'timestamp': datetime.utcnow()
        }

        # Cleanup old cache entries
        await self._cleanup_cache()

    async def _cleanup_cache(self):
        """Remove expired cache entries"""
        current_time = datetime.utcnow()

        expired_keys = []
        for key, data in self.cache.items():
            cache_age = (current_time - data['timestamp']).total_seconds()

            # Extract timeframe from key
            timeframe = key.split('_')[-1]
            max_age = self.cache_durations.get(timeframe, 1800)

            if cache_age > max_age * 2:  # Keep cache for 2x the duration
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]
```

This comprehensive multi-timeframe analysis guide provides all the necessary components for implementing sophisticated timeframe confluence analysis with proper optimization and asset-specific configurations.
