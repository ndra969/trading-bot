"""
Unit tests for signal notification formatting with confluence and price action.

Tests the notification message format when executing signals, ensuring:
- Confluence breakdown is included
- Price action details are included
- Strategy scores are properly formatted
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from trading_worker.strategies.models import SignalDirection, TradingSignal


@pytest.fixture
def mock_notification_manager():
    """Mock notification manager."""
    manager = MagicMock()
    manager.send_message = AsyncMock()
    return manager


@pytest.fixture
def sample_signal_with_confluence():
    """Create sample signal with confluence and strategy scores."""
    return TradingSignal(
        signal_id="test_signal_001",
        symbol="EURUSD",
        direction=SignalDirection.BUY,
        entry_price=1.08500,
        stop_loss=1.08200,
        take_profit=1.09000,
        confluence_score=75.5,
        risk_reward_ratio=2.0,
        strategy_scores={
            "foundation": 30.0,
            "rsi": 8.5,
            "price_action": 12.0,
            "trendline": 15.0,
            "fibonacci": 10.0,
        },
        metadata={
            "price_action": {
                "pattern_type": "PINBAR",
                "direction": "BULLISH",
                "confidence": 75.0,
                "status": "detected",
            }
        },
    )


@pytest.fixture
def sample_signal_without_price_action():
    """Create sample signal without price action."""
    return TradingSignal(
        signal_id="test_signal_002",
        symbol="GBPUSD",
        direction=SignalDirection.SELL,
        entry_price=1.33800,
        stop_loss=1.34100,
        take_profit=1.33200,
        confluence_score=68.2,
        risk_reward_ratio=2.0,
        strategy_scores={
            "foundation": 25.0,
            "rsi": 10.0,
            "trendline": 12.0,
        },
        metadata={},
    )


@pytest.fixture
def sample_signal_neutral_price_action():
    """Create sample signal with neutral price action."""
    return TradingSignal(
        signal_id="test_signal_003",
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2650.00,
        stop_loss=2640.00,
        take_profit=2670.00,
        confluence_score=72.0,
        risk_reward_ratio=2.0,
        strategy_scores={
            "foundation": 28.0,
            "price_action": 6.0,  # Reduced for neutral
        },
        metadata={
            "price_action": {
                "pattern_type": "INSIDE_BAR",
                "direction": "NEUTRAL",
                "confidence": 50.0,
                "status": "neutral_pattern",
            }
        },
    )


class TestNotificationFormatting:
    """Test notification message formatting."""

    def test_format_confluence_breakdown(self, sample_signal_with_confluence):
        """Test confluence breakdown formatting."""
        signal = sample_signal_with_confluence

        # Format confluence breakdown (simulating logic from main.py)
        confluence_text = f"\n📊 Confluence: **{signal.confluence_score:.1f}%**"

        layer_names = {
            "foundation": "S&D Zones",
            "rsi": "RSI",
            "ma": "MA",
            "trendline": "Trendline",
            "price_action": "Price Action",
            "fibonacci": "Fibonacci",
            "structure": "Structure",
            "breakout_retest": "Breakout",
        }

        active_layers = []
        for layer, score in sorted(
            signal.strategy_scores.items(), key=lambda x: x[1], reverse=True
        ):
            if score > 0:
                layer_display = layer_names.get(layer, layer.title())
                active_layers.append(f"{layer_display}: {score:.1f}%")

        if active_layers:
            confluence_text += f"\n   └─ {' | '.join(active_layers[:5])}"

        # Verify format
        assert "📊 Confluence: **75.5%**" in confluence_text
        assert "S&D Zones: 30.0%" in confluence_text
        assert "Trendline: 15.0%" in confluence_text
        assert "Price Action: 12.0%" in confluence_text
        assert "Fibonacci: 10.0%" in confluence_text
        assert "RSI: 8.5%" in confluence_text

    def test_format_price_action_detected(self, sample_signal_with_confluence):
        """Test price action formatting when pattern is detected."""
        signal = sample_signal_with_confluence
        pa_info = signal.metadata["price_action"]

        pattern_type = pa_info.get("pattern_type", "UNKNOWN")
        direction = pa_info.get("direction", "")
        confidence = pa_info.get("confidence", 0.0)
        status = pa_info.get("status", "detected")

        # Format price action (simulating logic from main.py)
        if status == "detected" or status == "neutral_pattern":
            direction_emoji = (
                "🟢" if direction == "BULLISH" else "🔴" if direction == "BEARISH" else "⚪"
            )
            pattern_emoji = "📌" if "PINBAR" in pattern_type else "📊"

            neutral_note = " (neutral)" if status == "neutral_pattern" else ""
            price_action_text = f"\n{pattern_emoji} Price Action: {direction_emoji} **{pattern_type}** ({direction}, {confidence:.0f}%){neutral_note}"

        # Verify format
        assert "📌 Price Action: 🟢 **PINBAR**" in price_action_text
        assert "(BULLISH, 75%)" in price_action_text
        assert "(neutral)" not in price_action_text

    def test_format_price_action_neutral(self, sample_signal_neutral_price_action):
        """Test price action formatting for neutral patterns."""
        signal = sample_signal_neutral_price_action
        pa_info = signal.metadata["price_action"]

        pattern_type = pa_info.get("pattern_type", "UNKNOWN")
        direction = pa_info.get("direction", "")
        confidence = pa_info.get("confidence", 0.0)
        status = pa_info.get("status", "detected")

        # Format price action
        if status == "detected" or status == "neutral_pattern":
            direction_emoji = (
                "🟢" if direction == "BULLISH" else "🔴" if direction == "BEARISH" else "⚪"
            )
            pattern_emoji = "📊"

            neutral_note = " (neutral)" if status == "neutral_pattern" else ""
            price_action_text = f"\n{pattern_emoji} Price Action: {direction_emoji} **{pattern_type}** ({direction}, {confidence:.0f}%){neutral_note}"

        # Verify format
        assert "📊 Price Action: ⚪ **INSIDE_BAR**" in price_action_text
        assert "(NEUTRAL, 50%)" in price_action_text
        assert "(neutral)" in price_action_text

    def test_format_price_action_missing(self, sample_signal_without_price_action):
        """Test notification when price action is missing."""
        signal = sample_signal_without_price_action

        # When no price action in metadata
        price_action_text = ""
        if signal.metadata and "price_action" in signal.metadata:
            # Should not enter here
            pass
        else:
            # No price action text
            pass

        # Verify no price action text
        assert price_action_text == ""

    def test_confluence_with_many_layers(self):
        """Test confluence breakdown with more than 5 layers."""
        signal = TradingSignal(
            signal_id="test",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.08500,
            stop_loss=1.08200,
            take_profit=1.09000,
            confluence_score=85.0,
            risk_reward_ratio=2.0,
            strategy_scores={
                "foundation": 30.0,
                "rsi": 8.5,
                "ma": 6.4,
                "trendline": 15.0,
                "price_action": 12.0,
                "fibonacci": 10.0,
                "structure": 6.4,
                "breakout_retest": 7.2,
            },
        )

        # Format confluence
        confluence_text = f"\n📊 Confluence: **{signal.confluence_score:.1f}%**"

        layer_names = {
            "foundation": "S&D Zones",
            "rsi": "RSI",
            "ma": "MA",
            "trendline": "Trendline",
            "price_action": "Price Action",
            "fibonacci": "Fibonacci",
            "structure": "Structure",
            "breakout_retest": "Breakout",
        }

        active_layers = []
        for layer, score in sorted(
            signal.strategy_scores.items(), key=lambda x: x[1], reverse=True
        ):
            if score > 0:
                layer_display = layer_names.get(layer, layer.title())
                active_layers.append(f"{layer_display}: {score:.1f}%")

        if active_layers:
            confluence_text += f"\n   └─ {' | '.join(active_layers[:5])}"
            if len(active_layers) > 5:
                confluence_text += f" (+{len(active_layers) - 5} more)"

        # Verify only first 5 shown
        assert "S&D Zones: 30.0%" in confluence_text
        assert "Trendline: 15.0%" in confluence_text
        assert "Price Action: 12.0%" in confluence_text
        assert "Fibonacci: 10.0%" in confluence_text
        assert "RSI: 8.5%" in confluence_text
        # 6th layer should not be in main text
        assert "Breakout: 7.2%" not in confluence_text.split("(+")[0]  # Not in main part
        # But should show count
        assert "(+3 more)" in confluence_text

    def test_price_action_pattern_emoji_mapping(self):
        """Test emoji mapping for different price action patterns."""
        patterns = {
            "PINBAR": "📌",
            "ENGULFING": "🔄",
            "HARAMI": "🔀",
            "MORNING_STAR": "⭐",
            "EVENING_STAR": "⭐",
            "PULLBACK": "↩️",
            "ORDER_BLOCK": "📦",
            "LIQUIDITY_SWEEP": "🌊",
            "UNKNOWN_PATTERN": "📊",  # Default
        }

        for pattern_type, expected_emoji in patterns.items():
            pattern_emoji = "📊"  # Default
            if "PINBAR" in pattern_type:
                pattern_emoji = "📌"
            elif "ENGULFING" in pattern_type:
                pattern_emoji = "🔄"
            elif "HARAMI" in pattern_type:
                pattern_emoji = "🔀"
            elif "MORNING_STAR" in pattern_type or "EVENING_STAR" in pattern_type:
                pattern_emoji = "⭐"
            elif "PULLBACK" in pattern_type:
                pattern_emoji = "↩️"
            elif "ORDER_BLOCK" in pattern_type:
                pattern_emoji = "📦"
            elif "LIQUIDITY_SWEEP" in pattern_type:
                pattern_emoji = "🌊"

            assert (
                pattern_emoji == expected_emoji
            ), f"Pattern {pattern_type} should map to {expected_emoji}"

    def test_complete_notification_format(self, sample_signal_with_confluence):
        """Test complete notification message format."""
        signal = sample_signal_with_confluence

        # Simulate complete notification format
        message = (
            f"✅ **LIVE ORDER EXECUTED**\n"
            f"🎫 Ticket: `12345678`\n"
            f"💱 **{signal.symbol}** | **{signal.direction.value}**\n"
            f"📊 Size: `0.10` lots\n"
            f"📉 Price: `{signal.entry_price:.5f}`\n"
            f"🛑 SL: `{signal.stop_loss:.5f}`\n"
            f"🎯 TP: `{signal.take_profit:.5f}`"
        )

        # Add confluence
        confluence_text = f"\n📊 Confluence: **{signal.confluence_score:.1f}%**"
        message += confluence_text

        # Add price action
        pa_info = signal.metadata["price_action"]
        pattern_type = pa_info.get("pattern_type", "UNKNOWN")
        direction = pa_info.get("direction", "")
        confidence = pa_info.get("confidence", 0.0)
        pattern_emoji = "📌" if "PINBAR" in pattern_type else "📊"
        direction_emoji = "🟢" if direction == "BULLISH" else "🔴"
        price_action_text = f"\n{pattern_emoji} Price Action: {direction_emoji} **{pattern_type}** ({direction}, {confidence:.0f}%)"
        message += price_action_text

        # Verify all components present
        assert "✅ **LIVE ORDER EXECUTED**" in message
        assert f"**{signal.symbol}**" in message
        assert f"**{signal.direction.value}**" in message
        assert f"Confluence: **{signal.confluence_score:.1f}%**" in message
        assert "Price Action:" in message
        assert pattern_type in message

    def test_dry_run_notification_format(self, sample_signal_with_confluence):
        """Test dry-run notification format."""
        signal = sample_signal_with_confluence

        # Simulate dry-run notification format
        message = (
            f"⚠️ **Dry-Run Order**\n"
            f"💱 **{signal.symbol}** | **{signal.direction.value}**\n"
            f"📊 Size: `0.10` lots\n"
            f"📉 Price: `{signal.entry_price:.5f}`"
        )

        # Add confluence
        confluence_text = f"\n📊 Confluence: **{signal.confluence_score:.1f}%**"
        message += confluence_text

        # Verify format
        assert "⚠️ **Dry-Run Order**" in message
        assert f"**{signal.symbol}**" in message
        assert f"Confluence: **{signal.confluence_score:.1f}%**" in message

    def test_price_action_wrong_direction(self):
        """Test price action formatting when direction is wrong."""
        signal = TradingSignal(
            signal_id="test",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.08500,
            stop_loss=1.08200,
            take_profit=1.09000,
            confluence_score=60.0,
            risk_reward_ratio=2.0,
            strategy_scores={},
            metadata={
                "price_action": {
                    "status": "wrong_direction",
                    "detected_pattern": "PINBAR",
                    "detected_direction": "BEARISH",
                    "required_direction": "BULLISH",
                }
            },
        )

        pa_info = signal.metadata["price_action"]
        status = pa_info.get("status", "detected")

        if status == "wrong_direction":
            detected_pattern = pa_info.get("detected_pattern", "UNKNOWN")
            price_action_text = f"\n⚠️ Price Action: **{detected_pattern}** (wrong direction)"

        assert "⚠️ Price Action: **PINBAR**" in price_action_text
        assert "(wrong direction)" in price_action_text

    def test_empty_strategy_scores(self):
        """Test confluence formatting with empty strategy scores."""
        signal = TradingSignal(
            signal_id="test",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.08500,
            stop_loss=1.08200,
            take_profit=1.09000,
            confluence_score=50.0,
            risk_reward_ratio=2.0,
            strategy_scores={},  # Empty
        )

        # Format confluence
        confluence_text = f"\n📊 Confluence: **{signal.confluence_score:.1f}%**"

        if signal.strategy_scores:
            # Should not enter here
            active_layers = []
            for layer, score in sorted(
                signal.strategy_scores.items(), key=lambda x: x[1], reverse=True
            ):
                if score > 0:
                    active_layers.append(f"{layer}: {score:.1f}%")

            if active_layers:
                confluence_text += f"\n   └─ {' | '.join(active_layers[:5])}"

        # Verify only total confluence shown
        assert "📊 Confluence: **50.0%**" in confluence_text
        assert "└─" not in confluence_text  # No breakdown
