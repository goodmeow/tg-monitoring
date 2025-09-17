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

from typing import Any, List
from aiogram import Router

from tgbot.modules.base import Module as BaseModule
from tgbot.services.qrcode_service import QrCodeService


class Module(BaseModule):
    name = "qrcode"

    def routers(self) -> List[Router]:
        self.service = QrCodeService(self.ctx.cfg)
        return [self.service.build_router()]

    def tasks(self, ctx: Any) -> List:
        return []

