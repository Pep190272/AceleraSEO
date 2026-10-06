"""HTTP surface for GET /sense/rankings: guard, config gating, validation, shape."""
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import aceleraseo.interfaces.api.app as app_module
from aceleraseo.domain.models import RankingSignal
from aceleraseo.infrastructure.config import Settings
from aceleraseo.infrastructure.persistence.db import make_session_factory
from aceleraseo.infrastructure.persistence.repository import RankingRepository

TOKEN = {"X-Engine-Token": "local-test-token"}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.setenv("ENGINE_API_TOKEN", "local-test-token")

    def configure(site_url="sc-domain:example.com"):
        # A file, not :memory: — every request builds a fresh engine.
        settings = Settings(_env_file=None, gsc_site_url=site_url,
                            database_url=f"sqlite:///{tmp_path}/t.db")
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
    assert body["rows"] == [{"query": "seo", "clicks": 4, "impressions": 40,
                             "position": 3.0, "previous_position": 5.0,
                             "position_delta": -2.0}]


@pytest.mark.parametrize("params", ["days=0", "days=241", "limit=0", "limit=501"])
def test_422_when_out_of_range(setup, params):
    setup()
    resp = TestClient(app_module.app).get(f"/sense/rankings?{params}", headers=TOKEN)
    assert resp.status_code == 422


@pytest.mark.parametrize("params", ["days=240", "limit=500", "days=240&limit=500"])
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
