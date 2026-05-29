from aceleraseo.infrastructure.providers.dataforseo import parse_keyword_response


def test_parse_extracts_keywords_from_response():
    data = {
        "tasks": [{
            "result": [{
                "items": [{
                    "keyword": "seo barcelona",
                    "keyword_info": {"search_volume": 1200},
                    "keyword_properties": {"keyword_difficulty": 34},
                    "search_intent_info": {"main_intent": "Commercial"},
                }]
            }]
        }]
    }
    kws = parse_keyword_response(data)
    assert len(kws) == 1
    assert kws[0].term == "seo barcelona"
    assert kws[0].search_volume == 1200
    assert kws[0].difficulty == 34.0
    assert kws[0].intent == "commercial"  # lowercased


def test_parse_is_defensive_against_missing_fields():
    data = {"tasks": [{"result": [{"items": [{"keyword": "x"}]}]}]}
    kws = parse_keyword_response(data)
    assert kws[0].search_volume == 0
    assert kws[0].difficulty == 0.0
    assert kws[0].intent == "informational"


def test_parse_handles_empty_response():
    assert parse_keyword_response({}) == []
