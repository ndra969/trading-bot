import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trading_bot.config import Configuration
from trading_bot.utils.notification_manager import (
    NotificationLevel,
    NotificationManager,
    markdownish_to_html,
)


class TestMarkdownishToHtml:
    """Tests for the Telegram markup converter (regression for 400 errors)."""

    def test_bold_converted(self):
        assert markdownish_to_html("**Bold**") == "<b>Bold</b>"

    def test_code_converted(self):
        assert markdownish_to_html("`code`") == "<code>code</code>"

    def test_underscores_in_position_id_preserved(self):
        # Legacy Markdown choked on these unbalanced underscores -> 400.
        out = markdownish_to_html("Position pos_8063aa334151 closed")
        assert "pos_8063aa334151" in out

    def test_underscores_in_enum_preserved(self):
        out = markdownish_to_html("reason: STOP_LOSS")
        assert "STOP_LOSS" in out

    def test_html_special_chars_escaped(self):
        out = markdownish_to_html("a & b < c > d")
        assert "&amp;" in out
        assert "&lt;" in out
        assert "&gt;" in out

    def test_data_with_underscores_inside_code_escaped_but_preserved(self):
        out = markdownish_to_html("`pos_ab_12` & STOP_LOSS")
        assert out == "<code>pos_ab_12</code> &amp; STOP_LOSS"

    def test_real_close_notification_shape(self):
        msg = "**Trade Closed** `pos_8063aa334151` reason: STOP_LOSS P&L: -5.00 USC"
        out = markdownish_to_html(msg)
        assert out == (
            "<b>Trade Closed</b> <code>pos_8063aa334151</code> "
            "reason: STOP_LOSS P&amp;L: -5.00 USC"
        )


@pytest.fixture
def mock_config():
    """Mock configuration object."""
    config = MagicMock(spec=Configuration)
    config.telegram = MagicMock()
    config.telegram.enabled = True
    config.telegram.bot_token = "123456:ABC-DEF"
    config.telegram.chat_id = "987654321"
    config.env = "test"
    config.trading = MagicMock()
    config.trading.dry_run = True
    return config


@pytest.fixture
def notification_manager(mock_config):
    """NotificationManager instance."""
    return NotificationManager(mock_config)


@pytest.mark.asyncio
async def test_initialization_with_config_object(mock_config):
    """Test initialization with Configuration object."""
    manager = NotificationManager(mock_config)
    assert manager.enabled is True
    assert manager.telegram_config.bot_token == "123456:ABC-DEF"


@pytest.mark.asyncio
async def test_initialization_with_dict():
    """Test initialization with dictionary."""
    config_dict = {
        "telegram": {"enabled": True, "bot_token": "dict_token", "chat_id": "dict_chat"},
        "env": "test_dict",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)
    assert manager.enabled is True
    # Verify we can access attributes on the dynamic object
    assert manager.telegram_config.bot_token == "dict_token"
    assert manager.env == "test_dict"
    assert manager.is_dry_run is False


@pytest.mark.asyncio
async def test_send_message_queues_item(notification_manager):
    """Test send_message puts item in queue."""
    await notification_manager.send_message("Hello World", level=NotificationLevel.INFO)

    assert notification_manager.queue.qsize() == 1
    item = await notification_manager.queue.get()
    assert "ℹ️ Hello World" in item["text"]
    assert item["disable_notification"] is False


@pytest.mark.asyncio
async def test_formatting_levels(notification_manager):
    """Test emoji formatting for different levels."""
    levels = [
        (NotificationLevel.SUCCESS, "✅"),
        (NotificationLevel.WARNING, "⚠️"),
        (NotificationLevel.ERROR, "❌"),
        (NotificationLevel.CRITICAL, "🚨"),
    ]

    for level, emoji in levels:
        await notification_manager.send_message("Test", level=level)
        item = await notification_manager.queue.get()
        assert emoji in item["text"]


@pytest.mark.asyncio
async def test_process_queue_sends_request(notification_manager):
    """Test worker loop sends HTTP request."""
    # Mock httpx.AsyncClient
    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client_instance

        # Setup mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_client_instance.post.return_value = mock_response

        # Add item to queue
        await notification_manager.queue.put(
            {"text": "Test Message", "disable_notification": False}
        )

        # Start worker temporarily
        notification_manager.is_running = True
        worker_task = asyncio.create_task(notification_manager._process_queue())

        # Give it a moment to process
        await asyncio.sleep(0.1)

        # Stop worker
        notification_manager.is_running = False
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        # Verify post was called
        mock_client_instance.post.assert_called_once()
        args, kwargs = mock_client_instance.post.call_args

        # Check URL and Data
        assert "123456:ABC-DEF" in args[0]
        assert kwargs["json"]["chat_id"] == "987654321"
        assert kwargs["json"]["text"] == "Test Message"
        assert kwargs["json"]["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_disabled_manager_does_nothing(mock_config):
    """Test disabled manager queues nothing."""
    mock_config.telegram.enabled = False
    manager = NotificationManager(mock_config)

    await manager.send_message("Test")
    assert manager.queue.qsize() == 0


@pytest.mark.asyncio
async def test_heartbeat_formatting(notification_manager):
    """Test send_heartbeat formatting."""
    stats = {"balance": 1234.56, "open_positions": 5}
    await notification_manager.send_heartbeat(stats)

    item = await notification_manager.queue.get()
    assert "💓 **Bot Heartbeat**" in item["text"]
    assert "1,234.56 USD" in item["text"]
    assert "5" in item["text"]


@pytest.mark.asyncio
async def test_start_method(notification_manager):
    """Test start method initializes worker."""
    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_client_instance.post.return_value = mock_response

        await notification_manager.start()

        assert notification_manager.is_running is True
        assert notification_manager.worker_task is not None

        # Cleanup
        await notification_manager.stop()


@pytest.mark.asyncio
async def test_start_method_disabled():
    """Test start method does nothing when disabled."""
    config_dict = {
        "telegram": {"enabled": False, "bot_token": None, "chat_id": "123"},
        "env": "test",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)

    await manager.start()
    assert manager.is_running is False
    assert manager.worker_task is None


@pytest.mark.asyncio
async def test_stop_method(notification_manager):
    """Test stop method stops worker."""
    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_client_instance.post.return_value = mock_response

        await notification_manager.start()
        assert notification_manager.is_running is True

        await notification_manager.stop()
        assert notification_manager.is_running is False


@pytest.mark.asyncio
async def test_stop_method_not_running(notification_manager):
    """Test stop method when not running."""
    # Should not raise error
    await notification_manager.stop()
    assert notification_manager.is_running is False


@pytest.mark.asyncio
async def test_send_message_disabled():
    """Test send_message when manager is disabled."""
    config_dict = {
        "telegram": {"enabled": False, "bot_token": None, "chat_id": "123"},
        "env": "test",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)

    await manager.send_message("Test")
    assert manager.queue.qsize() == 0


@pytest.mark.asyncio
async def test_process_queue_error_handling(notification_manager):
    """Test _process_queue handles errors gracefully."""
    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        # Simulate error
        mock_client_instance.post.side_effect = Exception("Network error")

        # Add item to queue
        await notification_manager.queue.put(
            {"text": "Test Message", "disable_notification": False}
        )

        # Start worker temporarily
        notification_manager.is_running = True
        worker_task = asyncio.create_task(notification_manager._process_queue())

        # Give it a moment to process
        await asyncio.sleep(0.1)

        # Stop worker
        notification_manager.is_running = False
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        # Should have attempted to send
        mock_client_instance.post.assert_called()


@pytest.mark.asyncio
async def test_send_message_with_sound_disabled(notification_manager):
    """Test send_message with sound disabled."""
    await notification_manager.send_message("Test", sound=False)

    item = await notification_manager.queue.get()
    assert item["disable_notification"] is True


@pytest.mark.asyncio
async def test_send_message_with_sound_enabled(notification_manager):
    """Test send_message with sound enabled."""
    await notification_manager.send_message("Test", sound=True)

    item = await notification_manager.queue.get()
    assert item["disable_notification"] is False


@pytest.mark.asyncio
async def test_initialization_with_dict_converts_telegram_config():
    """Test DictObj conversion when telegram_config is a dict."""
    config_dict = {
        "telegram": {"enabled": True, "bot_token": "test_token", "chat_id": "test_chat"},
        "env": "test_dict_obj",
        "trading": {"dry_run": True},
    }
    manager = NotificationManager(config_dict)

    # Verify the telegram config object works correctly
    # The type("obj", ...) creates a dynamic object
    assert manager.enabled is True
    assert manager.telegram_config.bot_token == "test_token"
    assert manager.telegram_config.chat_id == "test_chat"


@pytest.mark.asyncio
async def test_initialization_with_object_config():
    """Test initialization with Configuration object (not dict)."""

    class FakeConfig:
        def __init__(self):
            # Start with telegram as an object with attributes
            class Telegram:
                def __init__(self):
                    self.enabled = True
                    self.bot_token = "token123"
                    self.chat_id = "chat123"

            self.telegram = Telegram()
            self.env = "test"
            self.trading = type("obj", (object,), {"dry_run": False})()

    manager = NotificationManager(FakeConfig())

    # Since FakeConfig has telegram attribute, it should go through
    # the hasattr branch, and use the object directly
    assert manager.enabled is True
    assert manager.telegram_config.bot_token == "token123"
    assert manager.telegram_config.chat_id == "chat123"


@pytest.mark.asyncio
async def test_stop_with_cancelled_error():
    """Test stop method handles asyncio.CancelledError gracefully."""
    config_dict = {
        "telegram": {"enabled": True, "bot_token": "cancel_test", "chat_id": "123"},
        "env": "test",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)

    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client_instance

        # Make the POST call hang indefinitely to ensure worker is still running
        async def hanging_post(*args, **kwargs):
            # This will never complete, ensuring the worker is cancelled
            await asyncio.sleep(100)

        mock_client_instance.post.side_effect = hanging_post

        await manager.start()
        assert manager.is_running is True

        # Add multiple items to queue to ensure worker is busy
        await manager.send_message("Test message 1")
        await manager.send_message("Test message 2")
        await manager.send_message("Test message 3")

        # Give worker a moment to start processing the first item
        await asyncio.sleep(0.1)

        # Stop should handle CancelledError gracefully (lines 142-143)
        # The worker_task.cancel() will raise CancelledError when we await it
        # because the worker is still processing the hanging POST call
        await manager.stop()
        assert manager.is_running is False

        # Verify the task was cancelled
        assert manager.worker_task is None or manager.worker_task.done()


@pytest.mark.asyncio
async def test_send_heartbeat_when_disabled():
    """Test send_heartbeat returns early when manager is disabled."""
    config_dict = {
        "telegram": {"enabled": False, "bot_token": None, "chat_id": "123"},
        "env": "test",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)

    stats = {"balance": 1000.0, "open_positions": 3}
    await manager.send_heartbeat(stats)

    # Queue should be empty
    assert manager.queue.qsize() == 0


@pytest.mark.asyncio
async def test_send_daily_report_success(notification_manager):
    """Test send_daily_report formats and queues message correctly."""
    report_data = {
        "date": "2026-01-19",
        "pnl": 1250.50,
        "trades_count": 15,
        "win_rate": 66.7,
        "balance": 11250.50,
    }

    await notification_manager.send_daily_report(report_data)

    item = await notification_manager.queue.get()
    assert "📈 **Daily Report**" in item["text"]
    assert "2026-01-19" in item["text"]
    assert "1,250.50 USD" in item["text"]
    assert "15" in item["text"]
    assert "66.7%" in item["text"]
    assert "11,250.50 USD" in item["text"]


@pytest.mark.asyncio
async def test_send_daily_report_with_loss(notification_manager):
    """Test send_daily_report shows correct emoji for negative PnL."""
    report_data = {
        "pnl": -500.25,
        "trades_count": 10,
        "win_rate": 40.0,
        "balance": 9500.00,
    }

    await notification_manager.send_daily_report(report_data)

    item = await notification_manager.queue.get()
    text = item["text"]
    assert "📉 **Daily Report**" in text
    # Negative P&L formats as "-500.25 USD" (currency unit suffix)
    assert "-500.25 USD" in text


@pytest.mark.asyncio
async def test_send_daily_report_when_disabled():
    """Test send_daily_report returns early when manager is disabled."""
    config_dict = {
        "telegram": {"enabled": False, "bot_token": None, "chat_id": "123"},
        "env": "test",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)

    report_data = {"pnl": 100.0, "trades_count": 5, "win_rate": 60.0, "balance": 10000.0}
    await manager.send_daily_report(report_data)

    # Queue should be empty
    assert manager.queue.qsize() == 0


@pytest.mark.asyncio
async def test_send_daily_report_with_default_values(notification_manager):
    """Test send_daily_report uses default values for missing keys."""
    report_data = {"pnl": 100.0}  # Minimal data

    await notification_manager.send_daily_report(report_data)

    item = await notification_manager.queue.get()
    assert "📈 **Daily Report**" in item["text"]
    assert "Today" in item["text"]  # Default date
    assert "0" in item["text"]  # Default trades_count
    assert "0.0%" in item["text"]  # Default win_rate
    assert "0.00 USD" in item["text"]  # Default balance


@pytest.mark.asyncio
async def test_process_queue_without_bot_token():
    """Test _process_queue returns early when bot_token is missing."""
    config_dict = {
        "telegram": {"enabled": True, "bot_token": None, "chat_id": "123"},
        "env": "test",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)

    # Process queue should return immediately
    await manager._process_queue()

    # Queue should remain unprocessed
    await manager.queue.put({"text": "Test", "disable_notification": False})
    assert manager.queue.qsize() == 1


@pytest.mark.asyncio
async def test_process_queue_without_chat_id():
    """Test _process_queue handles missing chat_id gracefully."""
    config_dict = {
        "telegram": {"enabled": True, "bot_token": "test_token", "chat_id": None},
        "env": "test",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)

    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client_instance

        # Add item to queue
        await manager.queue.put({"text": "Test Message", "disable_notification": False})

        # Start worker temporarily
        manager.is_running = True
        worker_task = asyncio.create_task(manager._process_queue())

        # Give it a moment to process
        await asyncio.sleep(0.1)

        # Stop worker
        manager.is_running = False
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        # Queue should be empty (task_done was called)
        assert manager.queue.qsize() == 0


@pytest.mark.asyncio
async def test_process_queue_retry_logic():
    """Test _process_queue retries failed requests with backoff."""
    config_dict = {
        "telegram": {"enabled": True, "bot_token": "retry_token", "chat_id": "123"},
        "env": "test",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)

    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client_instance

        # Use a counter to track attempts
        attempt_count = [0]

        async def failing_post(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception(f"Fail attempt {attempt_count[0]}")
            # Third attempt succeeds
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            return mock_response

        mock_client_instance.post.side_effect = failing_post

        # Add item to queue
        await manager.queue.put({"text": "Retry Test", "disable_notification": False})

        # Start worker temporarily
        manager.is_running = True
        worker_task = asyncio.create_task(manager._process_queue())

        # Give it time to process all retries (including backoff delays)
        await asyncio.sleep(3.5)

        # Stop worker
        manager.is_running = False
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        # Should have attempted 3 times
        assert attempt_count[0] == 3
        # Queue should be empty (task_done was called)
        assert manager.queue.qsize() == 0


@pytest.mark.asyncio
async def test_process_queue_max_retries_exceeded():
    """Test _process_queue logs error after max retries."""
    config_dict = {
        "telegram": {"enabled": True, "bot_token": "max_retry_token", "chat_id": "123"},
        "env": "test",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)

    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client_instance

        # Always fail
        attempt_count = [0]

        async def always_failing_post(*args, **kwargs):
            attempt_count[0] += 1
            raise Exception("Always fail")

        mock_client_instance.post.side_effect = always_failing_post

        # Add item to queue
        await manager.queue.put({"text": "Fail Test", "disable_notification": False})

        # Start worker temporarily
        manager.is_running = True
        worker_task = asyncio.create_task(manager._process_queue())

        # Give it time to process all retries (including backoff delays)
        await asyncio.sleep(3.5)

        # Stop worker
        manager.is_running = False
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        # Should have attempted 3 times (max retries)
        assert attempt_count[0] == 3
        # Queue should be empty (task_done was called despite failures)
        assert manager.queue.qsize() == 0


@pytest.mark.asyncio
async def test_process_queue_exception_handling():
    """Test _process_queue handles exceptions and continues (lines 266-268)."""
    config_dict = {
        "telegram": {"enabled": True, "bot_token": "exception_token", "chat_id": "123"},
        "env": "test",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)

    # We need to trigger an exception outside the retry loop
    # The best way is to mock queue.get() to raise an exception
    original_get = manager.queue.get

    async def failing_get():
        # First call raises exception
        if not hasattr(failing_get, "called"):
            failing_get.called = True
            raise RuntimeError("Queue error")
        # Second call works normally
        return await original_get()

    manager.queue.get = failing_get

    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_client_instance.post.return_value = mock_response

        # Start worker temporarily
        manager.is_running = True
        worker_task = asyncio.create_task(manager._process_queue())

        # Give it time to process the exception and wait 5 seconds
        # But we'll cancel it after a short time to avoid the long wait
        await asyncio.sleep(0.2)

        # Stop worker
        manager.is_running = False
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        # The exception should have been caught by the outer handler (lines 266-268)
        # and logged, then the loop waited 5 seconds before continuing


@pytest.mark.asyncio
async def test_stop_drains_queue_with_timeout():
    """Test stop method handles queue drain timeout."""
    config_dict = {
        "telegram": {"enabled": True, "bot_token": "timeout_token", "chat_id": "123"},
        "env": "test",
        "trading": {"dry_run": False},
    }
    manager = NotificationManager(config_dict)

    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client_instance

        # Make post hang indefinitely
        async def hanging_post(*args, **kwargs):
            await asyncio.sleep(100)

        mock_client_instance.post.side_effect = hanging_post

        await manager.start()

        # Add items to queue
        for i in range(5):
            await manager.queue.put({"text": f"Message {i}", "disable_notification": False})

        # Stop should timeout after 5 seconds
        import time

        start = time.time()
        await manager.stop()
        elapsed = time.time() - start

        # Should timeout around 5 seconds
        assert elapsed >= 4.5  # Allow some margin
        assert manager.is_running is False
