from __future__ import annotations

import asyncio
import os
import importlib
from dataclasses import dataclass
from typing import Any, Dict, List, Coroutine

from aiogram import Bot, Dispatcher

from monitor.config import Config
from monitor.state import StateStore
from monitor.rss_store import RssStore


@dataclass
class AppContext:
    cfg: Config
    bot: Bot
    dp: Dispatcher
    stores: Dict[str, Any]
    clients: Dict[str, Any]


class App:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.bot = Bot(cfg.bot_token)
        self.dp = Dispatcher()
        self.ctx = AppContext(
            cfg=cfg,
            bot=self.bot,
            dp=self.dp,
            stores={},
            clients={},
        )

        # Default stores (reuse existing implementations)
        self.ctx.stores["state"] = StateStore(cfg.state_file)
        self.ctx.stores["rss"] = RssStore(cfg.rss_store_file)

        self.modules = []  # type: List[Any]
        self._tasks: List[asyncio.Task] = []

    def _import_symbol(self, path: str):
        mod_name, _, sym = path.partition(":")
        if not sym:
            raise ImportError(f"Invalid module path spec (missing symbol): {path}")
        mod = importlib.import_module(mod_name)
        return getattr(mod, sym)

    def _load_module(self, name: str):
        # Accept dotted path with :Symbol or shorthand name
        spec = name
        if ":" not in spec and "." not in spec:
            # shorthand -> tgbot.modules.<name>.module:Module
            spec = f"tgbot.modules.{name}.module:Module"
        cls = self._import_symbol(spec)
        return cls(self.ctx)

    async def _start_modules(self):
        # Load modules from env
        raw = os.environ.get("MODULES", "monitoring,rss")
        names = [n.strip() for n in raw.split(",") if n.strip()]
        for n in names:
            m = self._load_module(n)
            self.modules.append(m)

        # Startup hooks, register routers, spawn tasks
        for m in self.modules:
            if hasattr(m, "on_startup"):
                await m.on_startup(self.ctx)
            for r in (m.routers() or []):
                self.dp.include_router(r)
            for c in (m.tasks(self.ctx) or []):
                self._tasks.append(asyncio.create_task(c))

    async def _stop_modules(self):
        # Cancel background tasks
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            with asyncio.CancelledError:  # type: ignore
                try:
                    await t
                except Exception:
                    pass
        self._tasks.clear()

        # Shutdown hooks
        for m in self.modules:
            if hasattr(m, "on_shutdown"):
                try:
                    await m.on_shutdown(self.ctx)
                except Exception:
                    pass

    async def run(self):
        await self._start_modules()
        try:
            await self.dp.start_polling(self.bot, allowed_updates=["message"])  # keep simple
        finally:
            await self._stop_modules()

