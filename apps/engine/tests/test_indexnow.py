from aceleraseo.infrastructure.providers.indexnow import build_payload


def test_payload_includes_host_key_and_urls():
    urls = ["https://x.com/a", "https://x.com/b"]
    p = build_payload("x.com", "SECRET", "https://x.com/SECRET.txt", urls)
    assert p["host"] == "x.com"
    assert p["key"] == "SECRET"
    assert p["urlList"] == urls
    assert p["keyLocation"] == "https://x.com/SECRET.txt"


def test_payload_omits_key_location_when_absent():
    p = build_payload("x.com", "SECRET", "", ["https://x.com/a"])
    assert "keyLocation" not in p
