import logging

from app.core.logging import RedactTokenFilter


def test_access_log_redacts_query_token() -> None:
    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:1", "GET", "/api/advisory/CASE-1/stream?access_token=eyJ.abc.def&x=1", "1.1", 200),
        None,
    )
    assert RedactTokenFilter().filter(record)
    message = record.getMessage()
    assert "eyJ" not in message
    assert "access_token=[redacted]&x=1" in message
