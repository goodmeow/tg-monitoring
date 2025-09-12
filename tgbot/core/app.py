from __future__ import annotations

import asyncio
import os
import importlib
from dataclasses import dataclass
from typing import Any, Dict, List, Coroutine

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from tgbot.domain.config import Config
from tgbot.core.logging import setup_logging
from tgbot.stores.state_store import StateStore
from tgbot.stores.rss_store import RssStore
from tgbot.clients.node_exporter import NodeExporterClient
from tgbot.clients.feed_client import FeedClient


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
        self.log = setup_logging()
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

        # Default clients
        self.ctx.clients["node_exporter"] = NodeExporterClient(
            url=cfg.node_exporter_url, timeout_sec=cfg.http_timeout_sec
        )
        self.ctx.clients["feed"] = FeedClient()

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
        raw = os.environ.get("MODULES", "monitoring,rss,help,stickers")
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
        self.log.info("Modules started: %s", ", ".join(getattr(m, 'name', 'module') for m in self.modules))

        # Set bot commands (menu) for convenience
        try:
            cmds = [
                BotCommand(command="help", description="Bantuan & tombol cepat"),
                BotCommand(command="status", description="Ringkasan status server"),
                BotCommand(command="rss_add", description="Tambah langganan RSS"),
                BotCommand(command="rss_rm", description="Hapus langganan RSS"),
                BotCommand(command="rss_ls", description="Daftar langganan RSS"),
            ]
            await self.bot.set_my_commands(cmds)
        except Exception:
            self.log.warning("set_my_commands failed", exc_info=True)

    async def _stop_modules(self):
        # Cancel background tasks
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass
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
        self.log.info("Modules stopped")

    async def run(self):
        await self._start_modules()
        try:
            await self.dp.start_polling(
                self.bot,
                allowed_updates=["message", "callback_query"],
            )
        finally:
            await self._stop_modules()
