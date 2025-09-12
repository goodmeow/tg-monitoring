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
            ],
        ]
    )


@dataclass
class HelpService:
    cfg: Config
    node: NodeExporterClient
    rss: RssStore
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
                "",
                "Tombol cepat tersedia di bawah.",
            ]
            await message.answer(
                "\n".join(lines), parse_mode="HTML", reply_markup=_help_keyboard()
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

        return router

