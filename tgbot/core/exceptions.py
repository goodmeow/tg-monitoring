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

from typing import Any, Dict, Optional


class TgMonitoringError(Exception):
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.context = context or {}
        self.cause = cause

    def __str__(self) -> str:
        msg = super().__str__()
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            msg += f" (context: {ctx_str})"
        if self.cause:
            msg += f" (caused by: {self.cause})"
        return msg


class ConfigurationError(TgMonitoringError):
    pass


class ModuleError(TgMonitoringError):
    pass


class StorageError(TgMonitoringError):
    pass


class NetworkError(TgMonitoringError):
    pass


class ValidationError(TgMonitoringError):
    pass


class DatabaseError(TgMonitoringError):
    pass


class MemoryError(TgMonitoringError):
    pass