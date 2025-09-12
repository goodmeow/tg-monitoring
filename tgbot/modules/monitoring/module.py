from __future__ import annotations

from typing import Any, List, Coroutine
from aiogram import Router

from tgbot.modules.base import Module as BaseModule
from tgbot.services.monitoring_service import MonitoringService


class Module(BaseModule):
    name = "monitoring"

    def routers(self) -> List[Router]:
        self.service = MonitoringService(self.ctx.cfg, self.ctx.stores["state"])  # type: ignore[attr-defined]
        return [self.service.build_router()]

    def tasks(self, ctx: Any) -> List[Coroutine[Any, Any, None]]:
        return [self.service.run_loop(self.ctx.bot)]
