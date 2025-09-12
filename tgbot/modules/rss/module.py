from __future__ import annotations

from typing import Any, List, Coroutine
from aiogram import Router

from tgbot.modules.base import Module as BaseModule

# Reuse existing RSS logic while we migrate
from monitor.main import build_rss_router, rss_poll_task, rss_digest_task


class Module(BaseModule):
    name = "rss"

    def routers(self) -> List[Router]:
        rss = self.ctx.stores["rss"]
        return [build_rss_router(self.ctx.cfg, rss)]

    def tasks(self, ctx: Any) -> List[Coroutine[Any, Any, None]]:
        rss = self.ctx.stores["rss"]
        return [
            rss_poll_task(self.ctx.cfg, rss),
            rss_digest_task(self.ctx.cfg, rss, self.ctx.bot),
        ]

