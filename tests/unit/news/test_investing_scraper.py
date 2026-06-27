"""Unit tests for InvestingScraper.parse against a saved filter-endpoint fixture.

No live network: parsing is pure and fixture-driven. The fixture mirrors the
real Investing.com filter-endpoint row format (verified 2026-06-27). These
tests pin the parser's contract so a schema fix has a clear target.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from trading_worker.news.investing_scraper import InvestingScraper
from trading_worker.news.models import NewsImpact

FIXTURE = Path(__file__).parents[2] / "fixtures" / "news" / "investing_calendar.html"


@pytest.fixture
def html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def scraper() -> InvestingScraper:
    return InvestingScraper()


class TestParse:
    def test_parses_valid_events_only(self, scraper, html):
        events = scraper.parse(html)
        # 3 real events; the "All Day" holiday (no datetime) and the malformed
        # (no-currency) row are dropped without crashing.
        assert len(events) == 3
        assert {e.name for e in events} == {
            "Nonfarm Payrolls (May)",
            "German Ifo Business Climate (Jun)",
            "Crude Oil Inventories",
        }

    def test_high_impact_event_fields(self, scraper, html):
        nfp = next(e for e in scraper.parse(html) if e.name.startswith("Nonfarm"))
        assert nfp.currency == "USD"
        assert nfp.impact is NewsImpact.HIGH
        assert nfp.event_time_utc == datetime(2026, 6, 25, 12, 30, tzinfo=UTC)
        assert nfp.actual == "200K"
        assert nfp.forecast == "180K"
        assert nfp.previous == "175K"
        assert nfp.source_id == "551001"
        assert nfp.has_actual

    def test_times_are_utc_aware(self, scraper, html):
        assert all(e.event_time_utc.tzinfo == UTC for e in scraper.parse(html))

    def test_impact_tiers(self, scraper, html):
        by_name = {e.name.split()[0]: e.impact for e in scraper.parse(html)}
        assert by_name["Nonfarm"] is NewsImpact.HIGH
        assert by_name["German"] is NewsImpact.MEDIUM
        assert by_name["Crude"] is NewsImpact.LOW

    def test_impact_falls_back_to_icon_count_without_img_key(self, scraper, html):
        # The LOW row (Crude Oil) has no data-img_key — impact comes from the
        # single filled icon, exercising the fallback path.
        low = next(e for e in scraper.parse(html) if e.name.startswith("Crude"))
        assert low.impact is NewsImpact.LOW

    def test_empty_cells_become_none(self, scraper, html):
        ifo = next(e for e in scraper.parse(html) if e.name.startswith("German"))
        assert ifo.actual is None  # &nbsp; → None
        assert not ifo.has_actual

    def test_currency_uppercased(self, scraper, html):
        assert all(e.currency.isupper() for e in scraper.parse(html))


class TestDegradeSafe:
    def test_no_calendar_markup_returns_empty(self, scraper):
        assert scraper.parse("<html><body>no calendar here</body></html>") == []

    def test_garbage_input_returns_empty(self, scraper):
        assert scraper.parse("") == []
        assert scraper.parse("<<<broken") == []

    def test_empty_table_returns_empty(self, scraper):
        empty = '<table id="economicCalendarData"><tbody></tbody></table>'
        assert scraper.parse(empty) == []
