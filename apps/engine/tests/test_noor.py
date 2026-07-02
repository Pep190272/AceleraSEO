"""Tests for NoorCMSAdapter — parsers and use-cases, no network required.

All HTTP calls are mocked via httpx transport so we never hit the real Noor API.
Coverage:
  - audit parsing (parse_audit_response)
  - page list parsing (parse_pages_response + parse_page_item)
  - url_path canonicalization (_canonicalize_url_path)
  - update_page full-field send (build_update_payload)
  - keyword_h1 validation rejection (use-case UpdateSeoPage)
  - auth-error translation: 401, 403, 503 → NoorCMSError
  - 422 translation → NoorCMSError with detail
  - verify() returns True on 200, False on auth errors
"""
import pytest
import httpx

from aceleraseo.application.cms import GetSiteAudit, ListSeoPages, UpdateSeoPage, _validate_h1
from aceleraseo.domain.models import SeoPage
from aceleraseo.infrastructure.providers.noor import (
    NoorCMSAdapter,
    NoorCMSError,
    _canonicalize_url_path,
    _safe_int,
    _safe_str,
    build_update_payload,
    parse_audit_response,
    parse_page_item,
    parse_pages_response,
)


# ── _safe_int / _safe_str ─────────────────────────────────────

def test_safe_int_converts_number():
    assert _safe_int(10) == 10


def test_safe_int_handles_none():
    assert _safe_int(None) == 0


def test_safe_int_handles_empty_string():
    assert _safe_int("") == 0


def test_safe_int_handles_non_numeric():
    assert _safe_int("abc") == 0


def test_safe_str_handles_none():
    assert _safe_str(None) == ""


def test_safe_str_returns_string():
    assert _safe_str(42) == "42"


# ── _canonicalize_url_path ────────────────────────────────────

def test_canonicalize_lowercase():
    assert _canonicalize_url_path("/Servicios") == "/servicios"


def test_canonicalize_adds_leading_slash():
    assert _canonicalize_url_path("servicios") == "/servicios"


def test_canonicalize_removes_trailing_slash():
    assert _canonicalize_url_path("/servicios/") == "/servicios"


def test_canonicalize_root_path_stays_single_slash():
    assert _canonicalize_url_path("/") == "/"


def test_canonicalize_trims_whitespace():
    assert _canonicalize_url_path("  /About  ") == "/about"


def test_canonicalize_no_scheme():
    # Should not strip paths; this is only for url_path slugs
    assert _canonicalize_url_path("/Contacto/") == "/contacto"


# ── parse_audit_response ──────────────────────────────────────

_AUDIT_DATA = {
    "keywords": {
        "total": 10,
        "active": 8,
        "urls_configured": ["/home", "/about"],
        "urls_missing_meta": ["/contact"],
    },
    "textos": {"total": 5, "active": 4, "urls_configured": ["/home"]},
    "images": {
        "total": 100,
        "portfolio_images": 50,
        "portfolio_missing_alt": 3,
        "contenido_multimedia": 20,
    },
    "blog": {"total_posts": 12, "posts_without_cover": 2, "posts_without_meta": 1},
    "portfolio": {"published": 8},
}


def test_parse_audit_keywords():
    audit = parse_audit_response(_AUDIT_DATA)
    assert audit.keywords.total == 10
    assert audit.keywords.active == 8
    assert "/home" in audit.keywords.urls_configured
    assert "/contact" in audit.keywords.urls_missing_meta


def test_parse_audit_textos():
    audit = parse_audit_response(_AUDIT_DATA)
    assert audit.textos.total == 5
    assert audit.textos.active == 4
    assert "/home" in audit.textos.urls_configured


def test_parse_audit_images():
    audit = parse_audit_response(_AUDIT_DATA)
    assert audit.images.total == 100
    assert audit.images.portfolio_missing_alt == 3
    assert audit.images.contenido_multimedia == 20


def test_parse_audit_blog():
    audit = parse_audit_response(_AUDIT_DATA)
    assert audit.blog.total_posts == 12
    assert audit.blog.posts_without_meta == 1


def test_parse_audit_portfolio():
    audit = parse_audit_response(_AUDIT_DATA)
    assert audit.portfolio.published == 8


def test_parse_audit_defensive_against_empty():
    audit = parse_audit_response({})
    assert audit.keywords.total == 0
    assert audit.images.total == 0
    assert audit.blog.total_posts == 0


def test_parse_audit_defensive_against_null_sections():
    audit = parse_audit_response({"keywords": None, "blog": None})
    assert audit.keywords.total == 0
    assert audit.blog.total_posts == 0


# ── parse_page_item / parse_pages_response ────────────────────

_PAGE_ITEM = {
    "id": 1,
    "url_path": "/servicios",
    "keyword_h1": "Servicios de construcción",
    "keyword_h2": "Reformas integrales",
    "hero_title": "Construimos tu hogar",
    "meta_title": "Servicios | Noor",
    "meta_description": "Todo tipo de servicios de construcción.",
    "is_active": True,
}


def test_parse_page_item_maps_all_fields():
    page = parse_page_item(_PAGE_ITEM)
    assert page.url == "/servicios"
    assert page.h1 == "Servicios de construcción"
    assert page.h2 == "Reformas integrales"
    assert page.hero_title == "Construimos tu hogar"
    assert page.meta_title == "Servicios | Noor"
    assert page.meta_description == "Todo tipo de servicios de construcción."


def test_parse_page_item_optional_null_fields():
    item = {"url_path": "/home", "keyword_h1": "Inicio", "keyword_h2": None,
            "hero_title": None, "meta_title": None, "meta_description": None}
    page = parse_page_item(item)
    assert page.h2 is None
    assert page.hero_title is None
    assert page.meta_title is None
    assert page.meta_description is None


def test_parse_pages_response_maps_list():
    pages = parse_pages_response([_PAGE_ITEM])
    assert len(pages) == 1
    assert pages[0].url == "/servicios"


def test_parse_pages_response_empty_list():
    assert parse_pages_response([]) == []


def test_parse_pages_response_handles_none():
    assert parse_pages_response(None) == []


# ── build_update_payload ──────────────────────────────────────

def test_build_update_payload_sends_all_fields():
    page = SeoPage(
        url="/Servicios/",
        h1="Servicios",
        h2="Reformas",
        hero_title="Hero",
        meta_title="Meta",
        meta_description="Desc",
    )
    payload = build_update_payload(page)
    # url_path must be canonicalized
    assert payload["url_path"] == "/servicios"
    assert payload["keyword_h1"] == "Servicios"
    assert payload["keyword_h2"] == "Reformas"
    assert payload["hero_title"] == "Hero"
    assert payload["meta_title"] == "Meta"
    assert payload["meta_description"] == "Desc"


def test_build_update_payload_includes_none_fields():
    """Optional fields must be present even when None (full replace, not patch)."""
    page = SeoPage(url="/home", h1="Inicio")
    payload = build_update_payload(page)
    assert "keyword_h2" in payload
    assert "hero_title" in payload
    assert "meta_title" in payload
    assert "meta_description" in payload
    assert payload["keyword_h2"] is None
    assert payload["meta_title"] is None


# ── _validate_h1 (use-case validation) ───────────────────────

def test_validate_h1_accepts_valid():
    _validate_h1("Servicios de construcción")  # should not raise


def test_validate_h1_rejects_too_short():
    with pytest.raises(ValueError, match="3"):
        _validate_h1("Ab")  # only 2 non-whitespace chars


def test_validate_h1_rejects_whitespace_only():
    with pytest.raises(ValueError):
        _validate_h1("   ")


def test_validate_h1_rejects_angle_brackets():
    with pytest.raises(ValueError, match="angle brackets"):
        _validate_h1("Título <b>en negrita</b>")


def test_validate_h1_rejects_greater_than():
    with pytest.raises(ValueError, match="angle brackets"):
        _validate_h1("A > B construction")


def test_validate_h1_rejects_too_long():
    with pytest.raises(ValueError, match="60"):
        _validate_h1("A" * 61)


def test_validate_h1_exactly_3_non_ws_chars():
    _validate_h1("a b c")  # 3 non-whitespace chars — should pass


# ── HTTP transport helpers ────────────────────────────────────

class _MockTransport(httpx.BaseTransport):
    """Minimal HTTPX transport that returns a pre-canned response."""

    def __init__(self, status_code: int, json_body=None, text_body: str = ""):
        self._status = status_code
        self._json = json_body
        self._text = text_body

    def handle_request(self, request):
        import json as _json
        if self._json is not None:
            content = _json.dumps(self._json).encode()
            headers = {"Content-Type": "application/json"}
        else:
            content = self._text.encode()
            headers = {}
        return httpx.Response(self._status, content=content, headers=headers)


# ── auth error translation ────────────────────────────────────

@pytest.mark.parametrize("status_code,match_text", [
    (401, "missing"),
    (403, "rejected"),
    (503, "503"),  # W2: message covers both "no API key configured" and "unavailable"
])
def test_raise_for_noor_errors_auth(status_code, match_text):
    resp = httpx.Response(status_code, content=b'{"detail":"err"}',
                          headers={"Content-Type": "application/json"})
    with pytest.raises(NoorCMSError, match=match_text):
        NoorCMSAdapter._raise_for_noor_errors(resp)


def test_raise_for_noor_errors_422_includes_detail():
    resp = httpx.Response(422, content=b'{"detail":"url_path must be unique"}',
                          headers={"Content-Type": "application/json"})
    with pytest.raises(NoorCMSError, match="url_path must be unique"):
        NoorCMSAdapter._raise_for_noor_errors(resp)


def test_raise_for_noor_errors_200_does_not_raise():
    # httpx.Response at 200 does not call raise_for_status — our helper must not raise
    with httpx.Client(transport=_MockTransport(200, json_body={"ok": True})) as client:
        resp = client.get("http://test/api/seo/audit")
    NoorCMSAdapter._raise_for_noor_errors(resp)  # must not raise


# ── adapter.get_audit (mocked transport) ─────────────────────
# We patch the adapter's _get/_put methods to use httpx.Client with a mock
# transport rather than the real HTTP stack.  Using httpx.Client(transport=...)
# is the supported way to inject a transport; the top-level httpx.get() does
# not accept a 'transport' keyword argument.

def _make_get_patch(transport):
    def patched(self, path):
        with httpx.Client(transport=transport) as client:
            resp = client.get(f"{self._base}{path}", headers=self._headers,
                              timeout=self._timeout)
        NoorCMSAdapter._raise_for_noor_errors(resp)
        return resp
    return patched


def _make_put_patch(transport, captured: dict | None = None):
    def patched(self, path, payload):
        if captured is not None:
            captured.update(payload)
        with httpx.Client(transport=transport) as client:
            resp = client.put(f"{self._base}{path}", headers=self._headers,
                              json=payload, timeout=self._timeout)
        NoorCMSAdapter._raise_for_noor_errors(resp)
        return resp
    return patched


def test_adapter_get_audit(monkeypatch):
    monkeypatch.setattr(NoorCMSAdapter, "_get", _make_get_patch(_MockTransport(200, json_body=_AUDIT_DATA)))
    adapter = NoorCMSAdapter("http://test", "key")
    audit = adapter.get_audit()
    assert audit.keywords.total == 10
    assert audit.blog.total_posts == 12


def test_adapter_list_pages(monkeypatch):
    monkeypatch.setattr(NoorCMSAdapter, "_get", _make_get_patch(_MockTransport(200, json_body=[_PAGE_ITEM])))
    adapter = NoorCMSAdapter("http://test", "key")
    pages = adapter.list_pages()
    assert len(pages) == 1
    assert pages[0].url == "/servicios"


def test_adapter_update_page_sends_all_fields(monkeypatch):
    """update_page must send ALL SeoPage fields (replace semantics)."""
    captured_payload: dict = {}
    monkeypatch.setattr(
        NoorCMSAdapter, "_put",
        _make_put_patch(_MockTransport(200, json_body={"action": "updated", "url_path": "/servicios"}),
                        captured=captured_payload)
    )
    adapter = NoorCMSAdapter("http://test", "key")
    page = SeoPage(url="/servicios", h1="Servicios", h2="Reformas",
                   hero_title=None, meta_title="Meta", meta_description=None)
    result = adapter.update_page(page)
    assert result["action"] == "updated"
    # All optional keys must be present in the payload — even None ones
    assert "keyword_h2" in captured_payload
    assert "hero_title" in captured_payload
    assert "meta_description" in captured_payload
    assert captured_payload["keyword_h2"] == "Reformas"
    assert captured_payload["hero_title"] is None


def test_adapter_verify_succeeds_on_200(monkeypatch):
    """verify() must return without raising when the probe call succeeds."""
    monkeypatch.setattr(NoorCMSAdapter, "_get", _make_get_patch(_MockTransport(200, json_body=_AUDIT_DATA)))
    NoorCMSAdapter("http://test", "key").verify()  # must not raise


def test_adapter_verify_raises_noor_cms_error_on_auth_error(monkeypatch):
    """verify() must propagate NoorCMSError on auth failures (no swallowing)."""
    monkeypatch.setattr(NoorCMSAdapter, "_get", _make_get_patch(_MockTransport(403, json_body={"detail": "Invalid API key"})))
    with pytest.raises(NoorCMSError):
        NoorCMSAdapter("http://test", "key").verify()


# ── UpdateSeoPage use-case ────────────────────────────────────

class _FakeCMS:
    def __init__(self, pages=None):
        self._pages = pages or []
        self.last_update: SeoPage | None = None

    def get_audit(self):
        from aceleraseo.domain.models import (
            BlogStats, ImageStats, KeywordStats, PortfolioStats, SeoAudit, TextStats
        )
        return SeoAudit(
            keywords=KeywordStats(total=0, active=0),
            textos=TextStats(total=0, active=0),
            images=ImageStats(total=0, portfolio_images=0, portfolio_missing_alt=0,
                              contenido_multimedia=0),
            blog=BlogStats(total_posts=0, posts_without_cover=0, posts_without_meta=0),
            portfolio=PortfolioStats(published=0),
        )

    def list_pages(self):
        return self._pages

    def update_page(self, page):
        self.last_update = page
        return {"action": "updated", "url_path": page.url}

    def verify(self):
        return True


def test_update_seo_page_delegates_to_cms():
    cms = _FakeCMS()
    page = SeoPage(url="/servicios", h1="Servicios válidos")
    result = UpdateSeoPage(cms).execute(page)
    assert result["action"] == "updated"
    assert cms.last_update is page


def test_update_seo_page_rejects_short_h1():
    cms = _FakeCMS()
    page = SeoPage(url="/x", h1="Ab")
    with pytest.raises(ValueError):
        UpdateSeoPage(cms).execute(page)


def test_update_seo_page_rejects_angle_brackets_in_h1():
    cms = _FakeCMS()
    page = SeoPage(url="/x", h1="<script>")
    with pytest.raises(ValueError, match="angle brackets"):
        UpdateSeoPage(cms).execute(page)


def test_list_seo_pages_delegates_to_cms():
    page = SeoPage(url="/home", h1="Inicio")
    cms = _FakeCMS(pages=[page])
    result = ListSeoPages(cms).execute()
    assert result == [page]


def test_get_site_audit_delegates_to_cms():
    cms = _FakeCMS()
    audit = GetSiteAudit(cms).execute()
    assert audit.keywords.total == 0


# ── W4: non-JSON response raises NoorCMSError ─────────────────


class _NonJsonTransport(httpx.BaseTransport):
    """Transport that returns a 200 with an HTML (non-JSON) body."""

    def handle_request(self, request):
        content = b"<html><body>Error</body></html>"
        return httpx.Response(200, content=content, headers={"Content-Type": "text/html"})


def test_get_audit_non_json_response_raises_noor_error(monkeypatch):
    monkeypatch.setattr(NoorCMSAdapter, "_get", _make_get_patch(_NonJsonTransport()))
    adapter = NoorCMSAdapter("http://test", "key")
    with pytest.raises(NoorCMSError, match="non-JSON"):
        adapter.get_audit()


# ── N4: verify_cms (factory) ──────────────────────────────────


def _make_verify_cms_settings(base_url: str = "http://noor.test", api_key: str = "real-key"):
    """Return a minimal Settings-like object for verify_cms tests."""
    from aceleraseo.infrastructure.config import Settings
    return Settings(
        noor_base_url=base_url,
        noor_api_key=api_key,
        # suppress pydantic-settings from reading from the environment
        _env_file=None,
    )


def test_verify_cms_success(monkeypatch):
    """verify_cms returns ok=True with a friendly message on a 200 response."""
    from aceleraseo.infrastructure.llm.factory import verify_cms

    monkeypatch.setattr(NoorCMSAdapter, "_get", _make_get_patch(_MockTransport(200, json_body=_AUDIT_DATA)))
    result = verify_cms(_make_verify_cms_settings())
    assert result["ok"] is True
    assert "http://noor.test" in result["detail"]


def test_verify_cms_invalid_key_403(monkeypatch):
    """verify_cms returns ok=False with auth detail on a 403 (invalid key)."""
    from aceleraseo.infrastructure.llm.factory import verify_cms

    monkeypatch.setattr(NoorCMSAdapter, "_get", _make_get_patch(_MockTransport(403, json_body={"detail": "Bad key"})))
    result = verify_cms(_make_verify_cms_settings())
    assert result["ok"] is False
    # The 403 NoorCMSError message mentions "rejected" (per _raise_for_noor_errors)
    assert "rejected" in result["detail"].lower() or "403" in result["detail"]


def test_verify_cms_503_unavailable(monkeypatch):
    """verify_cms returns ok=False with a message covering both causes of a 503."""
    from aceleraseo.infrastructure.llm.factory import verify_cms

    monkeypatch.setattr(NoorCMSAdapter, "_get", _make_get_patch(_MockTransport(503, text_body="Service Unavailable")))
    result = verify_cms(_make_verify_cms_settings())
    assert result["ok"] is False
    # The 503 message must mention both "unavailable" and "API key"
    detail_lower = result["detail"].lower()
    assert "503" in detail_lower or "unavailable" in detail_lower


def test_verify_cms_network_failure(monkeypatch):
    """verify_cms returns ok=False mentioning it could not reach Noor on network errors."""
    from aceleraseo.infrastructure.llm.factory import verify_cms
    import httpx

    def _raise_network(self, path):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(NoorCMSAdapter, "_get", _raise_network)
    result = verify_cms(_make_verify_cms_settings())
    assert result["ok"] is False
    assert "noor" in result["detail"].lower() or "http://noor.test" in result["detail"]


def test_verify_cms_unconfigured_base_url():
    """verify_cms returns ok=False immediately when noor_base_url is blank."""
    from aceleraseo.infrastructure.llm.factory import verify_cms
    from aceleraseo.infrastructure.config import Settings

    settings = Settings(noor_base_url="", noor_api_key="some-key", _env_file=None)
    result = verify_cms(settings)
    assert result["ok"] is False
    assert "base URL" in result["detail"] or "url" in result["detail"].lower()


def test_verify_cms_unconfigured_api_key():
    """verify_cms returns ok=False immediately when noor_api_key is blank."""
    from aceleraseo.infrastructure.llm.factory import verify_cms
    from aceleraseo.infrastructure.config import Settings

    settings = Settings(noor_base_url="http://noor.test", noor_api_key="", _env_file=None)
    result = verify_cms(settings)
    assert result["ok"] is False
    assert "key" in result["detail"].lower()


# ── N1: _validate_h1 whitespace edge-cases ────────────────────


def test_validate_h1_rejects_newline_padded():
    """Newline-only content must fail — \\n is whitespace."""
    with pytest.raises(ValueError):
        _validate_h1("\n\n\n")


def test_validate_h1_rejects_nbsp_padded():
    """Non-breaking space (\\xa0) padding must be stripped before the length check."""
    with pytest.raises(ValueError):
        _validate_h1("\xa0\xa0")


def test_validate_h1_rejects_mixed_whitespace_short():
    """A mix of whitespace chars yielding fewer than 3 real chars must fail."""
    with pytest.raises(ValueError):
        _validate_h1("a\nb")  # only 2 non-whitespace chars
