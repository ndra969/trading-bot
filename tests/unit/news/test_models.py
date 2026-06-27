"""Unit tests for news domain value objects (Phase 0)."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest
from trading_worker.news.models import NewsEvent, NewsImpact


class TestNewsImpactFromImportance:
    @pytest.mark.parametrize(
        "importance,expected",
        [
            ("1", NewsImpact.LOW),
            ("2", NewsImpact.MEDIUM),
            ("3", NewsImpact.HIGH),
            (1, NewsImpact.LOW),
            (3, NewsImpact.HIGH),
            (4, NewsImpact.HIGH),  # clamps, never raises
            ("-1", NewsImpact.LOW),  # holiday marker
            (None, NewsImpact.LOW),  # missing → safe default
            ("garbage", NewsImpact.LOW),  # unparseable → safe default
        ],
    )
    def test_mapping(self, importance, expected):
        assert NewsImpact.from_importance(importance) == expected


class TestNewsEvent:
    def _event(self, **overrides) -> NewsEvent:
        base = {
            "event_time_utc": datetime(2026, 6, 25, 12, 30, tzinfo=UTC),
            "currency": "USD",
            "impact": NewsImpact.HIGH,
            "name": "Nonfarm Payrolls",
        }
        base.update(overrides)
        return NewsEvent(**base)

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            self._event(event_time_utc=datetime(2026, 6, 25, 12, 30))

    def test_is_high_impact(self):
        assert self._event(impact=NewsImpact.HIGH).is_high_impact
        assert not self._event(impact=NewsImpact.MEDIUM).is_high_impact

    def test_has_actual(self):
        assert not self._event().has_actual
        assert not self._event(actual="").has_actual
        assert self._event(actual="200K").has_actual

    def test_is_frozen(self):
        event = self._event()
        with pytest.raises(FrozenInstanceError):
            event.currency = "EUR"  # type: ignore[misc]
