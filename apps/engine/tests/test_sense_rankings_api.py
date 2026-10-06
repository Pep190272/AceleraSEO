"""HTTP surface for GET /sense/rankings: guard, config gating, validation, shape."""
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import aceleraseo.interfaces.api.app as app_module
from aceleraseo.domain.models import ConversionCount, ConversionSnapshot, RankingSignal
from aceleraseo.infrastructure.config import Settings
from aceleraseo.infrastructure.persistence.db import make_session_factory
from aceleraseo.infrastructure.persistence.repository import (
    ConversionRepository,
    RankingRepository,
)

TOKEN = {"X-Engine-Token": "local-test-token"}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.setenv("ENGINE_API_TOKEN", "local-test-token")

    def configure(site_url="sc-domain:example.com", **values):
        # A file, not :memory: — every request builds a fresh engine.
        settings = Settings(_env_file=None, gsc_site_url=site_url,
                            database_url=f"sqlite:///{tmp_path}/t.db", **values)
        monkeypatch.setattr(app_module, "get_settings", lambda: settings)
        return settings

    return configure


def test_requires_token(setup):
    setup()
    assert TestClient(app_module.app).get("/sense/rankings").status_code == 401


def test_400_without_site_url(setup):
    setup(site_url="")
    resp = TestClient(app_module.app).get("/sense/rankings", headers=TOKEN)
    assert resp.status_code == 400
    assert "GSC_SITE_URL" in resp.json()["detail"]


def test_empty_store_returns_200_with_no_rows(setup):
    setup()
    resp = TestClient(app_module.app).get("/sense/rankings", headers=TOKEN)
    assert resp.status_code == 200
    body = resp.json()
    assert body["rows"] == [] and body["last_observed_on"] is None
    assert body["window"]["days"] == 28


def test_returns_rows_with_deltas(setup):
    settings = setup()
    last = date.today() - timedelta(days=3)
    RankingRepository(make_session_factory(settings.database_url)).save_many(
        settings.gsc_site_url, [
            RankingSignal("seo", "/", 3.0, 4, 40, 0.1, last),
            RankingSignal("seo", "/", 5.0, 2, 40, 0.05, last - timedelta(days=7)),
        ])
    resp = TestClient(app_module.app).get("/sense/rankings?days=7", headers=TOKEN)
    assert resp.status_code == 200
    body = resp.json()
    assert body["window"] == {"start": (last - timedelta(days=6)).isoformat(),
                              "end": last.isoformat(), "days": 7}
    assert body["min_impressions"] == 10
    assert body["rows"] == [{"query": "seo", "clicks": 4, "impressions": 40,
                             "position": 3.0, "previous_position": 5.0,
                             "previous_impressions": 40, "position_delta": -2.0,
                             "top_page": None, "conversions": None}]
    assert body["conversions_source"] == "none" and body["conversions_window"] is None


def _seed_conversions(settings, last, snapshot_rows):
    factory = make_session_factory(settings.database_url)
    RankingRepository(factory).save_many(settings.gsc_site_url, [
        RankingSignal("seo", "https://example.com/espa%C3%B1a", 3.0, 9, 90, 0.1, last),
        RankingSignal("seo", "https://example.com/other/", 7.0, 1, 50, 0.02, last),
        RankingSignal("quiet", "https://example.com/blog/", 4.0, 2, 40, 0.05, last),
    ])
    ConversionRepository(factory).save_snapshot(
        settings.gsc_site_url, ConversionSnapshot(last, 90, snapshot_rows))


def test_rows_carry_the_conversions_of_the_top_page(setup):
    settings = setup(conversions_source="wordpress")
    last = date.today() - timedelta(days=3)
    _seed_conversions(settings, last, [
        ConversionCount("/españa/", "form", 2), ConversionCount("/españa/", "whatsapp", 1),
        ConversionCount("/other/", "form", 5),
    ])
    body = TestClient(app_module.app).get("/sense/rankings?days=7", headers=TOKEN).json()
    rows = {r["query"]: r for r in body["rows"]}
    # /other/ converts more, but "seo" lands on /españa/ (most clicks): 2 + 1 there.
    assert rows["seo"]["top_page"] == "https://example.com/espa%C3%B1a"
    assert rows["seo"]["conversions"] == 3
    assert rows["quiet"]["conversions"] == 0  # a real zero, not missing data
    assert body["conversions_source"] == "wordpress"
    assert body["conversions_window"] == {
        "start": (last - timedelta(days=89)).isoformat(), "end": last.isoformat(), "days": 90}


def test_conversions_are_hidden_when_the_source_is_none(setup):
    settings = setup()
    last = date.today() - timedelta(days=3)
    _seed_conversions(settings, last, [ConversionCount("/blog/", "form", 1)])
    body = TestClient(app_module.app).get("/sense/rankings?days=7", headers=TOKEN).json()
    assert {r["conversions"] for r in body["rows"]} == {None}
    assert body["conversions_window"] is None


def test_min_impressions_filters_rows_and_zero_keeps_them(setup):
    settings = setup()
    last = date.today() - timedelta(days=3)
    RankingRepository(make_session_factory(settings.database_url)).save_many(
        settings.gsc_site_url, [
            RankingSignal("seo", "/", 3.0, 4, 40, 0.1, last),
            RankingSignal("blip", "/", 9.0, 9, 3, 0.1, last),
        ])
    client = TestClient(app_module.app)
    filtered = client.get("/sense/rankings?days=7", headers=TOKEN).json()
    assert [r["query"] for r in filtered["rows"]] == ["seo"]
    unfiltered = client.get("/sense/rankings?days=7&min_impressions=0", headers=TOKEN).json()
    assert unfiltered["min_impressions"] == 0
    assert [r["query"] for r in unfiltered["rows"]] == ["blip", "seo"]


@pytest.mark.parametrize("params", ["days=0", "days=241", "limit=0", "limit=501",
                                    "min_impressions=-1", "min_impressions=10001"])
def test_422_when_out_of_range(setup, params):
    setup()
    resp = TestClient(app_module.app).get(f"/sense/rankings?{params}", headers=TOKEN)
    assert resp.status_code == 422


@pytest.mark.parametrize("params", ["days=240", "limit=500", "days=240&limit=500",
                                    "min_impressions=0", "min_impressions=10000"])
def test_inclusive_upper_bounds_are_accepted(setup, params):
    setup()
    resp = TestClient(app_module.app).get(f"/sense/rankings?{params}", headers=TOKEN)
    assert resp.status_code == 200


def test_search_console_today_is_pacific_time():
    # 05:00 UTC on 2 January is still 1 January in Los Angeles.
    now = datetime(2026, 1, 2, 5, 0, tzinfo=UTC)
    assert app_module._search_console_today(now) == date(2026, 1, 1)


def test_window_clamps_to_pacific_today(setup, monkeypatch):
    settings = setup()
    pacific_today = date(2026, 1, 1)
    RankingRepository(make_session_factory(settings.database_url)).save_many(
        settings.gsc_site_url, [
            RankingSignal("seo", "/", 3.0, 4, 40, 0.1, pacific_today),
            RankingSignal("seo", "/", 3.0, 4, 40, 0.1, pacific_today + timedelta(days=1)),
        ])
    monkeypatch.setattr(app_module, "_search_console_today", lambda: pacific_today)
    resp = TestClient(app_module.app).get("/sense/rankings?days=7", headers=TOKEN)
    assert resp.status_code == 200
    assert resp.json()["window"]["end"] == pacific_today.isoformat()
