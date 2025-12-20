"""
Notification Manager for Telegram integration.

Handles asynchronous message sending with queueing and rate limiting.
"""

import asyncio
import logging
from enum import Enum
from typing import Any

import httpx

from trading_bot.config import Configuration

logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """Notification severity levels."""

    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class NotificationManager:
    """
    Manages Telegram notifications.

    Features:
    - Asynchronous message queue (non-blocking)
    - Rate limiting compliance
    - Automatic retries
    - HTML formatting support
    """

    def __init__(self, config: Configuration | dict):
        """
        Initialize notification manager.

        Args:
            config: Application configuration (Configuration object or dict)
        """
        self.config = config

        # Handle both Configuration object and dictionary
        if hasattr(config, "telegram"):
            self.telegram_config = config.telegram
            # Access other props via object
            self.env = getattr(config, "env", "unknown")
            self.is_dry_run = getattr(
                config.trading, "dry_run", False
            )  # Default to False for live trading
        else:
            # It's a dictionary
            self.telegram_config = type("obj", (object,), config.get("telegram", {}))
            self.env = config.get("env", "unknown")
            self.is_dry_run = config.get("trading", {}).get(
                "dry_run", False
            )  # Default to False for live trading

            # Helper to allow .access for the fake config object
            if isinstance(self.telegram_config, dict):
                # Convert dict to simple object with attributes
                class DictObj:
                    def __init__(self, d):
                        self.__dict__ = d

                    def __getattr__(self, name):
                        return None

                self.telegram_config = DictObj(config.get("telegram", {}))

        # Check if enabled
        # telegram_config might be an object with attributes now
        self.enabled = getattr(self.telegram_config, "enabled", False) and bool(
            getattr(self.telegram_config, "bot_token", None)
        )

        self.queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False
        self.worker_task: asyncio.Task | None = None

        # Emoji mapping
        self.emojis = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.SUCCESS: "✅",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨",
        }

        if self.enabled:
            logger.info("NotificationManager initialized (Telegram enabled)")
        else:
            logger.warning(
                "NotificationManager initialized (Telegram DISABLED - missing token or disabled in config)"
            )

    async def start(self):
        """Start the notification worker."""
        if not self.enabled:
            return

        self.is_running = True
        self.worker_task = asyncio.create_task(self._process_queue())
        logger.info("Notification worker started")

        # Send startup message
        await self.send_message(
            "🚀 **Trading Bot Started**\n"
            f"Environment: `{self.env}`\n"
            f"Mode: `{'Dry Run' if self.is_dry_run else 'Live Trading'}`",
            level=NotificationLevel.SUCCESS,
        )

    async def stop(self):
        """Stop the notification worker."""
        if not self.is_running:
            return

        # Send shutdown message
        await self.send_message("🛑 **Trading Bot Stopped**", level=NotificationLevel.WARNING)

        self.is_running = False

        # Wait for queue to drain (with timeout)
        try:
            if not self.queue.empty():
                logger.info(f"Waiting for {self.queue.qsize()} notifications to send...")
                await asyncio.wait_for(self.queue.join(), timeout=5.0)
        except TimeoutError:
            logger.warning("Notification queue drain timed out")

        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        logger.info("Notification worker stopped")

    async def send_message(
        self, message: str, level: NotificationLevel = NotificationLevel.INFO, sound: bool = True
    ):
        """
        Queue a message for sending.

        Args:
            message: Message text (supports Markdown/HTML)
            level: Severity level
            sound: Whether to play notification sound
        """
        if not self.enabled:
            return

        # Format message with emoji
        emoji = self.emojis.get(level, "ℹ️")
        formatted_message = f"{emoji} {message}"

        await self.queue.put({"text": formatted_message, "disable_notification": not sound})

    async def send_heartbeat(self, stats: dict[str, Any]):
        """
        Send periodic heartbeat message.

        Args:
            stats: Dictionary containing bot statistics
        """
        if not self.enabled:
            return

        # Format stats
        balance = stats.get("balance", 0.0)
        positions = stats.get("open_positions", 0)

        message = (
            "💓 **Bot Heartbeat**\n"
            f"💰 Balance: `${balance:,.2f}`\n"
            f"📈 Open Positions: `{positions}`\n"
            "🟢 System Status: **Online**"
        )

        await self.send_message(message, level=NotificationLevel.INFO, sound=False)

    async def send_daily_report(self, report: dict[str, Any]):
        """
        Send daily performance report.

        Args:
            report: Dictionary containing daily report data
        """
        if not self.enabled:
            return

        pnl = report.get("pnl", 0.0)
        trades_count = report.get("trades_count", 0)
        win_rate = report.get("win_rate", 0.0)

        # Emoji based on PnL
        header_emoji = "📈" if pnl >= 0 else "📉"

        message = (
            f"{header_emoji} **Daily Report**\n"
            f"📅 Date: `{report.get('date', 'Today')}`\n"
            f"💵 P&L: **${pnl:,.2f}**\n"
            f"🔢 Trades: `{trades_count}`\n"
            f"🎯 Win Rate: `{win_rate:.1f}%`\n"
            f"💰 Final Balance: `${report.get('balance', 0.0):,.2f}`"
        )

        await self.send_message(message, level=NotificationLevel.SUCCESS)

    async def _process_queue(self):
        """Background worker to process the message queue."""
        bot_token = getattr(self.telegram_config, "bot_token", None)
        if not bot_token:
            logger.error("Bot token not configured, stopping worker")
            return

        base_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        async with httpx.AsyncClient(timeout=10.0) as client:
            while self.is_running:
                try:
                    # Get message from queue
                    payload = await self.queue.get()

                    # Prepare request
                    chat_id = getattr(self.telegram_config, "chat_id", None)
                    if not chat_id:
                        logger.error("Chat ID not configured")
                        self.queue.task_done()
                        continue

                    data = {
                        "chat_id": chat_id,
                        "text": payload["text"],
                        "parse_mode": "Markdown",  # Use Markdown for bold/italic
                        "disable_notification": payload["disable_notification"],
                    }

                    # Send with retry logic
                    for attempt in range(3):
                        try:
                            response = await client.post(base_url, json=data)
                            response.raise_for_status()
                            break  # Success
                        except Exception as e:
                            if attempt == 2:
                                logger.error(f"Failed to send Telegram notification: {e}")
                            else:
                                await asyncio.sleep(1 * (attempt + 1))  # Backoff

                    self.queue.task_done()

                    # Rate limiting (1 message per second to be safe)
                    await asyncio.sleep(1.0)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in notification worker: {e}")
                    await asyncio.sleep(5.0)  # Wait before retrying loop
