from __future__ import annotations

from typing import Any, List, Coroutine
from aiogram import Router

from tgbot.modules.base import Module as BaseModule
from tgbot.services.sticker_kang_service import StickerKangService


class Module(BaseModule):
    name = "stickers"

    def routers(self) -> List[Router]:
        self.service = StickerKangService()
        return [self.service.build_router()]

    def tasks(self, ctx: Any) -> List[Coroutine[Any, Any, None]]:
        return []

