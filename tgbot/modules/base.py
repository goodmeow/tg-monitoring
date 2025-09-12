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

