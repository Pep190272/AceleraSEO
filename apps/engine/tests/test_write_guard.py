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
def test_without_a_token_configured_local_calls_pass_the_guard(client, method, path, body):
    assert _call(client, method, path, body).status_code == 500


def test_every_state_changing_route_is_guarded():
    """A new PUT/PATCH/DELETE route, or a listed write losing its guard, fails here."""
    listed = {(method.upper(), path) for method, path, _ in WRITE_ENDPOINTS}
    for route in app_module.app.routes:
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        guarded = any(d.call is app_module.require_write_access for d in dependant.dependencies)
        concrete_path = route.path.replace("{proposal_id}", "1").replace("{status}", "approved")
        for method in route.methods:
            if method in {"PUT", "PATCH", "DELETE"} or (method, concrete_path) in listed:
                assert guarded, f"{method} {route.path} changes state but is not guarded"
