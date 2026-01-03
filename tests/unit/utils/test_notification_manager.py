import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trading_bot.config import Configuration
from trading_bot.utils.notification_manager import NotificationLevel, NotificationManager


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
    assert "$1,234.56" in item["text"]
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
