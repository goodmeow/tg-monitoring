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

from typing import Any, List, Coroutine
from aiogram import Router

from tgbot.modules.base import Module as BaseModule
from tgbot.services.rss_service import RssService


class Module(BaseModule):
    name = "rss"

    def routers(self) -> List[Router]:
        self.service = RssService(
            self.ctx.cfg,
            self.ctx.stores["rss"],
            self.ctx.clients["feed"],
        )  # type: ignore[attr-defined]
        return [self.service.build_router()]

    def tasks(self, ctx: Any) -> List[Coroutine[Any, Any, None]]:
        return [
            self.service.poll_loop(),
            self.service.digest_loop(self.ctx.bot),
        ]
