from __future__ import annotations

from typing import Any, List, Coroutine
from aiogram import Router

from tgbot.modules.base import Module as BaseModule
from tgbot.services.help_service import HelpService


class Module(BaseModule):
    name = "help"

    def routers(self) -> List[Router]:
        self.service = HelpService(
            self.ctx.cfg,
            self.ctx.clients["node_exporter"],
            self.ctx.stores["rss"],
        )  # type: ignore[attr-defined]
        return [self.service.build_router()]

    def tasks(self, ctx: Any) -> List[Coroutine[Any, Any, None]]:
        return []

