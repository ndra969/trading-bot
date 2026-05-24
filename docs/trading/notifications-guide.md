# Telegram Notifications Guide

Setup and configure Telegram notifications for trading bot alerts.

## Quick Setup

### 1. Create Telegram Bot

1. Open Telegram, search for `@BotFather`
2. Send `/newbot` command
3. Follow prompts to set name and username
4. Save the **bot token** provided

### 2. Get Your Chat ID

```bash
# Get updates from your bot
curl https://api.telegram.org/bot<TOKEN>/getUpdates

# Or send a message to your bot and check the result
```

Look for `"chat":{"id":123456789}` in the response.

### 3. Configure Environment

Add to `.env` file:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_ENABLED=true
```

### 4. Test Connection

```bash
uv run trading-bot start --dry-run
# Should send startup notification
```

## Notification Types

### Trading Events

| Event | Notification |
|-------|--------------|
| Signal Generated | Symbol, direction, confidence |
| Position Opened | Entry price, SL, TP, volume |
| Position Closed | P&L, pips, duration |
| Breakeven Hit | SL moved to entry |
| Trailing Stop | New SL level |
| Partial Close | Profit taken, remaining position |

### Risk Alerts

| Alert | Trigger |
|-------|----------|
| Warning | Risk > 80% of limit |
| Critical | Risk > 95% of limit |
| Emergency | Drawdown > 10% |
| Daily Loss | Daily loss > 1% |

### System Events

| Event | Notification |
|-------|--------------|
| Bot Started | Configuration summary |
| Bot Stopped | Final P&L summary |
| MT5 Connected | Account info |
| MT5 Disconnected | Connection error |
| Error | Error details with stack trace |

## Configuration

`config/default.yaml`:

```yaml
monitoring:
  telegram:
    enabled: true
    bot_token: ${TELEGRAM_BOT_TOKEN}
    chat_id: ${TELEGRAM_CHAT_ID}

    # Notification types
    notify_on_trade: true
    notify_on_risk: true
    notify_on_error: true
    notify_daily_summary: true

    # Rate limiting (prevent spam)
    rate_limit_per_minute: 5
    rate_limit_per_hour: 20
    quiet_hours_enabled: false
```

## Message Format

### Trade Opened
```
📊 NEW POSITION
┌─────────────────────────
💱 EURUSD BUY
📈 Entry: 1.0850
🎯 TP: 1.0950 (+100 pips)
🛑 SL: 1.0800 (-50 pips)
📊 Volume: 0.01 lots
💰 Risk: $10
└─────────────────────────
```

### Position Closed
```
✅ POSITION CLOSED
┌─────────────────────────
💱 EURUSD #12345
📊 Result: +$50 (50 pips)
⏱️ Duration: 2h 15m
📈 Win Rate: 65%
└─────────────────────────
```

## Rate Limiting

Prevents notification spam:
- **Per minute**: Max 5 notifications
- **Per hour**: Max 20 notifications
- **Cooldown**: 60 seconds between similar alerts

## Troubleshooting

### No Notifications Received

**Check**:
1. Bot token is correct in `.env`
2. Chat ID is correct (no leading `-` for personal chats)
3. Bot is started: `uv run trading-bot start --dry-run`
4. Check logs for Telegram errors

### Bot Token Invalid

**Solution**:
1. Recreate bot via BotFather
2. Update `.env` with new token
3. Restart bot

### Wrong Chat ID

**Common mistakes**:
- Using group ID for personal chat (remove `-100` prefix)
- Using channel ID (must invite bot first)
- Old chat ID (re-check with `/getUpdates`)

## Best Practices

1. **Test First**: Always test with `--dry-run`
2. **Use Groups**: For multiple users, create a Telegram group
3. **Set Quiet Hours**: Disable notifications during sleep
4. **Monitor Limits**: Watch rate limit usage
5. **Secure Token**: Never commit bot token to git

## Commands

> **Note**: `notifications` CLI commands are 📋 planned. Currently test via dry-run mode.

```bash
# ✅ Current: Test via dry-run with notifications enabled
# Set send_in_dry_run: true in config, then:
uv run trading-bot start --dry-run

# 📋 Planned commands:
# uv run trading-bot notifications test
# uv run trading-bot notifications status
# uv run trading-bot notify --message "Test message"
```

## Related Documentation

- [Configuration Guide](../setup/configuration-guide.md) - Full config setup
- [Risk Management Guide](risk-management-guide.md) - Risk alerts
