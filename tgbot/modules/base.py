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

from abc import ABC, abstractmethod
from typing import Any, List, Coroutine

from aiogram import Router


class Module(ABC):
    name: str = "module"

    def __init__(self, ctx: Any):
        self.ctx = ctx

    @abstractmethod
    def routers(self) -> List[Router]:
        ...

    def tasks(self, ctx: Any) -> List[Coroutine[Any, Any, None]]:
        return []

    async def on_startup(self, ctx: Any):
        pass

    async def on_shutdown(self, ctx: Any):
        pass

