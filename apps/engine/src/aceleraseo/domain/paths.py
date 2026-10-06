"""Page identity shared by Search Console rows and conversion counts."""
from __future__ import annotations

import unicodedata
from urllib.parse import unquote, urlsplit

MAX_SOURCE_PATH_LENGTH = 255


def is_plausible_path(value: object) -> bool:
    """True for a site-relative path a conversions source may report.

    Anyone can make the site record a conversion on a made-up path, so a path is
    untrusted text: at most 255 characters, starting with '/', and without
    whitespace, control characters or backslashes, before or after percent-decoding.
    """
    if not isinstance(value, str) or not 0 < len(value) <= MAX_SOURCE_PATH_LENGTH:
        return False
    # '//host/x' would parse as a host, not a path.
    if not value.startswith("/") or value.startswith("//"):
        return False
    return not any(
        ch == "\\" or ch.isspace() or unicodedata.category(ch).startswith("C")
        for ch in value + unquote(value)
    )


def normalize_path(value: str) -> str:
    """Reduce a URL or path to '/path/': decoded, leading and trailing slash, no query.

    Search Console reports full, percent-encoded URLs and the conversions sources report
    paths; both meet on this form, so '/espa%C3%B1a' and 'https://x.test/españa/'
    are the same page.
    """
    path = unquote(urlsplit(value.strip()).path) or "/"
    if not path.startswith("/"):
        path = "/" + path
    if not path.endswith("/"):
        path += "/"
    return path
