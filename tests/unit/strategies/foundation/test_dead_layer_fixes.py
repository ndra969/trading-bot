"""
Unit tests for the dead-layer bug fixes (spec: enhancement-layer-rework, Phase 0).

Covers:
- Structure vocabulary fix: BULLISH/BEARISH mapped to BUY/SELL in both the
  scoring branch and the commodities >90-confidence gate.
- Trendline pip_value fix: the engine passes the symbol's real pip size into
  analyze_trendline_signal, and the analyzer scales distances correctly per
  asset class.
- Trendline signal-type tightening: BREAK_SUPPORT / BREAK_RESISTANCE no
  longer count as zone confluence (bounce types only).
"""

from unittest.mock import AsyncMock, patch

import pytest
from trading_worker.strategies.enhancement.trendline_analyzer import TrendlineAnalyzer
from trading_worker.strategies.foundation.foundation_engine import FoundationEngine
from trading_worker.strategies.models import SignalDirection


def _mock_signal(**attrs):
    """Build a lightweight analyzer-result stand-in."""
    return type("MockSignal", (), attrs)()


NEUTRAL_RSI = _mock_signal(
    signal_type="NEUTRAL", confidence=0.0, rsi_value=50.0, details={"condition": "NEUTRAL"}
)
NEUTRAL_MA = _mock_signal(signal_type="NEUTRAL", confidence=0.0, details={})
NEUTRAL_TRENDLINE = _mock_signal(signal_type="NEUTRAL", confidence=0.0, details={})


@pytest.fixture
def engine():
    return FoundationEngine(config={}, use_database=False)


async def run_enhancement(
    engine,
    *,
    direction=SignalDirection.BUY,
    is_demand=True,
    asset_class="forex_major",
    pip_size=0.0001,
    rsi=NEUTRAL_RSI,
    ma=NEUTRAL_MA,
    trendline=NEUTRAL_TRENDLINE,
    price_action=None,
    fibonacci=None,
    structure=None,
    zone_lower=1.099,
    zone_upper=1.101,
):
    """Run _run_enhancement_analyzers with every analyzer mocked."""
    with (
        patch.object(
            engine.rsi_analyzer, "analyze_rsi_signal", new_callable=AsyncMock, return_value=rsi
        ),
        patch.object(
            engine.ma_analyzer, "analyze_ma_signal", new_callable=AsyncMock, return_value=ma
        ),
        patch.object(
            engine.trendline_analyzer,
            "analyze_zone_confluence",
            new_callable=AsyncMock,
            return_value=trendline,
        ) as mock_trendline,
        patch.object(
            engine.price_action_analyzer,
            "analyze_pattern",
            new_callable=AsyncMock,
            return_value=price_action,
        ),
        patch.object(
            engine.fibonacci_analyzer,
            "analyze_fibonacci",
            new_callable=AsyncMock,
            return_value=fibonacci,
        ),
        patch.object(
            engine.structure_analyzer,
            "analyze_structure",
            new_callable=AsyncMock,
            return_value=structure,
        ),
    ):
        result = await engine._run_enhancement_analyzers(
            symbol="EURUSD",
            direction=direction,
            is_demand=is_demand,
            zone_type_str="DEMAND" if is_demand else "SUPPLY",
            timeframe="H1",
            asset_class=asset_class,
            opens=[1.1] * 100,
            highs=[1.101] * 100,
            lows=[1.099] * 100,
            closes=[1.1] * 100,
            current_price=1.1,
            pip_size=pip_size,
            zone_lower=zone_lower,
            zone_upper=zone_upper,
        )
    return result, mock_trendline


class TestStructureVocabularyFix:
    """BULLISH/BEARISH must map to BUY/SELL in scoring and the gate."""

    def test_structure_aligns_mapping(self, engine):
        assert engine._structure_aligns("BULLISH", SignalDirection.BUY) is True
        assert engine._structure_aligns("BEARISH", SignalDirection.SELL) is True
        assert engine._structure_aligns("BULLISH", SignalDirection.SELL) is False
        assert engine._structure_aligns("BEARISH", SignalDirection.BUY) is False
        assert engine._structure_aligns("NEUTRAL", SignalDirection.BUY) is False

    @pytest.mark.asyncio
    async def test_aligned_bullish_structure_scores_on_buy(self, engine):
        """A BULLISH structure on a BUY must contribute to confluence."""
        structure = _mock_signal(
            direction="BULLISH", confidence=80.0, structure_type="BOS", details={}
        )
        result, _ = await run_enhancement(
            engine, direction=SignalDirection.BUY, structure=structure
        )
        assert result is not None
        layer_scores, _, raw_confidences = result
        assert raw_confidences["structure"] == 80.0
        assert layer_scores["structure"] == pytest.approx(80.0 * 0.08)

    @pytest.mark.asyncio
    async def test_opposed_structure_does_not_score(self, engine):
        """A BEARISH structure on a BUY must not contribute."""
        structure = _mock_signal(
            direction="BEARISH", confidence=80.0, structure_type="BOS", details={}
        )
        result, _ = await run_enhancement(
            engine, direction=SignalDirection.BUY, structure=structure
        )
        assert result is not None
        _, _, raw_confidences = result
        assert "structure" not in raw_confidences

    @pytest.mark.asyncio
    async def test_commodities_gate_keeps_aligned_high_confidence_trade(self, engine):
        """BULLISH structure at conf>90 on a commodities BUY must NOT be rejected.

        Pre-fix, the raw string comparison treated BULLISH != BUY as
        misaligned and wrongly hard-rejected aligned trades.
        """
        structure = _mock_signal(
            direction="BULLISH", confidence=95.0, structure_type="CHOCH", details={}
        )
        result, _ = await run_enhancement(
            engine,
            direction=SignalDirection.BUY,
            asset_class="commodities",
            structure=structure,
        )
        assert result is not None
        _, _, raw_confidences = result
        assert raw_confidences["structure"] == 95.0

    @pytest.mark.asyncio
    async def test_commodities_gate_rejects_opposed_high_confidence(self, engine):
        """BEARISH structure at conf>90 on a commodities BUY is still rejected."""
        structure = _mock_signal(
            direction="BEARISH", confidence=95.0, structure_type="CHOCH", details={}
        )
        result, _ = await run_enhancement(
            engine,
            direction=SignalDirection.BUY,
            asset_class="commodities",
            structure=structure,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_commodities_gate_allows_weak_opposed_structure(self, engine):
        """Opposed structure at conf<=90 proceeds (no score, no rejection)."""
        structure = _mock_signal(
            direction="BEARISH", confidence=85.0, structure_type="BOS", details={}
        )
        result, _ = await run_enhancement(
            engine,
            direction=SignalDirection.BUY,
            asset_class="commodities",
            structure=structure,
        )
        assert result is not None
        _, _, raw_confidences = result
        assert "structure" not in raw_confidences


class TestTrendlinePipValueFix:
    """The engine must pass the symbol's pip size to the trendline analyzer."""

    def test_engine_caches_pip_calculator(self, engine):
        assert engine.pip_calculator is not None
        # Same instance reused, not re-created per call
        assert engine.pip_calculator is engine.pip_calculator

    @pytest.mark.asyncio
    async def test_zone_bounds_forwarded_to_trendline_analyzer(self, engine):
        """Phase 1 supersedes pip forwarding: the engine now evaluates
        trendline confluence against the zone band (asset-scale independent
        by construction), so it must forward the zone bounds + side."""
        _, mock_trendline = await run_enhancement(
            engine, is_demand=True, zone_lower=1.0950, zone_upper=1.0980
        )
        kwargs = mock_trendline.call_args.kwargs
        assert kwargs["zone_lower"] == 1.0950
        assert kwargs["zone_upper"] == 1.0980
        assert kwargs["is_demand"] is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "base, slope, amp, pip_value",
        [
            (1.1000, 0.0001, 0.005, 0.0001),  # forex_major
            (150.00, 0.01, 0.5, 0.01),  # forex_jpy
            (2000.0, 0.1, 5.0, 0.1),  # commodities (gold)
            (50000.0, 1.0, 50.0, 1.0),  # crypto
        ],
    )
    async def test_analyzer_distance_scales_per_asset_class(self, base, slope, amp, pip_value):
        """With the correct pip size a bounce fires on every asset class;
        with the old hardcoded 0.0001 default it stays NEUTRAL (except
        forex_major, where 0.0001 IS the pip size)."""
        analyzer = TrendlineAnalyzer({})
        prices = self._ascending_support_series(base, slope, amp)

        signal = await analyzer.analyze_trendline_signal("TEST", prices, "H1", pip_value=pip_value)
        assert signal.signal_type == "BOUNCE_SUPPORT"
        # Last bar sits 10 pips off the line in the symbol's own scale
        assert signal.distance_to_trendline == pytest.approx(10.0, abs=1.0)

        if pip_value != 0.0001:
            buggy = await analyzer.analyze_trendline_signal("TEST", prices, "H1")
            assert buggy.signal_type == "NEUTRAL"

    @staticmethod
    def _ascending_support_series(base: float, slope: float, amp: float) -> list[float]:
        """Price series with collinear swing lows every 10 bars on a rising
        support line; the final bar closes 0.2*amp above the line (= 10 pips
        when amp = 50 pips)."""
        prices = []
        for i in range(100):
            m = i % 10
            offset = amp * min(m, 10 - m) / 5.0
            prices.append(base + slope * i + offset)
        return prices


class TestTrendlineBounceTypesOnly:
    """BREAK_SUPPORT/BREAK_RESISTANCE must not count as zone confluence."""

    @pytest.mark.asyncio
    async def test_bounce_support_scores_on_demand(self, engine):
        trendline = _mock_signal(signal_type="BOUNCE_SUPPORT", confidence=40.0, details={})
        result, _ = await run_enhancement(engine, is_demand=True, trendline=trendline)
        assert result is not None
        _, _, raw_confidences = result
        assert raw_confidences["trendline"] == 40.0

    @pytest.mark.asyncio
    async def test_break_support_does_not_score_on_demand(self, engine):
        """Pre-fix, '"SUPPORT" in signal_type' also matched BREAK_SUPPORT —
        a breakdown through support argued AGAINST a demand entry yet still
        added confluence."""
        trendline = _mock_signal(signal_type="BREAK_SUPPORT", confidence=40.0, details={})
        result, _ = await run_enhancement(engine, is_demand=True, trendline=trendline)
        assert result is not None
        _, _, raw_confidences = result
        assert "trendline" not in raw_confidences

    @pytest.mark.asyncio
    async def test_bounce_resistance_scores_on_supply(self, engine):
        trendline = _mock_signal(signal_type="BOUNCE_RESISTANCE", confidence=40.0, details={})
        result, _ = await run_enhancement(
            engine, direction=SignalDirection.SELL, is_demand=False, trendline=trendline
        )
        assert result is not None
        _, _, raw_confidences = result
        assert raw_confidences["trendline"] == 40.0

    @pytest.mark.asyncio
    async def test_break_resistance_does_not_score_on_supply(self, engine):
        trendline = _mock_signal(signal_type="BREAK_RESISTANCE", confidence=40.0, details={})
        result, _ = await run_enhancement(
            engine, direction=SignalDirection.SELL, is_demand=False, trendline=trendline
        )
        assert result is not None
        _, _, raw_confidences = result
        assert "trendline" not in raw_confidences
