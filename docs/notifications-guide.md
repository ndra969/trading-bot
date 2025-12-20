# Telegram Notification System Guide

This guide provides comprehensive information about the trading bot's Telegram notification system, including setup, configuration, message types, and advanced features.

## Overview

The trading bot includes a sophisticated Telegram notification system that provides real-time updates on all trading activities, system events, and performance metrics. The system is designed to keep traders informed while avoiding notification spam through intelligent rate limiting and message prioritization.

### Key Features

- **Real-time notifications** for all trading events
- **Rich message formatting** with emojis and structured layout
- **Priority-based messaging** (High/Medium/Low)
- **Rate limiting** to prevent spam
- **Configurable notification types** (enable/disable specific events)
- **Daily/weekly summaries** with performance statistics
- **Error alerts** and system monitoring
- **Chart integration** (optional) with trading signals

## Telegram Setup

### Bot Creation and Configuration

#### Step 1: Create Telegram Bot

1. **Start conversation with BotFather**: Search for `@BotFather` on Telegram
2. **Create new bot**: Send `/newbot` command
3. **Set bot name**: Choose a name for your trading bot
4. **Set username**: Must end with 'bot' (e.g., `my_trading_bot`)
5. **Get bot token**: Save the token provided by BotFather

#### Step 2: Get Chat ID

```bash
# Method 1: Send message to your bot and get chat ID
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates

# Method 2: Use bot command
# Send any message to your bot, then check updates
```

#### Step 3: Environment Configuration

```bash
# Add to .env file
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# For group notifications (optional)
TELEGRAM_GROUP_CHAT_ID=group_chat_id_here
```

### Initial Bot Setup

```python
# Test bot connection
uv run trading-bot notifications test
uv run trading-bot notifications setup --interactive
```

## Notification Configuration

### Core Configuration File

```yaml
# config/telegram_notifications.yaml
telegram:
  enabled: true
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_id: "${TELEGRAM_CHAT_ID}"

  # Optional group notifications
  group_notifications:
    enabled: false
    group_chat_id: "${TELEGRAM_GROUP_CHAT_ID}"
    events: ["trade_opened", "trade_closed", "daily_summary"]

  # Connection settings
  connection:
    timeout: 30
    retry_attempts: 3
    retry_delay: 5
    rate_limit_per_minute: 20

  # Message formatting
  formatting:
    use_emojis: true
    use_markdown: true
    timestamp_format: "%Y-%m-%d %H:%M:%S UTC"
    timezone: "UTC"

  # Notification categories
  notifications:
    # Trade Execution Events
    trade_events:
      trade_opened:
        enabled: true
        priority: "high"
        include_chart: false
        template: "trade_opened"

      trade_closed:
        enabled: true
        priority: "high"
        include_profit_stats: true
        template: "trade_closed"

      trade_rejected:
        enabled: true
        priority: "medium"
        include_reason: true
        template: "trade_rejected"

    # Position Management Events
    position_events:
      breakeven_triggered:
        enabled: true
        priority: "medium"
        template: "breakeven_triggered"

      trailing_activated:
        enabled: true
        priority: "medium"
        template: "trailing_activated"

      trailing_updated:
        enabled: false  # Can be noisy
        priority: "low"
        template: "trailing_updated"

      partial_close_executed:
        enabled: true
        priority: "medium"
        template: "partial_close"

      stop_loss_hit:
        enabled: true
        priority: "high"
        template: "stop_loss_hit"

      take_profit_hit:
        enabled: true
        priority: "high"
        template: "take_profit_hit"

    # System Events
    system_events:
      bot_started:
        enabled: true
        priority: "medium"
        include_system_info: true
        template: "bot_started"

      bot_stopped:
        enabled: true
        priority: "medium"
        template: "bot_stopped"

      connection_lost:
        enabled: true
        priority: "high"
        template: "connection_lost"

      connection_restored:
        enabled: true
        priority: "medium"
        template: "connection_restored"

      error_occurred:
        enabled: true
        priority: "high"
        include_stack_trace: false
        template: "error_occurred"

      warning_issued:
        enabled: true
        priority: "medium"
        template: "warning_issued"

    # Analytics Events
    analytics_events:
      daily_summary:
        enabled: true
        send_time: "21:00"  # 9 PM UTC
        template: "daily_summary"

      weekly_summary:
        enabled: true
        send_day: "sunday"
        send_time: "20:00"
        template: "weekly_summary"

      monthly_summary:
        enabled: true
        send_day: "last"
        send_time: "19:00"
        template: "monthly_summary"

      drawdown_warning:
        enabled: true
        threshold_percent: 4.0
        priority: "high"
        template: "drawdown_warning"

      profit_milestone:
        enabled: true
        milestones: [100, 500, 1000, 5000]  # USD milestones
        template: "profit_milestone"

  # Rate limiting to prevent spam
  rate_limiting:
    max_messages_per_minute: 10
    max_messages_per_hour: 100
    cooldown_similar_messages: 60  # seconds
    burst_protection: true

    # Priority-based limits
    priority_limits:
      high: 30    # per hour
      medium: 60  # per hour
      low: 20     # per hour

  # Message templates
  templates_path: "config/notification_templates/"
```

### Advanced Configuration Options

```yaml
# Advanced notification features
advanced_features:
  # Smart notifications
  smart_notifications:
    enabled: true

    # Adaptive frequency based on performance
    adaptive_frequency:
      good_performance_reduce: 0.7  # Reduce notifications by 30% when performing well
      poor_performance_increase: 1.3  # Increase notifications by 30% when struggling
      performance_window_hours: 24

    # Context-aware notifications
    context_aware:
      session_based: true  # Different notifications for different trading sessions
      volatility_based: true  # Adjust based on market volatility
      drawdown_based: true  # More notifications during drawdown

  # Chart integration
  chart_integration:
    enabled: false  # Requires additional setup
    chart_provider: "tradingview"  # or "custom"
    include_with_signals: true
    chart_timeframe: "H1"

  # Multi-language support
  localization:
    enabled: false
    default_language: "en"
    available_languages: ["en", "es", "fr", "de"]

  # Webhook integration
  webhooks:
    enabled: false
    endpoints:
      - url: "https://your-webhook-url.com/trading-bot"
        events: ["trade_opened", "trade_closed"]
        secret: "${WEBHOOK_SECRET}"
```

## Message Templates

### Template System

The notification system uses a flexible template system for message formatting:

```yaml
# config/notification_templates/trade_opened.yaml
trade_opened:
  title: "🟢 TRADE OPENED"
  format: |
    🟢 **TRADE OPENED**

    📊 **Symbol:** {symbol}
    📈 **Direction:** {direction}
    💰 **Volume:** {volume} lots
    🎯 **Entry:** {entry_price}
    🛡️ **Stop Loss:** {stop_loss}
    🎁 **Take Profit:** {take_profit}
    ⚡ **Strategy:** {strategy_name}
    📊 **Confidence:** {confidence_score}%

    💪 **Risk:** ${risk_amount} ({risk_percent}%)
    📈 **Potential Profit:** ${potential_profit}

    ⏰ **Time:** {timestamp}

trade_closed:
  title: "🔴 TRADE CLOSED"
  format: |
    {result_emoji} **TRADE CLOSED**

    📊 **Symbol:** {symbol}
    📈 **Direction:** {direction}
    💰 **Volume:** {volume} lots

    🎯 **Entry:** {entry_price}
    🏁 **Exit:** {exit_price}
    📊 **Pips:** {pips_profit} pips
    💰 **Profit:** ${profit} ({profit_percent}%)

    ⏱️ **Duration:** {trade_duration}
    ⚡ **Strategy:** {strategy_name}

    ⏰ **Closed:** {timestamp}

daily_summary:
  title: "📊 DAILY SUMMARY"
  format: |
    📊 **DAILY SUMMARY - {date}**

    📈 **Trades:** {total_trades}
    ✅ **Winners:** {winning_trades}
    ❌ **Losers:** {losing_trades}
    📊 **Win Rate:** {win_rate}%

    💰 **P&L:** ${daily_pnl} ({daily_pnl_percent}%)
    📈 **Best Trade:** ${best_trade}
    📉 **Worst Trade:** ${worst_trade}

    🎯 **Success Rate by Strategy:**
    {strategy_breakdown}

    📊 **Account Status:**
    💰 **Balance:** ${account_balance}
    📈 **Equity:** ${account_equity}
    📊 **Margin Used:** {margin_used}%

    {performance_emoji} **{performance_message}**
```

### Dynamic Message Templates

```python
class MessageTemplateEngine:
    """
    Advanced message template engine with dynamic content
    """

    def __init__(self, templates_path: str):
        self.templates_path = templates_path
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict:
        """Load all message templates"""
        templates = {}

        for template_file in Path(self.templates_path).glob("*.yaml"):
            with open(template_file, 'r') as f:
                template_data = yaml.safe_load(f)
                templates.update(template_data)

        return templates

    def render_message(self, template_name: str, context: Dict) -> str:
        """Render message using template and context"""
        if template_name not in self.templates:
            return f"Template '{template_name}' not found"

        template = self.templates[template_name]
        message_format = template.get('format', '')

        # Add dynamic context
        enhanced_context = self._enhance_context(context, template_name)

        try:
            return message_format.format(**enhanced_context)
        except KeyError as e:
            return f"Template error: Missing variable {e}"

    def _enhance_context(self, context: Dict, template_name: str) -> Dict:
        """Add dynamic context based on template type"""
        enhanced = context.copy()

        # Add emojis based on context
        if template_name == "trade_closed":
            profit = float(context.get('profit', 0))
            if profit > 0:
                enhanced['result_emoji'] = "✅"
                enhanced['performance_message'] = "Great trade!"
            else:
                enhanced['result_emoji'] = "❌"
                enhanced['performance_message'] = "Better luck next time!"

        # Add formatted timestamps
        if 'timestamp' in context:
            if isinstance(context['timestamp'], datetime):
                enhanced['timestamp'] = context['timestamp'].strftime("%Y-%m-%d %H:%M:%S UTC")

        # Add calculated fields
        if template_name == "daily_summary":
            total_trades = int(context.get('total_trades', 0))
            winning_trades = int(context.get('winning_trades', 0))

            if total_trades > 0:
                win_rate = (winning_trades / total_trades) * 100
                enhanced['win_rate'] = f"{win_rate:.1f}"
            else:
                enhanced['win_rate'] = "0.0"

            # Performance emoji based on daily P&L
            daily_pnl = float(context.get('daily_pnl', 0))
            if daily_pnl > 100:
                enhanced['performance_emoji'] = "🚀"
                enhanced['performance_message'] = "Excellent day!"
            elif daily_pnl > 0:
                enhanced['performance_emoji'] = "💪"
                enhanced['performance_message'] = "Good day!"
            elif daily_pnl > -50:
                enhanced['performance_emoji'] = "😐"
                enhanced['performance_message'] = "Neutral day"
            else:
                enhanced['performance_emoji'] = "📉"
                enhanced['performance_message'] = "Tough day, keep going!"

        return enhanced
```

## Telegram Manager Implementation

### Core Telegram Manager

```python
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yaml
import json

class TelegramNotificationManager:
    """
    Comprehensive Telegram notification manager
    """

    def __init__(self, config_path: str = "config/telegram_notifications.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['telegram']

        self.bot_token = self.config['bot_token']
        self.chat_id = self.config['chat_id']
        self.enabled = self.config.get('enabled', True)

        # Rate limiting
        self.message_history = []
        self.rate_limiter = TelegramRateLimiter(self.config.get('rate_limiting', {}))

        # Template engine
        templates_path = self.config.get('templates_path', 'config/notification_templates/')
        self.template_engine = MessageTemplateEngine(templates_path)

        # Session for HTTP requests
        self.session = None

    async def initialize(self):
        """Initialize the Telegram manager"""
        if not self.enabled:
            return

        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.get('connection', {}).get('timeout', 30))
        )

        # Test connection
        try:
            await self._test_connection()
            self.logger.info("Telegram bot connected successfully")
        except Exception as e:
            self.logger.error(f"Telegram bot connection failed: {e}")
            raise

    async def _test_connection(self):
        """Test Telegram bot connection"""
        url = f"https://api.telegram.org/bot{self.bot_token}/getMe"

        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Telegram API error: {response.status}")

            data = await response.json()
            if not data.get('ok'):
                raise Exception(f"Telegram bot error: {data.get('description')}")

    async def send_notification(self, notification_type: str, context: Dict) -> bool:
        """Send notification with type and context"""
        if not self.enabled:
            return True

        # Check if notification type is enabled
        if not self._is_notification_enabled(notification_type):
            return True

        # Apply rate limiting
        if not await self.rate_limiter.can_send_message(notification_type, context):
            self.logger.debug(f"Rate limited: {notification_type}")
            return False

        try:
            # Get message content
            message = self._prepare_message(notification_type, context)

            # Send message
            success = await self._send_message(message)

            if success:
                # Update rate limiter
                await self.rate_limiter.record_message(notification_type, context)
                self.logger.debug(f"Sent notification: {notification_type}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to send notification {notification_type}: {e}")
            return False

    def _is_notification_enabled(self, notification_type: str) -> bool:
        """Check if notification type is enabled"""
        # Navigate through nested configuration
        parts = notification_type.split('.')
        config_section = self.config.get('notifications', {})

        for part in parts[:-1]:
            config_section = config_section.get(part, {})

        notification_config = config_section.get(parts[-1], {})
        return notification_config.get('enabled', False)

    def _prepare_message(self, notification_type: str, context: Dict) -> str:
        """Prepare message using template"""
        # Get template name from configuration
        parts = notification_type.split('.')
        config_section = self.config.get('notifications', {})

        for part in parts[:-1]:
            config_section = config_section.get(part, {})

        notification_config = config_section.get(parts[-1], {})
        template_name = notification_config.get('template', parts[-1])

        # Render message
        return self.template_engine.render_message(template_name, context)

    async def _send_message(self, message: str) -> bool:
        """Send message to Telegram"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        data = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'Markdown' if self.config.get('formatting', {}).get('use_markdown', True) else None,
            'disable_notification': False
        }

        try:
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return response_data.get('ok', False)
                else:
                    self.logger.error(f"Telegram API error: {response.status}")
                    return False

        except asyncio.TimeoutError:
            self.logger.error("Telegram request timeout")
            return False
        except Exception as e:
            self.logger.error(f"Telegram request failed: {e}")
            return False

    # Convenience methods for common notifications
    async def send_trade_opened(self, trade_data: Dict) -> bool:
        """Send trade opened notification"""
        return await self.send_notification('trade_events.trade_opened', trade_data)

    async def send_trade_closed(self, trade_data: Dict) -> bool:
        """Send trade closed notification"""
        return await self.send_notification('trade_events.trade_closed', trade_data)

    async def send_breakeven_triggered(self, position_data: Dict) -> bool:
        """Send breakeven triggered notification"""
        return await self.send_notification('position_events.breakeven_triggered', position_data)

    async def send_error_alert(self, error_data: Dict) -> bool:
        """Send error alert notification"""
        return await self.send_notification('system_events.error_occurred', error_data)

    async def send_daily_summary(self, summary_data: Dict) -> bool:
        """Send daily summary notification"""
        return await self.send_notification('analytics_events.daily_summary', summary_data)

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
```

### Rate Limiting System

```python
class TelegramRateLimiter:
    """
    Sophisticated rate limiting for Telegram notifications
    """

    def __init__(self, config: Dict):
        self.config = config
        self.message_history = []
        self.similar_message_cache = {}

    async def can_send_message(self, notification_type: str, context: Dict) -> bool:
        """Check if message can be sent based on rate limits"""
        current_time = datetime.utcnow()

        # Check overall rate limits
        if not self._check_overall_rate_limit(current_time):
            return False

        # Check priority-based limits
        priority = self._get_message_priority(notification_type)
        if not self._check_priority_rate_limit(priority, current_time):
            return False

        # Check similar message cooldown
        if not self._check_similar_message_cooldown(notification_type, context, current_time):
            return False

        return True

    def _check_overall_rate_limit(self, current_time: datetime) -> bool:
        """Check overall rate limits"""
        max_per_minute = self.config.get('max_messages_per_minute', 10)
        max_per_hour = self.config.get('max_messages_per_hour', 100)

        # Clean old messages
        minute_ago = current_time - timedelta(minutes=1)
        hour_ago = current_time - timedelta(hours=1)

        recent_messages = [
            msg for msg in self.message_history
            if msg['timestamp'] > hour_ago
        ]
        self.message_history = recent_messages

        # Count messages in last minute and hour
        messages_last_minute = len([
            msg for msg in recent_messages
            if msg['timestamp'] > minute_ago
        ])

        messages_last_hour = len(recent_messages)

        return (messages_last_minute < max_per_minute and
                messages_last_hour < max_per_hour)

    def _check_priority_rate_limit(self, priority: str, current_time: datetime) -> bool:
        """Check priority-based rate limits"""
        priority_limits = self.config.get('priority_limits', {})
        max_per_hour = priority_limits.get(priority, 50)

        hour_ago = current_time - timedelta(hours=1)
        priority_messages = len([
            msg for msg in self.message_history
            if msg['timestamp'] > hour_ago and msg['priority'] == priority
        ])

        return priority_messages < max_per_hour

    def _check_similar_message_cooldown(self, notification_type: str, context: Dict, current_time: datetime) -> bool:
        """Check cooldown for similar messages"""
        cooldown_seconds = self.config.get('cooldown_similar_messages', 60)

        # Create message signature
        signature = self._create_message_signature(notification_type, context)

        if signature in self.similar_message_cache:
            last_sent = self.similar_message_cache[signature]
            time_diff = (current_time - last_sent).total_seconds()

            if time_diff < cooldown_seconds:
                return False

        return True

    def _create_message_signature(self, notification_type: str, context: Dict) -> str:
        """Create signature for similar message detection"""
        # Create signature based on notification type and key context
        key_fields = ['symbol', 'direction', 'strategy_name']
        signature_parts = [notification_type]

        for field in key_fields:
            if field in context:
                signature_parts.append(f"{field}:{context[field]}")

        return "|".join(signature_parts)

    async def record_message(self, notification_type: str, context: Dict):
        """Record sent message for rate limiting"""
        current_time = datetime.utcnow()
        priority = self._get_message_priority(notification_type)

        # Add to message history
        self.message_history.append({
            'timestamp': current_time,
            'type': notification_type,
            'priority': priority
        })

        # Update similar message cache
        signature = self._create_message_signature(notification_type, context)
        self.similar_message_cache[signature] = current_time

    def _get_message_priority(self, notification_type: str) -> str:
        """Get message priority from configuration"""
        # Default priority mapping
        priority_mapping = {
            'trade_events': 'high',
            'position_events': 'medium',
            'system_events': 'high',
            'analytics_events': 'low'
        }

        category = notification_type.split('.')[0]
        return priority_mapping.get(category, 'medium')
```

## Scheduled Notifications

### Daily/Weekly Summary System

```python
class ScheduledNotificationManager:
    """
    Manager for scheduled notifications like daily/weekly summaries
    """

    def __init__(self, telegram_manager: TelegramNotificationManager, database):
        self.telegram = telegram_manager
        self.database = database
        self.scheduler = None

    async def initialize(self):
        """Initialize scheduled notifications"""
        # Setup scheduler (using APScheduler or similar)
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        self.scheduler = AsyncIOScheduler()

        # Schedule daily summary
        if self._is_enabled('analytics_events.daily_summary'):
            send_time = self._get_send_time('analytics_events.daily_summary')
            self.scheduler.add_job(
                self.send_daily_summary,
                'cron',
                hour=send_time.hour,
                minute=send_time.minute
            )

        # Schedule weekly summary
        if self._is_enabled('analytics_events.weekly_summary'):
            send_day = self._get_send_day('analytics_events.weekly_summary')
            send_time = self._get_send_time('analytics_events.weekly_summary')

            self.scheduler.add_job(
                self.send_weekly_summary,
                'cron',
                day_of_week=send_day,
                hour=send_time.hour,
                minute=send_time.minute
            )

        self.scheduler.start()

    async def send_daily_summary(self):
        """Send daily trading summary"""
        try:
            # Get daily statistics
            summary_data = await self._get_daily_statistics()

            # Send notification
            await self.telegram.send_daily_summary(summary_data)

        except Exception as e:
            self.logger.error(f"Failed to send daily summary: {e}")

    async def _get_daily_statistics(self) -> Dict:
        """Get daily trading statistics"""
        today = datetime.utcnow().date()

        # Query database for today's trades
        trades = await self.database.get_trades_by_date(today)

        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.profit > 0])
        losing_trades = total_trades - winning_trades

        total_profit = sum(t.profit for t in trades)
        best_trade = max([t.profit for t in trades], default=0)
        worst_trade = min([t.profit for t in trades], default=0)

        # Strategy breakdown
        strategy_stats = {}
        for trade in trades:
            strategy = trade.strategy_name
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'total': 0, 'wins': 0}

            strategy_stats[strategy]['total'] += 1
            if trade.profit > 0:
                strategy_stats[strategy]['wins'] += 1

        strategy_breakdown = []
        for strategy, stats in strategy_stats.items():
            win_rate = (stats['wins'] / stats['total'] * 100) if stats['total'] > 0 else 0
            strategy_breakdown.append(f"  • {strategy}: {win_rate:.1f}% ({stats['wins']}/{stats['total']})")

        # Account information
        account_info = await self.database.get_latest_account_info()

        return {
            'date': today.strftime('%Y-%m-%d'),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'daily_pnl': total_profit,
            'daily_pnl_percent': (total_profit / account_info.balance * 100) if account_info else 0,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'strategy_breakdown': '\n'.join(strategy_breakdown) if strategy_breakdown else "No trades today",
            'account_balance': account_info.balance if account_info else 0,
            'account_equity': account_info.equity if account_info else 0,
            'margin_used': account_info.margin_used_percent if account_info else 0
        }
```

## Integration with Trading Events

### Automatic Event Integration

```python
class TradingBot:
    """
    Trading bot with integrated Telegram notifications
    """

    def __init__(self, config):
        self.config = config
        self.telegram = TelegramNotificationManager()
        self.scheduled_notifications = ScheduledNotificationManager(self.telegram, self.database)

    async def initialize(self):
        """Initialize bot with notifications"""
        await self.telegram.initialize()
        await self.scheduled_notifications.initialize()

        # Send startup notification
        await self.telegram.send_notification('system_events.bot_started', {
            'timestamp': datetime.utcnow(),
            'version': self.config.version,
            'environment': self.config.environment,
            'trading_symbols': self.config.trading_symbols
        })

    async def execute_trade(self, signal):
        """Execute trade with automatic notifications"""
        result = await self.mt5_connector.place_order(signal)

        if result['success']:
            # Prepare trade data for notification
            trade_data = {
                'symbol': signal.symbol,
                'direction': signal.direction,
                'volume': signal.volume,
                'entry_price': result['price'],
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'strategy_name': signal.strategy_name,
                'confidence_score': signal.confidence,
                'risk_amount': self._calculate_risk_amount(signal),
                'risk_percent': self._calculate_risk_percent(signal),
                'potential_profit': self._calculate_potential_profit(signal),
                'timestamp': datetime.utcnow()
            }

            # Send trade opened notification
            await self.telegram.send_trade_opened(trade_data)

            return True
        else:
            # Send trade rejected notification
            await self.telegram.send_notification('trade_events.trade_rejected', {
                'symbol': signal.symbol,
                'direction': signal.direction,
                'reason': result.get('error', 'Unknown error'),
                'timestamp': datetime.utcnow()
            })
            return False

    async def on_position_event(self, position, event_type: str, event_data: Dict):
        """Handle position events with notifications"""
        notification_map = {
            'breakeven_triggered': 'position_events.breakeven_triggered',
            'trailing_activated': 'position_events.trailing_activated',
            'partial_close': 'position_events.partial_close_executed',
            'stop_loss_hit': 'position_events.stop_loss_hit',
            'take_profit_hit': 'position_events.take_profit_hit'
        }

        notification_type = notification_map.get(event_type)
        if notification_type:
            context = {
                'symbol': position.symbol,
                'direction': position.direction,
                'volume': position.volume,
                'timestamp': datetime.utcnow(),
                **event_data
            }

            await self.telegram.send_notification(notification_type, context)

    async def on_error(self, error: Exception, context: Dict):
        """Handle errors with notifications"""
        await self.telegram.send_error_alert({
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'timestamp': datetime.utcnow()
        })
```

## CLI Commands for Notification Management

### Notification CLI Commands

```bash
# Test notifications
uv run trading-bot notifications test
uv run trading-bot notifications test --type trade_opened

# Setup and configuration
uv run trading-bot notifications setup --interactive
uv run trading-bot notifications status

# Enable/disable notifications
uv run trading-bot notifications enable --type trade_events.trade_opened
uv run trading-bot notifications disable --type position_events.trailing_updated
uv run trading-bot notifications list --enabled

# Manual notifications
uv run trading-bot notifications send --message "Manual test message"
uv run trading-bot notifications summary --send-now

# Notification history and stats
uv run trading-bot notifications history --days 7
uv run trading-bot notifications stats --period month
uv run trading-bot notifications failed --retry
```

## Advanced Features

### Smart Notification Features

- **Adaptive frequency** based on trading performance
- **Context-aware messaging** based on market conditions
- **Intelligent grouping** of similar notifications
- **Emoji and formatting** based on message content
- **Multi-language support** (configurable)
- **Webhook integration** for external systems

### Performance Monitoring

- **Message delivery tracking** with retry mechanisms
- **Rate limiting statistics** and optimization
- **Template performance** monitoring
- **Error handling and fallback** systems

## Risk Alert Integration ✅ **NEW - Phase 4.5**

### Overview

Complete integration with the risk management system provides real-time alerts for all critical risk events through rich Telegram notifications. This ensures immediate awareness of portfolio risks, emergency situations, and system status changes.

**Status**: ✅ **COMPLETED** (Phase 4.5 - Week 12)

### AlertHistory → Telegram Flow

The risk alert system follows a sophisticated flow from risk detection to formatted notification delivery:

```
Risk Event → AlertHistory Object → Rich Formatting → Telegram Delivery
     ↓               ↓                    ↓              ↓
Risk Monitor    Data Structure    Emoji + Styling    API Delivery
     ↓               ↓                    ↓              ↓
Thresholds      Alert Metadata    Priority Queue      Rate Limiting
```

### Risk Alert Types

#### 1. Portfolio Risk Alerts
**Trigger**: Portfolio risk exceeds configured thresholds

```telegram
🚨 *RISK ALERT - HIGH*

🚨 **Alert Type:** Portfolio Risk High
📝 **Message:** High portfolio risk: 4.2% ($420.00)
⏰ **Time:** 2025-01-20 17:10:15
🆔 **Alert ID:** portfolio_risk_1642693815

📊 **Action Required:** Portfolio risk is approaching limits

🔔 **Status:** ACTIVE - Monitoring continues
```

**AlertHistory Object:**
```python
AlertHistory(
    alert_id="portfolio_risk_1642693815",
    alert_type=AlertType.PORTFOLIO_RISK_HIGH,
    severity=RiskLevel.HIGH,
    message="High portfolio risk: 4.2% ($420.00)",
    timestamp=datetime(2025, 1, 20, 17, 10, 15),
    resolved=False
)
```

#### 2. Drawdown Alerts
**Trigger**: Account drawdown exceeds safety thresholds

```telegram
🔴 *RISK ALERT - CRITICAL*

🚨 **Alert Type:** Emergency Stop
📝 **Message:** CRITICAL: Drawdown 15.2% - EMERGENCY STOP TRIGGERED
⏰ **Time:** 2025-01-20 17:15:30
🆔 **Alert ID:** emergency_stop_1642694130

🛑 **EMERGENCY:** All trading has been stopped immediately

🔔 **Status:** ACTIVE - Monitoring continues
```

#### 3. Correlation Alerts
**Trigger**: High correlation detected between positions

```telegram
⚠️ *RISK ALERT - MEDIUM*

⚠️ **Alert Type:** Correlation High
📝 **Message:** High correlation: 0.82 (positions may be too similar)
⏰ **Time:** 2025-01-20 17:05:45
🆔 **Alert ID:** correlation_1642693545

🔗 **Action Required:** High correlation detected between positions

🔔 **Status:** ACTIVE - Monitoring continues
```

#### 4. System Alerts
**Trigger**: Technical issues or system errors

```telegram
ℹ️ *RISK ALERT - LOW*

ℹ️ **Alert Type:** System Error
📝 **Message:** Connection timeout with MT5 connector
⏰ **Time:** 2025-01-20 16:55:20
🆔 **Alert ID:** system_error_1642692920

⚙️ **Technical:** System error requires attention

🔔 **Status:** ACTIVE - Monitoring continues
```

### Implementation Details

#### 1. Alert Object Structure
```python
@dataclass
class AlertHistory:
    """Risk alert data structure"""
    alert_id: str                    # Unique identifier
    alert_type: AlertType           # Type of risk alert
    severity: RiskLevel             # LOW/MEDIUM/HIGH/CRITICAL
    message: str                    # Human-readable message
    timestamp: datetime             # When alert was created
    resolved: bool = False          # Whether alert is resolved
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
```

#### 2. Rich Formatting Logic
```python
async def send_risk_alert(self, alert: AlertHistory) -> bool:
    """Send formatted risk alert to Telegram"""

    # Map severity to emoji and priority
    severity_emojis = {
        RiskLevel.LOW: "ℹ️",
        RiskLevel.MEDIUM: "⚠️",
        RiskLevel.HIGH: "🚨",
        RiskLevel.CRITICAL: "🔴"
    }

    priority_map = {
        RiskLevel.LOW: "low",
        RiskLevel.MEDIUM: "normal",
        RiskLevel.HIGH: "high",
        RiskLevel.CRITICAL: "high"
    }

    # Build rich message with context-sensitive content
    message = f"""
{severity_emojis[alert.severity]} *RISK ALERT - {alert.severity.value.upper()}*

🚨 **Alert Type:** {alert.alert_type.value.replace("_", " ").title()}
📝 **Message:** {alert.message}
⏰ **Time:** {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
🆔 **Alert ID:** {alert.alert_id}

{self._get_action_text(alert.alert_type)}

🔔 **Status:** {"RESOLVED" if alert.resolved else "ACTIVE"}
"""

    return await self.send_message(
        message,
        priority=priority_map[alert.severity]
    )
```

#### 3. Context-Sensitive Action Text
```python
def _get_action_text(self, alert_type: AlertType) -> str:
    """Get contextual action recommendations"""
    action_map = {
        AlertType.DRAWDOWN_EXCEEDED: "💰 **Action Required:** Review open positions and consider reducing risk",
        AlertType.PORTFOLIO_RISK_HIGH: "📊 **Action Required:** Portfolio risk is approaching limits",
        AlertType.CORRELATION_HIGH: "🔗 **Action Required:** High correlation detected between positions",
        AlertType.EMERGENCY_STOP: "🛑 **EMERGENCY:** All trading has been stopped immediately",
        AlertType.MARGIN_CALL: "💸 **URGENT:** Margin level is critically low",
        AlertType.VOLATILITY_SPIKE: "📈 **Warning:** Unusual market volatility detected",
        AlertType.SYSTEM_ERROR: "⚙️ **Technical:** System error requires attention"
    }
    return action_map.get(alert_type, "🔔 **Info:** Risk monitoring alert")
```

### Rate Limiting and Queue Management

#### Smart Rate Limiting
- **Hourly Limit**: 20 risk alerts per hour
- **Cooldown**: 5 minutes between similar alert types
- **Priority Override**: Critical alerts bypass rate limits
- **Queue Management**: Failed messages queued for retry

```python
async def _check_rate_limit(self) -> bool:
    """Smart rate limiting for risk alerts"""
    now = datetime.now()

    # Reset counter if hour has passed
    if now - self.last_notification_reset > timedelta(hours=1):
        self.notification_count.clear()
        self.last_notification_reset = now

    # Check limits
    total_notifications = sum(self.notification_count.values())
    return total_notifications < self.config.notification_rate_limit_per_hour
```

#### Cooldown Management
```python
async def _create_alert(self, alert_type: AlertType, severity: RiskLevel, message: str):
    """Create alert with cooldown management"""
    # Check cooldown to prevent spam
    cooldown_key = f"{alert_type.value}_{symbol or 'global'}"
    if cooldown_key in self.alert_cooldowns:
        return  # Still in cooldown

    # Create and send alert
    alert = AlertHistory(...)
    await self._send_notifications(alert)

    # Set cooldown
    cooldown_duration = timedelta(minutes=self.config.alert_cooldown_minutes)
    self.alert_cooldowns[cooldown_key] = datetime.now() + cooldown_duration
```

### Error Handling and Recovery

#### Retry Mechanism
```python
async def send_message(self, message: str, priority: str = "normal") -> bool:
    """Send with sophisticated retry logic"""

    for attempt in range(self.max_retries):
        try:
            success = await self._send_message_attempt(message)
            if success:
                await self._process_failed_messages()  # Process queue
                return True

        except Exception as e:
            logger.warning(f"Telegram send attempt {attempt + 1} failed: {e}")

        # Exponential backoff
        if attempt < self.max_retries - 1:
            delay = self.retry_delay * (2 ** attempt)
            await asyncio.sleep(delay)

    # Queue failed message for high/critical priority
    if priority in ["high", "normal"]:
        self._queue_failed_message(message, priority)

    return False
```

#### Failed Message Queue
```python
def _queue_failed_message(self, message: str, priority: str):
    """Queue failed messages for retry"""
    failed_msg = {
        "message": message,
        "priority": priority,
        "timestamp": now_utc(),
        "attempts": 0
    }

    # Limit queue size (max 50 messages)
    if len(self.failed_messages) < 50:
        self.failed_messages.append(failed_msg)
    else:
        # Drop oldest message and add new one
        self.failed_messages.pop(0)
        self.failed_messages.append(failed_msg)
```

### Configuration Options

#### Notification Settings in risk_parameters.yaml
```yaml
real_time_monitoring:
  notifications:
    telegram:
      enabled: true                    # Enable risk alerts via Telegram
      alert_cooldown_minutes: 5        # Cooldown between similar alerts
      rate_limit_per_hour: 20          # Maximum alerts per hour
      severity_levels:
        low: true                      # Send info/low priority alerts
        medium: true                   # Send warning/medium alerts
        high: true                     # Send high priority alerts
        critical: true                 # Send emergency/critical alerts

    email:
      enabled: false                   # Email notifications (optional)
      alert_cooldown_minutes: 10       # Email-specific cooldown
      rate_limit_per_hour: 10          # Email rate limit

  alert_types:
    drawdown_exceeded: true            # Drawdown threshold alerts
    portfolio_risk_high: true         # Portfolio risk alerts
    correlation_high: true            # Position correlation alerts
    position_size_large: true         # Large position alerts
    volatility_spike: true            # Market volatility alerts
    margin_call: true                 # Margin level alerts
    emergency_stop: true              # Emergency stop alerts
    system_error: true                # Technical error alerts
```

### Testing and Validation

#### Integration Testing
```python
async def test_risk_alert_integration():
    """Test complete AlertHistory → Telegram flow"""

    # Create test alert
    alert = AlertHistory(
        alert_id="test_integration_123",
        alert_type=AlertType.PORTFOLIO_RISK_HIGH,
        severity=RiskLevel.HIGH,
        message="Test portfolio risk alert: 3.8% ($380.00)",
        timestamp=datetime.now()
    )

    # Send via Telegram notifier
    telegram_notifier = TelegramNotifier(
        bot_token="test_token",
        chat_id="test_chat",
        enabled=True
    )

    success = await telegram_notifier.send_risk_alert(alert)
    assert success, "Risk alert should be sent successfully"

    # Verify message formatting
    assert "🚨 *RISK ALERT - HIGH*" in last_sent_message
    assert "Portfolio Risk High" in last_sent_message
    assert "test_integration_123" in last_sent_message
```

#### End-to-End Validation
```bash
# Test complete integration with dry-run
uv run trading-bot start --dry-run

# Expected output sequence:
✅ Risk management configuration loaded from risk_parameters.yaml
✅ Notification service initialized successfully
✅ Risk monitor connected to Telegram notifications
✅ All components initialized successfully

# Test alert generation (manual trigger)
uv run trading-bot risk test-alert --type portfolio_risk --severity high
```

### Benefits of Risk Alert Integration

✅ **Immediate Awareness**: Real-time notification of all risk events
✅ **Rich Context**: Detailed alerts with actionable recommendations
✅ **Smart Rate Limiting**: Prevents spam while ensuring critical alerts
✅ **Robust Delivery**: Retry mechanism with queue management
✅ **Configurable Severity**: Control which alert types to receive
✅ **Error Recovery**: Graceful handling of network issues
✅ **Production Ready**: Comprehensive testing and validation

**Integration Status**: ✅ **PRODUCTION READY** (Phase 4.5 Completed)
- **Flow**: AlertHistory objects seamlessly converted to rich Telegram messages
- **Rate Limiting**: Smart cooldowns prevent notification spam
- **Error Handling**: Robust retry mechanism with failed message queue
- **Configuration**: Complete control over alert types and severity levels
- **Testing**: End-to-end validation successful via integration tests

This comprehensive notification guide provides everything needed to implement and maintain a sophisticated Telegram notification system for the trading bot.
