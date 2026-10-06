"""WordPress conversions provider and source selection, against httpx.MockTransport only."""
from datetime import date

import httpx
import pytest

from aceleraseo.infrastructure.config import Settings
from aceleraseo.infrastructure.llm.factory import make_analytics, resolve_conversions_source
from aceleraseo.infrastructure.providers.wordpress_conversions import (
    WordPressConversionsError,
    WordPressConversionsProvider,
    normalize_path,
)

URL = "https://example.com/wp-json/example/v1/conversions"
BODY = {
    "from": "2026-07-08",
    "to": "2026-10-06",
    "rows": [
        {"path": "/landing/", "type": "form", "count": 2},
        {"path": "/landing", "type": "whatsapp", "count": 1},
        {"path": "/", "type": "whatsapp", "count": 0},
    ],
}


def _provider(handler) -> WordPressConversionsProvider:
    return WordPressConversionsProvider(URL, "test-key", transport=httpx.MockTransport(handler))


def test_sums_every_type_per_normalised_path_and_sends_key_and_days():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers["X-API-Key"]
        seen["days"] = request.url.params["days"]
        return httpx.Response(200, json=BODY)

    assert _provider(handler).fetch_conversions("", 90) == {"/landing/": 3.0, "/": 0.0}
    assert seen == {"key": "test-key", "days": "90"}


def test_rows_keep_the_type_and_the_reported_window():
    snapshot = _provider(lambda request: httpx.Response(200, json=BODY)).fetch_conversion_rows(90)
    assert (snapshot.window_end, snapshot.window_days) == (date(2026, 10, 6), 91)
    assert {(r.path, r.type, r.count) for r in snapshot.rows} == {
        ("/landing/", "form", 2), ("/landing/", "whatsapp", 1), ("/", "whatsapp", 0)}


@pytest.mark.parametrize(
    "status,expected,fragment",
    [(401, 502, "rejected the API key"), (403, 502, "rejected the API key"),
     (422, 502, "HTTP 422"), (429, 429, "rate limiting"), (500, 502, "HTTP 500")],
)
def test_http_errors_become_a_typed_error(status, expected, fragment):
    provider = _provider(lambda request: httpx.Response(status, text="nope"))
    with pytest.raises(WordPressConversionsError) as err:
        provider.fetch_conversions("", 30)
    assert err.value.status_code == expected
    assert fragment in str(err.value)


def test_redirects_are_not_followed_and_hint_the_final_url():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(301, headers={"Location": URL + "/"})

    with pytest.raises(WordPressConversionsError) as err:
        _provider(handler).fetch_conversions("", 30)
    assert len(calls) == 1
    assert err.value.status_code == 502
    assert "final URL" in str(err.value) and "trailing slash" in str(err.value)


def test_timeout_is_504():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(WordPressConversionsError) as err:
        _provider(handler).fetch_conversions("", 30)
    assert err.value.status_code == 504


def test_connection_failure_is_502():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(WordPressConversionsError) as err:
        _provider(handler).fetch_conversions("", 30)
    assert err.value.status_code == 502


@pytest.mark.parametrize(
    "content",
    [b"<html>cached page</html>", b'{"rows": []}',
     b'{"from": "2026-07-08", "to": "2026-10-06", "rows": [{"path": "/", "count": -1}]}',
     b'{"from": "2026-07-08", "to": "2026-10-06",'
     b' "rows": [{"path": "/", "type": "form", "count": true}]}',
     b'{"from": "2026-07-08", "to": "2026-10-06",'
     b' "rows": [{"path": "/", "type": "form", "count": "2"}]}',
     b'{"from": "2026-10-06", "to": "2026-07-08", "rows": []}',
     b'{"from": "2026-07-08", "to": "2026-10-06",'
     b' "rows": [{"path": "/", "type": "' + b"x" * 65 + b'", "count": 1}]}'],
)
def test_malformed_body_is_502(content):
    provider = _provider(lambda request: httpx.Response(200, content=content))
    with pytest.raises(WordPressConversionsError) as err:
        provider.fetch_conversions("", 30)
    assert err.value.status_code == 502


@pytest.mark.parametrize(
    "value,expected",
    [("/a/", "/a/"), ("/a", "/a/"), ("a", "/a/"), ("", "/"), ("/a/?utm=x#top", "/a/"),
     ("https://example.com/a/b?x=1", "/a/b/"), ("https://example.com", "/"),
     ("/espa%C3%B1a", "/espa\u00f1a/"), ("https://example.com/espa%C3%B1a/", "/espa\u00f1a/"),
     ("/espa\u00f1a/", "/espa\u00f1a/")],
)
def test_normalize_path(value, expected):
    assert normalize_path(value) == expected


def _settings(**values) -> Settings:
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    "values,expected",
    [({}, "none"), ({"ga4_property_id": "123"}, "ga4"),
     ({"ga4_property_id": "123", "conversions_source": "wordpress"}, "wordpress"),
     ({"conversions_source": " GA4 "}, "ga4"), ({"conversions_source": "matomo"}, "none")],
)
def test_resolve_conversions_source(values, expected):
    assert resolve_conversions_source(_settings(**values)) == expected


def test_make_analytics_selects_wordpress_only_with_url_and_key():
    wp = {"conversions_source": "wordpress", "wp_conversions_url": URL}
    assert make_analytics(_settings(**wp), None) is None
    assert make_analytics(_settings(**wp, wp_conversions_key="YOUR_KEY_HERE"), None) is None
    provider = make_analytics(_settings(**wp, wp_conversions_key="real-key"), None)
    assert isinstance(provider, WordPressConversionsProvider)


def test_make_analytics_needs_a_property_id_for_ga4():
    assert make_analytics(_settings(conversions_source="ga4"), None) is None


def test_make_analytics_returns_none_without_a_source():
    assert make_analytics(_settings(), None) is None
    assert make_analytics(_settings(conversions_source="none", ga4_property_id="1"), None) is None
