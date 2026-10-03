import logging
import re
import sys

# EventSource cannot send headers, so the SSE endpoint accepts ?access_token=<jwt>.
# Keep those bearer tokens out of the access log.
_TOKEN_IN_QUERY = re.compile(r"(access_token=)[^&\s\"]+")


class RedactTokenFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args and isinstance(record.args, tuple):
            record.args = tuple(
                _TOKEN_IN_QUERY.sub(r"\1[redacted]", arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        if isinstance(record.msg, str):
            record.msg = _TOKEN_IN_QUERY.sub(r"\1[redacted]", record.msg)
        return True


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("uvicorn.access").addFilter(RedactTokenFilter())
