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

import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from tgbot.domain.config import Config
from tgbot.domain.evaluator import Thresholds, evaluate
from tgbot.clients.node_exporter import NodeExporterClient
from tgbot.stores.rss_store import RssStore
from tgbot.services.monitoring_service import _compose_status_message_html


def _is_allowed(chat_id: int | str, allowed_list: List[int | str]) -> bool:
    for allowed in allowed_list:
        if isinstance(allowed, int) and chat_id == allowed:
            return True
        if isinstance(allowed, str) and str(chat_id) == allowed:
            return True
    return False


def _help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Status", callback_data="help:status"),
                InlineKeyboardButton(text="RSS List", callback_data="help:rss_ls"),
                InlineKeyboardButton(text="QR Code", callback_data="help:qrcode"),
            ],
            [
                InlineKeyboardButton(text="Versi", callback_data="help:version"),
            ],
        ]
    )


@dataclass
class HelpService:
    cfg: Config
    node: NodeExporterClient
    rss: RssStore
    version: str
    log: logging.Logger = logging.getLogger("tgbot.help")

    def build_router(self) -> Router:
        router = Router()

        @router.message(Command("help"))
        async def cmd_help(message: Message):
            if not _is_allowed(message.chat.id, self.cfg.allowed_chat_ids):
                return
            lines = [
                "<b>Bot Menu</b>",
                "",
                "Perintah:",
                "• /status — ringkasan status server",
                "• /rss_add &lt;url&gt; — tambah langganan RSS",
                "• /rss_rm &lt;url&gt; — hapus langganan RSS",
                "• /rss_ls — daftar langganan RSS",
                "• /qrcode &lt;text&gt; — buat QR code (atau reply ke pesan)",
                "• /version — info versi tg-monitoring",
                "",
                "Tombol cepat tersedia di bawah.",
            ]
            await message.answer(
                "\n".join(lines), parse_mode="HTML", reply_markup=_help_keyboard()
            )

        @router.message(Command("version"))
        async def cmd_version(message: Message):
            if not _is_allowed(message.chat.id, self.cfg.allowed_chat_ids):
                return
            await message.answer(
                f"tg-monitoring version: <code>{self.version}</code>",
                parse_mode="HTML",
            )

        @router.callback_query(F.data == "help:status")
        async def cb_status(query: CallbackQuery):
            chat_id = query.message.chat.id if query.message else query.from_user.id
            if not _is_allowed(chat_id, self.cfg.allowed_chat_ids):
                await query.answer()
                return
            try:
                stats = await self.node.fetch_stats()
                thresholds = Thresholds(
                    cpu_load_per_core_warn=self.cfg.cpu_load_per_core_warn,
                    mem_available_pct_warn=self.cfg.mem_available_pct_warn,
                    disk_usage_pct_warn=self.cfg.disk_usage_pct_warn,
                    enable_inodes=self.cfg.enable_inodes,
                    inode_free_pct_warn=self.cfg.inode_free_pct_warn,
                    exclude_fs_types=self.cfg.exclude_fs_types,
                )
                results = evaluate(stats, thresholds)
                text = _compose_status_message_html(
                    results, socket.gethostname(), stats.timestamp
                )
                if query.message:
                    await query.message.answer(
                        text, disable_web_page_preview=True, parse_mode="HTML"
                    )
                await query.answer()
            except Exception:
                self.log.exception("help:status failed")
                if query.message:
                    await query.message.answer("Failed to collect status")
                await query.answer()

        @router.callback_query(F.data == "help:rss_ls")
        async def cb_rss_ls(query: CallbackQuery):
            chat_id = query.message.chat.id if query.message else query.from_user.id
            if not _is_allowed(chat_id, self.cfg.allowed_chat_ids):
                await query.answer()
                return
            try:
                feeds = self.rss.list_feeds(chat_id)
                counts = self.rss.get_pending_counts(chat_id)
                last = self.rss.get_last_digest(chat_id)
                next_ts = last + self.cfg.rss_digest_interval_sec
                now = time.time()
                rem = max(0, int(next_ts - now))
                mins = rem // 60
                lines = ["<b>RSS Subscriptions</b>"]
                if feeds:
                    for u in feeds:
                        c = counts.get(u, 0)
                        lines.append(f"• {u} (pending: {c})")
                else:
                    lines.append("(none)")
                lines.append(f"\nNext digest in ~{mins} min")
                if query.message:
                    await query.message.answer("\n".join(lines), parse_mode="HTML")
                await query.answer()
            except Exception:
                self.log.exception("help:rss_ls failed")
                if query.message:
                    await query.message.answer("Failed to read RSS list")
                await query.answer()

        @router.callback_query(F.data == "help:qrcode")
        async def cb_qrcode(query: CallbackQuery):
            chat_id = query.message.chat.id if query.message else query.from_user.id
            if not _is_allowed(chat_id, self.cfg.allowed_chat_ids):
                await query.answer()
                return
            lines = [
                "<b>QR Code</b>",
                "",
                "Gunakan /qrcode &lt;text&gt; untuk membuat QR code baru.",
                "Atau reply ke pesan teks/caption lalu kirim /qrcode tanpa argumen.",
            ]
            if query.message:
                await query.message.answer("\n".join(lines), parse_mode="HTML")
            await query.answer()

        @router.callback_query(F.data == "help:version")
        async def cb_version(query: CallbackQuery):
            chat_id = query.message.chat.id if query.message else query.from_user.id
            if not _is_allowed(chat_id, self.cfg.allowed_chat_ids):
                await query.answer()
                return
            text = f"<b>Versi</b>\n\ntg-monitoring: <code>{self.version}</code>"
            if query.message:
                await query.message.answer(text, parse_mode="HTML")
            await query.answer()

        return router
