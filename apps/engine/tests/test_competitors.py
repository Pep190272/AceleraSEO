"""Tests for competitor analysis — parsers and use-case, no network required."""
from aceleraseo.application.competitors import (
    MAX_COMPETITORS,
    MAX_KEYWORDS_PER_COMPETITOR,
    AnalyzeCompetitors,
)
from aceleraseo.domain.models import CompetitorDomain, RankedKeyword
from aceleraseo.infrastructure.providers.dataforseo import (
    _bare_host,
    _safe_float,
    _safe_int,
    parse_competitors_response,
    parse_ranked_keywords_response,
)


# ── _safe_int / _safe_float helpers ──────────────────────────

def test_safe_int_converts_number():
    assert _safe_int(42) == 42


def test_safe_int_handles_none():
    assert _safe_int(None) == 0


def test_safe_int_handles_empty_string():
    assert _safe_int("") == 0


def test_safe_int_handles_non_numeric_string():
    assert _safe_int("abc") == 0


def test_safe_int_uses_custom_default():
    assert _safe_int(None, default=99) == 99


def test_safe_float_converts_number():
    assert _safe_float(3.5) == 3.5


def test_safe_float_handles_none():
    assert _safe_float(None) == 0.0


def test_safe_float_handles_non_numeric_string():
    assert _safe_float("not-a-number") == 0.0


# ── _bare_host helper ─────────────────────────────────────────

def test_bare_host_strips_scheme_and_path():
    assert _bare_host("https://rival.com/some/path") == "rival.com"


def test_bare_host_already_bare():
    assert _bare_host("rival.com") == "rival.com"


def test_bare_host_strips_http():
    assert _bare_host("http://example.org") == "example.org"


# ── parse_competitors_response ────────────────────────────────

def test_parse_competitors_extracts_domains():
    data = {
        "tasks": [{
            "result": [{
                "items": [
                    {
                        "domain": "rival.com",
                        "intersections": 42,
                        "estimated_traffic": 15000,
                        "metrics": {"organic": {"pos_1": 3.5}},
                    }
                ]
            }]
        }]
    }
    comps = parse_competitors_response(data)
    assert len(comps) == 1
    assert comps[0].domain == "rival.com"
    assert comps[0].common_keywords == 42
    assert comps[0].organic_traffic == 15000
    # avg_position is always None from this parser; it's set after enrichment
    assert comps[0].avg_position is None
    assert comps[0].ranked_keywords == ()   # populated later


def test_parse_competitors_sanitizes_url_domain():
    """When 'domain' is absent but 'url' is a full URL, only the bare host is stored."""
    data = {
        "tasks": [{
            "result": [{
                "items": [{"url": "https://rival.com/page", "intersections": 1}]
            }]
        }]
    }
    comps = parse_competitors_response(data)
    assert len(comps) == 1
    assert comps[0].domain == "rival.com"


def test_parse_competitors_defensive_against_missing_fields():
    data = {"tasks": [{"result": [{"items": [{"domain": "sparse.com"}]}]}]}
    comps = parse_competitors_response(data)
    assert comps[0].common_keywords == 0
    assert comps[0].organic_traffic == 0
    assert comps[0].avg_position is None


def test_parse_competitors_skips_items_without_domain():
    data = {"tasks": [{"result": [{"items": [{"intersections": 5}]}]}]}
    comps = parse_competitors_response(data)
    assert comps == []


def test_parse_competitors_handles_empty_response():
    assert parse_competitors_response({}) == []


def test_parse_competitors_non_numeric_fields_do_not_raise():
    """Non-numeric values in numeric fields must not throw ValueError."""
    data = {
        "tasks": [{
            "result": [{
                "items": [{
                    "domain": "robust.com",
                    "intersections": "not-a-number",
                    "estimated_traffic": None,
                }]
            }]
        }]
    }
    comps = parse_competitors_response(data)
    assert comps[0].common_keywords == 0
    assert comps[0].organic_traffic == 0


# ── parse_ranked_keywords_response ───────────────────────────

def test_parse_ranked_keywords_extracts_terms():
    data = {
        "tasks": [{
            "result": [{
                "items": [{
                    "keyword_data": {
                        "keyword": "seo barcelona",
                        "keyword_info": {"search_volume": 800},
                    },
                    "ranked_serp_element": {
                        "serp_item": {"rank_absolute": 4}
                    },
                }]
            }]
        }]
    }
    kws = parse_ranked_keywords_response(data)
    assert len(kws) == 1
    assert kws[0].term == "seo barcelona"
    assert kws[0].position == 4.0
    assert kws[0].search_volume == 800


def test_parse_ranked_keywords_defensive_against_missing_fields():
    data = {"tasks": [{"result": [{"items": [{"keyword_data": {"keyword": "x"}}]}]}]}
    kws = parse_ranked_keywords_response(data)
    assert kws[0].term == "x"
    assert kws[0].position == 0.0
    assert kws[0].search_volume == 0


def test_parse_ranked_keywords_handles_empty_response():
    assert parse_ranked_keywords_response({}) == ()


def test_parse_ranked_keywords_non_numeric_does_not_raise():
    """Non-numeric position/volume values must not throw ValueError."""
    data = {
        "tasks": [{
            "result": [{
                "items": [{
                    "keyword_data": {
                        "keyword": "test",
                        "keyword_info": {"search_volume": "bad-value"},
                    },
                    "ranked_serp_element": {
                        "serp_item": {"rank_absolute": "n/a"}
                    },
                }]
            }]
        }]
    }
    kws = parse_ranked_keywords_response(data)
    assert kws[0].position == 0.0
    assert kws[0].search_volume == 0


# ── AnalyzeCompetitors use-case ───────────────────────────────

class FakeProvider:
    def __init__(self, competitors):
        self._competitors = competitors
        self.last_call: dict = {}

    def fetch_competitors(self, target, location, language, max_competitors, max_keywords_per_competitor):
        self.last_call = dict(
            target=target, location=location, language=language,
            max_competitors=max_competitors, max_keywords_per_competitor=max_keywords_per_competitor,
        )
        return self._competitors


def _make_competitor(domain="rival.com", common=5, traffic=1000, avg_pos=None, kws=()):
    return CompetitorDomain(
        domain=domain, common_keywords=common, avg_position=avg_pos,
        organic_traffic=traffic, ranked_keywords=kws,
    )


def test_analyze_competitors_delegates_to_provider():
    provider = FakeProvider([_make_competitor()])
    result = AnalyzeCompetitors(provider).execute("target.com", location="Spain")
    assert len(result) == 1
    assert result[0].domain == "rival.com"


def test_analyze_competitors_passes_correct_params():
    provider = FakeProvider([])
    AnalyzeCompetitors(provider).execute(
        "target.com", location="Spain", language="en",
        max_competitors=3, max_keywords_per_competitor=5,
    )
    assert provider.last_call["target"] == "target.com"
    assert provider.last_call["language"] == "en"
    assert provider.last_call["max_competitors"] == 3
    assert provider.last_call["max_keywords_per_competitor"] == 5


def test_analyze_competitors_clamps_max_competitors_to_ceiling():
    """Caller cannot exceed MAX_COMPETITORS even by passing a larger value."""
    provider = FakeProvider([])
    AnalyzeCompetitors(provider).execute(
        "target.com", max_competitors=MAX_COMPETITORS + 99,
    )
    assert provider.last_call["max_competitors"] == MAX_COMPETITORS


def test_analyze_competitors_clamps_max_keywords_to_ceiling():
    """Caller cannot exceed MAX_KEYWORDS_PER_COMPETITOR even by passing a larger value."""
    provider = FakeProvider([])
    AnalyzeCompetitors(provider).execute(
        "target.com", max_keywords_per_competitor=MAX_KEYWORDS_PER_COMPETITOR + 99,
    )
    assert provider.last_call["max_keywords_per_competitor"] == MAX_KEYWORDS_PER_COMPETITOR


def test_analyze_competitors_returns_empty_list_when_none_found():
    result = AnalyzeCompetitors(FakeProvider([])).execute("unknown.com")
    assert result == []


# ── avg_position computed from ranked keywords ────────────────

def test_avg_position_is_mean_of_keyword_positions():
    """avg_position must be the arithmetic mean of the competitor's keyword positions."""
    kws = (
        RankedKeyword(term="kw1", position=4.0, search_volume=100),
        RankedKeyword(term="kw2", position=10.0, search_volume=200),
        RankedKeyword(term="kw3", position=7.0, search_volume=50),
    )
    comp = _make_competitor(avg_pos=7.0, kws=kws)
    expected_avg = sum(kw.position for kw in kws) / len(kws)
    assert comp.avg_position == expected_avg


def test_avg_position_is_none_when_no_keywords():
    """avg_position must be None when the competitor has no ranked keywords."""
    comp = _make_competitor(avg_pos=None, kws=())
    assert comp.avg_position is None
