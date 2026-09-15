"""SSRF guard for the audit crawler: only public addresses may be fetched."""
import socket

import httpx
import pytest
from fastapi.testclient import TestClient

import aceleraseo.infrastructure.providers.url_safety as url_safety
import aceleraseo.interfaces.api.app as app_module
from aceleraseo.infrastructure.providers.crawler import HttpxCrawler
from aceleraseo.infrastructure.providers.url_safety import UnsafeURLError, ensure_public_url


def _resolve_to(monkeypatch, address: str) -> None:
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    monkeypatch.setattr(
        url_safety.socket, "getaddrinfo",
        lambda *a, **k: [(family, socket.SOCK_STREAM, 6, "", (address, 80))],
    )


@pytest.mark.parametrize("address", [
    "127.0.0.1", "10.0.0.5", "172.16.3.4", "192.168.1.10", "169.254.169.254",
    "100.64.0.1", "0.0.0.0", "224.0.0.1", "::1", "fe80::1", "fc00::1", "::ffff:127.0.0.1",
])
def test_non_public_addresses_are_rejected(monkeypatch, address):
    _resolve_to(monkeypatch, address)
    with pytest.raises(UnsafeURLError):
        ensure_public_url("http://looks-public.example/")


def test_a_public_address_is_allowed(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")
    ensure_public_url("https://example.com/page")


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://example.com/", "http:///nohost", "http://example.com:99999/",
    "http://[::1/",
])
def test_non_http_or_hostless_urls_are_rejected(url):
    with pytest.raises(UnsafeURLError):
        ensure_public_url(url)


def test_unresolvable_host_is_rejected(monkeypatch):
    def fail(*a, **k):
        raise socket.gaierror("no such host")

    monkeypatch.setattr(url_safety.socket, "getaddrinfo", fail)
    with pytest.raises(UnsafeURLError):
        ensure_public_url("http://does-not-resolve.invalid/")


_TOKEN = {"X-Engine-Token": "local-test-token"}


def test_audit_run_refuses_a_private_start_url_before_crawling(monkeypatch):
    monkeypatch.setenv("ENGINE_API_TOKEN", "local-test-token")

    class Tripwire:
        def __init__(self, *a, **k):
            raise AssertionError("the crawler was built for a private URL")

    monkeypatch.setattr(app_module, "HttpxCrawler", Tripwire)
    res = TestClient(app_module.app).post(
        "/audit/run", params={"start_url": "http://127.0.0.1:8000/settings"}, headers=_TOKEN,
    )
    assert res.status_code == 400
    assert "public" in res.json()["detail"]


def test_crawler_does_not_follow_a_redirect_to_a_private_address(monkeypatch):
    addresses = {"public.example": "93.184.216.34", "internal.example": "10.0.0.7"}
    monkeypatch.setattr(
        url_safety.socket, "getaddrinfo",
        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addresses[host], 80))],
    )
    fetched = []

    def handler(request):
        fetched.append(request.url.host)
        return httpx.Response(302, headers={"location": "http://internal.example/admin"})

    crawler = HttpxCrawler()
    transport_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
        event_hooks=crawler._client.event_hooks,
    )
    crawler._client.close()
    crawler._client = transport_client
    page = crawler.fetch("http://public.example/")
    assert page.status_code == 0
    assert fetched == ["public.example"]


def test_audit_run_refuses_js_rendering_in_demo_mode(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ENGINE_API_TOKEN", "local-test-token")
    res = TestClient(app_module.app).post(
        "/audit/run", params={"start_url": "https://example.com/", "render": "true"}, headers=_TOKEN,
    )
    assert res.status_code == 403


class _FakeRoute:
    def __init__(self, url):
        self.request = type("Request", (), {"url": url})()
        self.outcome = None

    def abort(self):
        self.outcome = "aborted"

    def continue_(self):
        self.outcome = "continued"


@pytest.mark.parametrize("url,resolves_to,outcome", [
    ("http://169.254.169.254/latest/meta-data", "169.254.169.254", "aborted"),
    ("https://cdn.example/app.js", "93.184.216.34", "continued"),
    ("data:image/png;base64,AAAA", None, "continued"),
])
def test_rendering_crawler_blocks_browser_requests_to_private_hosts(monkeypatch, url, resolves_to, outcome):
    from aceleraseo.infrastructure.providers.rendering_crawler import block_private_requests

    if resolves_to:
        _resolve_to(monkeypatch, resolves_to)
    route = _FakeRoute(url)
    block_private_requests(route)
    assert route.outcome == outcome


def test_rendering_crawler_discards_a_page_reached_through_a_private_redirect(monkeypatch):
    from aceleraseo.infrastructure.providers.rendering_crawler import redirect_chain_is_public

    addresses = {"public.example": "93.184.216.34", "internal.example": "10.0.0.7"}
    monkeypatch.setattr(
        url_safety.socket, "getaddrinfo",
        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addresses[host], 80))],
    )

    def request(url, redirected_from=None):
        return type("Request", (), {"url": url, "redirected_from": redirected_from})()

    def response(req):
        return type("Response", (), {"request": req})()

    start = request("http://public.example/")
    assert redirect_chain_is_public(response(request("http://public.example/home", start)))
    assert not redirect_chain_is_public(response(request("http://internal.example/admin", start)))
