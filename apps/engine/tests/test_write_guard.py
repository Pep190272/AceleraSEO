"""Write endpoints refuse demo-mode and unauthenticated calls before doing any work.

Every guarded route is exercised with the dependency alone: a refused call must
never reach settings, the database, a managed site or an external index. Calls
that do pass the guard hit a tripwire on get_settings(), and the overrides file
points at a temporary path, since POST /settings writes it before that call.
"""
import pytest
from fastapi.testclient import TestClient

import aceleraseo.infrastructure.settings_store as settings_store
import aceleraseo.interfaces.api.app as app_module

# (method, path, json body) for every endpoint that changes state.
WRITE_ENDPOINTS = [
    ("post", "/settings", {"values": {"autonomy_mode": "none"}}),
    ("post", "/sense/run", None),
    ("put", "/cms/pages", {"url": "/", "h1": "Heading"}),
    ("post", "/act/indexnow", {"urls": ["https://example.com/"]}),
    ("post", "/act/proposals/1/approved", None),
]


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    # _OVERRIDES_PATH is read at import time, so patch the attribute, not the env var.
    monkeypatch.setattr(settings_store, "_OVERRIDES_PATH", str(tmp_path / "overrides.json"))
    monkeypatch.delenv("ENGINE_API_TOKEN", raising=False)

    def tripwire(*args, **kwargs):
        raise AssertionError("a refused write reached get_settings()")

    monkeypatch.setattr(app_module, "get_settings", tripwire)
    # /audit/run builds a crawler instead of reading settings: trip that too.
    monkeypatch.setattr(app_module, "HttpxCrawler", tripwire)
    return TestClient(app_module.app, raise_server_exceptions=False)


def _call(client, method, path, body, headers=None):
    return getattr(client, method)(path, json=body, headers=headers or {})


@pytest.mark.parametrize("method,path,body", WRITE_ENDPOINTS)
def test_write_endpoints_are_forbidden_in_demo_mode(client, monkeypatch, method, path, body):
    monkeypatch.setenv("DEMO_MODE", "true")
    res = _call(client, method, path, body)
    assert res.status_code == 403
    assert "demo" in res.json()["detail"].lower()


@pytest.mark.parametrize("method,path,body", WRITE_ENDPOINTS)
def test_write_endpoints_require_the_token_when_one_is_set(client, monkeypatch, method, path, body):
    monkeypatch.setenv("ENGINE_API_TOKEN", "local-test-token")
    assert _call(client, method, path, body).status_code == 401
    wrong = _call(client, method, path, body, {"X-Engine-Token": "wrong"})
    assert wrong.status_code == 401


@pytest.mark.parametrize("method,path,body", WRITE_ENDPOINTS)
def test_demo_mode_wins_even_with_a_valid_token(client, monkeypatch, method, path, body):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ENGINE_API_TOKEN", "local-test-token")
    res = _call(client, method, path, body, {"X-Engine-Token": "local-test-token"})
    assert res.status_code == 403


@pytest.mark.parametrize("method,path,body", WRITE_ENDPOINTS)
def test_a_valid_token_passes_the_guard(client, monkeypatch, method, path, body):
    monkeypatch.setenv("ENGINE_API_TOKEN", "local-test-token")
    # Past the guard, the handler calls get_settings(), which is the tripwire:
    # a 500 here proves the guard let the call through.
    res = _call(client, method, path, body, {"X-Engine-Token": "local-test-token"})
    assert res.status_code == 500


@pytest.mark.parametrize("method,path,body", WRITE_ENDPOINTS)
def test_without_a_token_configured_writes_fail_closed(client, method, path, body):
    res = _call(client, method, path, body)
    assert res.status_code == 503
    assert "ENGINE_API_TOKEN" in res.json()["detail"]


# (method, path, json body, query) for endpoints that change no state but spend a
# provider's quota or fetch URLs: token only, and demo mode must NOT block them.
COSTLY_ENDPOINTS = [
    ("post", "/settings/verify-llm", None, None),
    ("post", "/settings/verify-cms", None, None),
    ("post", "/audit/run", None, {"start_url": "https://example.com/"}),
    ("post", "/strategy/discover", {"business_description": "Plumber"}, None),
    ("post", "/strategy/preview", {"keywords": []}, None),
    ("post", "/competitors/analyze", {"domain": "example.com"}, None),
]


@pytest.mark.parametrize("method,path,body,query", COSTLY_ENDPOINTS)
def test_costly_endpoints_require_the_token_when_one_is_set(client, monkeypatch, method, path, body, query):
    monkeypatch.setenv("ENGINE_API_TOKEN", "local-test-token")
    res = getattr(client, method)(path, json=body, params=query)
    assert res.status_code == 401


@pytest.mark.parametrize("method,path,body,query", COSTLY_ENDPOINTS)
def test_costly_endpoints_stay_available_in_demo_mode(client, monkeypatch, method, path, body, query):
    # The public demo relies on these; the guard must not answer for them.
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ENGINE_API_TOKEN", "local-test-token")
    res = getattr(client, method)(path, json=body, params=query,
                                  headers={"X-Engine-Token": "local-test-token"})
    assert res.status_code not in (401, 403)


@pytest.mark.parametrize("method,path,body,query", COSTLY_ENDPOINTS)
def test_without_a_token_configured_costly_endpoints_fail_closed(client, method, path, body, query):
    res = getattr(client, method)(path, json=body, params=query)
    assert res.status_code == 503
    assert "ENGINE_API_TOKEN" in res.json()["detail"]


def test_startup_warns_when_no_token_is_configured(monkeypatch, caplog):
    from aceleraseo.interfaces.api.guards import warn_if_token_missing

    monkeypatch.delenv("ENGINE_API_TOKEN", raising=False)
    with caplog.at_level("WARNING"):
        warn_if_token_missing()
    assert "ENGINE_API_TOKEN" in caplog.text


def test_every_state_changing_route_is_guarded():
    """Every PUT/PATCH/DELETE and every POST must carry one of the two guards, and
    the listed endpoints must carry the right one — so a new route cannot ship open."""
    writes = {(m.upper(), p) for m, p, _ in WRITE_ENDPOINTS}
    costly = {(m.upper(), p) for m, p, _, _ in COSTLY_ENDPOINTS}
    for route in app_module.app.routes:
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        calls = {d.call for d in dependant.dependencies}
        concrete_path = route.path.replace("{proposal_id}", "1").replace("{status}", "approved")
        for method in route.methods:
            key = (method, concrete_path)
            if key in writes or method in {"PUT", "PATCH", "DELETE"}:
                assert app_module.require_write_access in calls, f"{method} {route.path} needs the write guard"
            elif key in costly:
                assert app_module.require_token in calls, f"{method} {route.path} needs the token guard"
            elif method == "POST":
                raise AssertionError(f"POST {route.path} is not classified as a write or costly endpoint")
