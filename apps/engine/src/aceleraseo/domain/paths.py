"""Page identity shared by Search Console rows and conversion counts."""
from __future__ import annotations

from urllib.parse import unquote, urlsplit


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
