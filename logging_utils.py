"""Structured logging helpers."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from settings import LOG_DIR

_LOG_INITIALIZED = False


def configure_logging() -> None:
    global _LOG_INITIALIZED
    if _LOG_INITIALIZED:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    handlers.append(logging.FileHandler(Path(LOG_DIR) / "watcher.log"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=handlers,
        force=True,
    )
    _LOG_INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
