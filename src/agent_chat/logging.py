from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import APP_DIR

LOG_DIR = APP_DIR / "logs"
LOG_FILE = LOG_DIR / "ac.log"


def setup_logging(verbose: bool = False) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("agent_chat")
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if verbose:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logger.addHandler(stream)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "agent_chat")
