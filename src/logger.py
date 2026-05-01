"""
Logging Configuration
======================
Sets up color-coded, structured console logging for the entire application.
Call `setup_logging()` once at startup before any other imports log messages.
"""

import logging
import sys

from src.config import settings

# Attempt to use colorlog for rich console output; fall back to plain logging
try:
    import colorlog

    _HAS_COLORLOG = True
except ImportError:
    _HAS_COLORLOG = False


def setup_logging() -> None:
    """
    Configure the root logger with a colored console handler.

    Uses colorlog if available for color-coded log levels:
      - DEBUG:    cyan
      - INFO:     green
      - WARNING:  yellow
      - ERROR:    red
      - CRITICAL: bold red

    Falls back to standard logging if colorlog is not installed.
    """
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    if _HAS_COLORLOG:
        formatter = colorlog.ColoredFormatter(
            fmt=(
                "%(log_color)s%(asctime)s │ %(levelname)-8s │ "
                "%(name)-28s │ %(message)s%(reset)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    else:
        formatter = logging.Formatter(
            fmt=(
                "%(asctime)s │ %(levelname)-8s │ "
                "%(name)-28s │ %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.info("Logging initialized (level=%s).", settings.LOG_LEVEL)
