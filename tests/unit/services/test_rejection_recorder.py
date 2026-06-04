"""Tests for RejectionRecorder (signal rejection telemetry)."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from trading_core.enums.rejection_stage import RejectionStage
from trading_worker.services.rejection_recorder import RejectionRecorder


def _session_patch(monkeypatch, session):
    """Patch trading_core.data.database.get_session to yield `session`."""

    @asynccontextmanager
    async def fake_get_session():
        yield session

    import trading_core.data.database as db

    monkeypatch.setattr(db, "get_session", fake_get_session)


class TestRecord:
    def test_disabled_is_noop(self):
        r = RejectionRecorder(enabled=False)
        r.record(stage=RejectionStage.CLIMAX, symbol="XAGUSD")
        assert r._buffer == []

    def test_record_buffers_and_serialises_stage(self):
        r = RejectionRecorder(enabled=True)
        r.record(
            stage=RejectionStage.CLIMAX,
            symbol="XAGUSD",
            asset_class="commodities",
            direction="SELL",
            confluence_score=61.7,
            details={"current_range": 1.2},
        )
        assert len(r._buffer) == 1
        row = r._buffer[0]
        assert row["stage"] == "climax"  # enum -> value
        assert row["symbol"] == "XAGUSD"
        assert row["confluence_score"] == 61.7
        assert row["details"] == {"current_range": 1.2}

    def test_record_accepts_plain_string_stage(self):
        r = RejectionRecorder(enabled=True)
        r.record(stage="custom_stage", symbol="EURUSD")
        assert r._buffer[0]["stage"] == "custom_stage"

    def test_buffer_capped(self):
        r = RejectionRecorder(enabled=True, max_buffer=3)
        for _ in range(10):
            r.record(stage=RejectionStage.RSI_GATE, symbol="EURUSD")
        assert len(r._buffer) == 3


class TestFlush:
    @pytest.mark.asyncio
    async def test_flush_writes_and_clears(self, monkeypatch):
        session = MagicMock()
        session.add_all = MagicMock()
        session.commit = AsyncMock()
        _session_patch(monkeypatch, session)

        r = RejectionRecorder(enabled=True)
        r.record(stage=RejectionStage.CONFLUENCE_TOO_LOW, symbol="EURUSD")
        r.record(stage=RejectionStage.CLIMAX, symbol="XAGUSD")

        written = await r.flush()

        assert written == 2
        assert r._buffer == []
        session.add_all.assert_called_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_flush_empty_returns_zero(self, monkeypatch):
        session = MagicMock()
        _session_patch(monkeypatch, session)
        r = RejectionRecorder(enabled=True)
        assert await r.flush() == 0

    @pytest.mark.asyncio
    async def test_flush_disabled_returns_zero(self):
        r = RejectionRecorder(enabled=False)
        r._buffer.append({"symbol": "X"})  # would-be data
        assert await r.flush() == 0

    @pytest.mark.asyncio
    async def test_flush_failure_rebuffers(self, monkeypatch):
        session = MagicMock()
        session.add_all = MagicMock()
        session.commit = AsyncMock(side_effect=RuntimeError("db down"))
        _session_patch(monkeypatch, session)

        r = RejectionRecorder(enabled=True)
        r.record(stage=RejectionStage.CLIMAX, symbol="XAGUSD")

        written = await r.flush()

        assert written == 0
        # data preserved for retry
        assert len(r._buffer) == 1
