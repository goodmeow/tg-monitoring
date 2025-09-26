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

import asyncio
import contextlib
import importlib
import os
import socket
from dataclasses import dataclass
from typing import Any, Dict, List, Coroutine

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeChat

from tgbot.domain.config import Config
from tgbot.core.logging import setup_logging
from tgbot.core.database import DatabaseManager
from tgbot.version import get_version
from tgbot.stores.state_store import StateStore
from tgbot.stores.rss_store import RssStore
from tgbot.stores.state_store_v2 import HybridStateStore
from tgbot.stores.rss_store_v2 import HybridRssStore
from tgbot.clients.node_exporter import NodeExporterClient
from tgbot.clients.feed_client import FeedClient


@dataclass
class AppContext:
    cfg: Config
    bot: Bot
    dp: Dispatcher
    stores: Dict[str, Any]
    clients: Dict[str, Any]
    version: str
    db_manager: DatabaseManager


class App:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.log = setup_logging()
        self.version = get_version()
        self.log.info("tg-monitoring version: %s", self.version)
        self.bot = Bot(cfg.bot_token)
        self.dp = Dispatcher()

        # Initialize database manager
        self.db_manager = DatabaseManager(cfg)

        self.ctx = AppContext(
            cfg=cfg,
            bot=self.bot,
            dp=self.dp,
            stores={},
            clients={},
            version=self.version,
            db_manager=self.db_manager,
        )

        # Use hybrid stores (PostgreSQL with JSON fallback)
        self.ctx.stores["state"] = HybridStateStore(
            self.db_manager, cfg.state_file, cfg.memory_cache_size
        )
        self.ctx.stores["rss"] = HybridRssStore(
            self.db_manager, cfg.rss_store_file, cfg.memory_cache_size
        )

        # Default clients
        self.ctx.clients["node_exporter"] = NodeExporterClient(
            url=cfg.node_exporter_url, timeout_sec=cfg.http_timeout_sec
        )
        self.ctx.clients["feed"] = FeedClient()

        self.modules = []  # type: List[Any]
        self._tasks: List[asyncio.Task] = []
        self._startup_notice_task: asyncio.Task | None = None

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
        raw = os.environ.get("MODULES", "monitoring,rss,help,stickers,qrcode")
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
                BotCommand(command="qrcode", description="Buat QR code"),
                BotCommand(command="version", description="Info versi bot"),
            ]
            scopes = [None]
            if not self.cfg.allow_any_chat:
                seen: set[Any] = set()
                for target in self.cfg.allowed_chat_ids:
                    if target in seen or target is None:
                        continue
                    seen.add(target)
                    scopes.append(BotCommandScopeChat(chat_id=target))

            for scope in scopes:
                try:
                    await self.bot.delete_my_commands(scope=scope)
                except Exception:
                    self.log.debug("delete_my_commands failed", exc_info=True)
                await self.bot.set_my_commands(cmds, scope=scope)
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

    def _control_chat_target(self) -> Any | None:
        return self.cfg.control_chat_id or self.cfg.chat_id

    async def _send_control_message(self, text: str, target: Any | None = None) -> None:
        if target is None:
            target = self._control_chat_target()
        if not target:
            self.log.debug("No control chat configured; skipping control message: %s", text)
            return
        try:
            await self.bot.send_message(
                target,
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception:
            self.log.warning("Failed to send control message", exc_info=True)

    async def _notify_startup(self) -> None:
        if not self._control_chat_target():
            return
        await asyncio.sleep(1)
        hostname = socket.gethostname()
        text = (
            f"<b>🟢 Bot is back online</b>\n"
            f"Host: <code>{hostname}</code>\n"
            f"Version: <code>{self.version}</code>"
        )
        await self._send_control_message(text)

    async def _notify_shutdown(self) -> None:
        target = self._control_chat_target()
        if not target:
            return
        hostname = socket.gethostname()
        text = (
            f"<b>🔴 Bot going offline</b>\n"
            f"Host: <code>{hostname}</code>\n"
            "Shutdown in <i>about 1 second</i>."
        )
        await self._send_control_message(text, target=target)
        await asyncio.sleep(1)

    async def run(self):
        # Initialize database first
        await self.db_manager.initialize()

        await self._start_modules()
        self._startup_notice_task = asyncio.create_task(self._notify_startup())
        try:
            await self.dp.start_polling(
                self.bot,
                allowed_updates=["message", "callback_query"],
            )
        finally:
            if self._startup_notice_task:
                with contextlib.suppress(Exception):
                    await self._startup_notice_task
                self._startup_notice_task = None
            await self._notify_shutdown()
            await self._stop_modules()
            # Close database connection
            await self.db_manager.close()
