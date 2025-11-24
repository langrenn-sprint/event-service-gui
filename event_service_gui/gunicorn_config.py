"""Gunicorn module for hosting an aiohttp server."""

import logging
import multiprocessing
import sys
from os import environ as env
from typing import Any

from dotenv import load_dotenv
from gunicorn import glogging
from pythonjsonlogger.json import JsonFormatter

load_dotenv()

HOST_PORT = env.get("HOST_PORT", "8080")
DEBUG_MODE = env.get("DEBUG_MODE", None)
LOGGING_LEVEL = env.get("LOGGING_LEVEL", "INFO")

# Gunicorn config
bind = ":" + HOST_PORT
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2 * multiprocessing.cpu_count()
logging_level = str(LOGGING_LEVEL)
accesslog = "-"

# Need to override the logger to remove healthcheck (ping) form accesslog


class StackdriverJsonFormatter(JsonFormatter):
    """json log formatter."""

    def __init__(
        self,
        fmt: str = "%(levelname) %(message)",
        style: str = "%",
        *args,  # noqa: ANN002
        **kwargs,  # noqa: ANN003
    ) -> None:
        """Initialize the StackdriverJsonFormatter."""
        _ = style
        JsonFormatter.__init__(
            self,
            *args,
            **kwargs,
            fmt=fmt,
        )

    def process_log_record(self, log_data) -> dict:
        """Process log record."""
        log_data["severity"] = log_data["levelname"]
        del log_data["levelname"]
        log_data["serviceContext"] = {"service": "event-service-gui"}
        return super().process_log_record(log_data)


# Override the logger to remove healthcheck (ping) from the access log and format logs as json
class CustomGunicornLogger(glogging.Logger):
    """Custom Gunicorn Logger class."""

    def setup(self, cfg: Any) -> None:
        """Set up function."""
        super().setup(cfg)

        access_logger = logging.getLogger("gunicorn.access")
        access_logger.addFilter(PingFilter())
        access_logger.addFilter(ReadyFilter())

        root_logger = logging.getLogger()
        root_logger.setLevel(logging_level)

        other_loggers = [
            "gunicorn",
            "gunicorn.error",
            "gunicorn.http",
            "gunicorn.http.wsgi",
        ]
        loggers = [logging.getLogger(name) for name in other_loggers]
        loggers.append(root_logger)
        loggers.append(access_logger)

        json_handler = logging.StreamHandler(sys.stdout)
        json_handler.setFormatter(StackdriverJsonFormatter())

        for logger in loggers:
            for handler in logger.handlers:
                logger.removeHandler(handler)
            logger.addHandler(json_handler)


class PingFilter(logging.Filter):
    """Custom Ping Filter class."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter function."""
        return "GET /ping" not in record.getMessage()


class ReadyFilter(logging.Filter):
    """Custom Ready Filter class."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter function."""
        return "GET /ready" not in record.getMessage()


logger_class = CustomGunicornLogger
