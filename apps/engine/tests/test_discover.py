from aceleraseo.application.discover import DiscoverKeywords
from aceleraseo.domain.models import Keyword
from aceleraseo.infrastructure.llm.discoverer import parse_keywords_json


class FakeDiscoverer:
    def __init__(self, kws):
        self._kws = kws

    def discover(self, description, location, language, max_keywords=20):
        return self._kws


class FakeMarket:
    """Returns real metrics for one of the two terms."""
    def keyword_metrics(self, terms, location):
        return [Keyword(term="plumber barcelona", search_volume=999,
                        difficulty=42, intent="commercial")]


def _llm_kws():
    return [
        Keyword("plumber barcelona", 100, 10, "transactional"),   # LLM estimate
        Keyword("emergency plumber", 50, 5, "transactional"),
    ]


def test_discover_without_market_returns_llm_estimates():
    out = DiscoverKeywords(FakeDiscoverer(_llm_kws())).execute("plumbing in BCN")
    assert [k.term for k in out] == ["plumber barcelona", "emergency plumber"]
    assert out[0].search_volume == 100  # LLM estimate kept


def test_market_enrichment_overrides_estimates():
    out = DiscoverKeywords(FakeDiscoverer(_llm_kws()), FakeMarket()).execute("plumbing")
    enriched = next(k for k in out if k.term == "plumber barcelona")
    assert enriched.search_volume == 999   # real metric replaced the estimate
    assert enriched.difficulty == 42
    assert enriched.intent == "transactional"  # LLM intent kept


def test_market_failure_falls_back_to_estimates():
    class Boom:
        def keyword_metrics(self, terms, location):
            raise RuntimeError("api down")

    out = DiscoverKeywords(FakeDiscoverer(_llm_kws()), Boom()).execute("x")
    assert out[0].search_volume == 100  # fell back, no crash


# ── JSON parser robustness ─────────────────────────────────────
def test_parse_plain_json_array():
    text = '[{"term":"a","search_volume":10,"difficulty":5,"intent":"commercial"}]'
    kws = parse_keywords_json(text)
    assert kws[0].term == "a" and kws[0].search_volume == 10


def test_parse_strips_markdown_fences_and_prose():
    text = 'Here you go:\n```json\n[{"term":"b","search_volume":3,"difficulty":2,"intent":"x"}]\n```'
    kws = parse_keywords_json(text)
    assert kws[0].term == "b"
    assert kws[0].intent == "informational"  # invalid intent normalised


def test_parse_handles_garbage():
    assert parse_keywords_json("not json at all") == []


def test_parse_clamps_difficulty_and_skips_empty_terms():
    text = '[{"term":"","search_volume":1,"difficulty":5,"intent":"x"},{"term":"ok","difficulty":500}]'
    kws = parse_keywords_json(text)
    assert len(kws) == 1
    assert kws[0].term == "ok"
    assert kws[0].difficulty == 100.0  # clamped to max
