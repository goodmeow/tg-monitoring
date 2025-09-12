from __future__ import annotations

import logging
import os
from typing import Optional


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """Initialize root logging once and return package logger.

    Level can be provided via argument or env `LOG_LEVEL` (default INFO).
    """
    lvl = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=getattr(logging, lvl, logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    else:
        logging.getLogger().setLevel(getattr(logging, lvl, logging.INFO))
    return logging.getLogger("tgbot")

