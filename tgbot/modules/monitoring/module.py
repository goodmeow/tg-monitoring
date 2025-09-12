from __future__ import annotations

from typing import Any, List, Coroutine
from aiogram import Router

from tgbot.modules.base import Module as BaseModule

# Reuse existing monitoring logic while we migrate
from monitor.main import build_router as build_monitor_router, monitor_task


class Module(BaseModule):
    name = "monitoring"

    def routers(self) -> List[Router]:
        state = self.ctx.stores["state"]
        return [build_monitor_router(self.ctx.cfg, state)]

    def tasks(self, ctx: Any) -> List[Coroutine[Any, Any, None]]:
        state = self.ctx.stores["state"]
        return [monitor_task(self.ctx.cfg, state, self.ctx.bot)]

