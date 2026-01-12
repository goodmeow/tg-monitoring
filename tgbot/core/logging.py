# This file is part of tg-monitoring.
#
# tg-monitoring is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tg-monitoring is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tg-monitoring. If not, see <https://www.gnu.org/licenses/>.
#
# Author: Claude (Anthropic AI Assistant)
# Co-author: goodmeow (Harun Al Rasyid) <aarunalr@pm.me>

from __future__ import annotations

import logging
import os
from typing import Optional


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """Initialize root logging once and return package logger.

    Level can be provided via argument or env `LOG_LEVEL` (default INFO).
    """
    lvl = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()
    
    handlers = [logging.StreamHandler()]
    
    # Determine log file path
    log_file = "logs/tgbot.log"
    if os.path.exists("/app/logs"):
        log_file = "/app/logs/tgbot.log"
    
    # Ensure directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception:
            pass  # Fallback to stream only if cannot create dir

    try:
        handlers.append(logging.FileHandler(log_file))
        print(f"Logging to file: {log_file}")
    except Exception as e:
        print(f"Failed to setup file logging to {log_file}: {e}")

    logging.basicConfig(
        level=getattr(logging, lvl, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    return logging.getLogger("tgbot")

