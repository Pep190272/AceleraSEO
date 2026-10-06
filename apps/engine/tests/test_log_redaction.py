"""The access log must never carry the OAuth one-time code or state."""
import logging

from aceleraseo.interfaces.api.log_redaction import (
    ACCESS_LOGGER,
    RedactQueryFilter,
    install_access_log_redaction,
)


def _access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        ACCESS_LOGGER, logging.INFO, __file__, 1,
        '%s - "%s %s HTTP/%s" %d', ("127.0.0.1:5000", "GET", path, "1.1", 303), None,
    )


def test_redacts_code_and_state_keeping_names() -> None:
    record = _access_record("/auth/google/callback?state=abc&code=4/0ASECRET&scope=x")
    assert RedactQueryFilter().filter(record)
    line = record.getMessage()
    assert "4/0ASECRET" not in line and "abc" not in line
    assert "?state=[redacted]&code=[redacted]&scope=x" in line


def test_redacts_token_and_key_like_params() -> None:
    record = _access_record("/x?access_token=t1&api_key=k1&page=2")
    RedactQueryFilter().filter(record)
    assert record.getMessage().count("[redacted]") == 2
    assert "page=2" in record.getMessage()


def test_leaves_unrelated_paths_untouched() -> None:
    for path in ("/health", "/sense/rankings?days=90&decode=1&keyword=seo&keys=a"):
        record = _access_record(path)
        RedactQueryFilter().filter(record)
        assert path in record.getMessage()


def test_install_is_idempotent() -> None:
    install_access_log_redaction()
    install_access_log_redaction()
    filters = logging.getLogger(ACCESS_LOGGER).filters
    assert sum(isinstance(f, RedactQueryFilter) for f in filters) == 1
