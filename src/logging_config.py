"""
logging_config.py
=================
Structured logging setup for Pune Convex Mirror Atlas.

Usage
-----
    from src.logging_config import setup_logging, get_logger
    setup_logging(level="INFO")
    log = get_logger(__name__)
    log.info("Application started")

Rules
-----
- NEVER log API key values (even partially).
- Log all API requests by URL template (not full URL with key).
- Use structured fields where possible.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
) -> None:
    """
    Configure root logger with console (and optionally file) handlers.

    Parameters
    ----------
    level:    Log level string — DEBUG, INFO, WARNING, ERROR.
    log_file: If provided, also write structured logs to this file.
    """
    global _configured

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = []

    # Console handler — writes to stderr
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(numeric_level)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    handlers.append(console)

    # Optional file handler
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(numeric_level)
        fh.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        handlers.append(fh)

    logging.basicConfig(level=numeric_level, handlers=handlers, force=True)

    # Silence noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Call setup_logging() before using it."""
    return logging.getLogger(name)
