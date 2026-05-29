import importlib

import pytest


@pytest.fixture
def store(tmp_path, monkeypatch):
    # Point the overrides file at a temp location and reload the module so the
    # module-level path constant picks it up.
    monkeypatch.setenv("SETTINGS_OVERRIDES_FILE", str(tmp_path / "ov.json"))
    import aceleraseo.infrastructure.settings_store as s
    importlib.reload(s)
    return s


def test_save_and_load_roundtrip(store):
    store.save_overrides({"gsc_site_url": "sc-domain:x.com"})
    assert store.load_overrides()["gsc_site_url"] == "sc-domain:x.com"


def test_unknown_keys_are_rejected(store):
    store.save_overrides({"gsc_site_url": "x", "evil_key": "boom"})
    loaded = store.load_overrides()
    assert "evil_key" not in loaded
    assert loaded["gsc_site_url"] == "x"


def test_empty_string_clears_an_override(store):
    store.save_overrides({"anthropic_api_key": "sk-real"})
    store.save_overrides({"anthropic_api_key": ""})
    assert "anthropic_api_key" not in store.load_overrides()


def test_describe_masks_secrets_but_shows_plain(store):
    class FakeSettings:
        gsc_site_url = "sc-domain:x.com"
        anthropic_api_key = "sk-secret-value"
        # other fields default to empty via getattr fallback
        def __getattr__(self, name):
            return ""

    rows = {r["key"]: r for r in store.describe(FakeSettings())}
    # Secret: value never echoed, but is_set reflects presence.
    assert rows["anthropic_api_key"]["value"] == ""
    assert rows["anthropic_api_key"]["is_set"] is True
    assert rows["anthropic_api_key"]["secret"] is True
    # Non-secret: value is echoed for display.
    assert rows["gsc_site_url"]["value"] == "sc-domain:x.com"
    assert rows["gsc_site_url"]["secret"] is False


def test_missing_file_loads_empty(store):
    assert store.load_overrides() == {}
