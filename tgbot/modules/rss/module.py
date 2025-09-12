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
