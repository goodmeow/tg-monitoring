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
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import psutil
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from tgbot.domain.config import Config
from tgbot.domain.evaluator import Thresholds, evaluate
import logging
from tgbot.clients.node_exporter import NodeExporterClient
from tgbot.stores.state_store import StateStore


def _human_gib(n: float) -> str:
    return f"{n/1024**3:.2f} GiB"


def _human_mib(n: float) -> str:
    return f"{n/1024**2:.0f} MiB"


def _bar(pct: float, width: int = 10) -> str:
    pct = max(0.0, min(1.0, pct))
    filled = int(round(pct * width))
    return "█" * filled + "░" * (width - filled)


def _decorate_with_bar(entry: Dict) -> str:
    if entry.get("type") == "cpu":
        p = float(entry.get("value") or 0)
        return f"CPU {p*100:.0f}% {_bar(p)}"
    if entry.get("type") == "mem":
        p = float(entry.get("value") or 0)
        return f"Mem used {p*100:.0f}% {_bar(p)}"
    if entry.get("type") == "disk":
        p = float(entry.get("value") or 0)
        mount = entry.get("mount") or "/"
        return f"{mount}: {p*100:.0f}% {_bar(p)}"
    if entry.get("type") == "inode":
        p = float(entry.get("value") or 0)
        mount = entry.get("mount") or "/"
        return f"{mount}: {p*100:.0f}% {_bar(p)}"
    return str(entry)


def _compose_changes_message_html(changes: List[Tuple[str, Dict]], hostname: str) -> str:
    by: Dict[str, List[Dict]] = {"ALERT": [], "RECOVERED": []}
    for change, entry in changes:
        by.setdefault(change, []).append(entry)

    lines: List[str] = []
    lines.append(f"<b>Server Monitor — {hostname}</b>")
    if by.get("ALERT"):
        lines.append("\n🔴 <b>ALERT</b>")
        for e in by["ALERT"]:
            lines.append(f"• {_decorate_with_bar(e)}")
    if by.get("RECOVERED"):
        lines.append("\n🟢 <b>RECOVERED</b>")
        for e in by["RECOVERED"]:
            lines.append(f"• {_decorate_with_bar(e)}")
    return "\n".join(lines)


def _compose_status_message_html(results: Dict[str, Dict], hostname: str, ts: float) -> str:
    ts_local = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
    ts_str = ts_local.strftime("%Y-%m-%d %H:%M:%S %Z")
    lines: List[str] = [f"<b>Server Status — {hostname}</b>", f"<i>{ts_str}</i>"]

    if "cpu" in results:
        r = results["cpu"]
        emoji = "🔴" if r["status"] == "alert" else "🟢"
        lines.append(f"\n<b>CPU</b> {emoji}\n{r['message']}")
    if "mem" in results:
        r = results["mem"]
        emoji = "🔴" if r["status"] == "alert" else "🟢"
        lines.append(f"\n<b>Memory</b> {emoji}\n{_decorate_with_bar(r)}")
        try:
            top = _top_mem_processes(3)
            if top:
                lines.append("Top RAM users:")
                for p in top:
                    lines.append(
                        f"• {p['name']} (pid {p['pid']}): {_human_mib(p['rss_bytes'])}"
                    )
        except Exception:
            pass
    if "disk" in results:
        r = results["disk"]
        emoji = "🔴" if r["status"] == "alert" else "🟢"
        lines.append(f"\n<b>Disk</b> {emoji}")
        by = (r.get("meta") or {}).get("by_mount") or []
        if by:
            for it in by:
                lines.append(
                    f"• {_decorate_with_bar({'type': 'disk', 'value': it.get('value', 0.0), 'mount': it.get('mount', '/')})}"
                )
        else:
            lines.append(r.get("message") or "OK")
    if "inode" in results:
        r = results["inode"]
        emoji = "🔴" if r["status"] == "alert" else "🟢"
        lines.append(f"\n<b>Inodes</b> {emoji}")
        by = (r.get("meta") or {}).get("by_mount") or []
        if by:
            for it in by:
                lines.append(
                    f"• {_decorate_with_bar({'type': 'inode', 'value': it.get('value', 0.0), 'mount': it.get('mount', '/')})}"
                )
        else:
            lines.append(r.get("message") or "OK")
    return "\n".join(lines)


def _top_mem_processes(n: int = 3):
    procs: List[Dict[str, Any]] = []
    for p in psutil.process_iter(attrs=["pid", "name", "memory_info"]):
        try:
            info = p.info
            meminfo = info.get("memory_info")
            if not meminfo:
                continue
            rss = getattr(meminfo, "rss", 0) or 0
            name = info.get("name") or f"pid{info.get('pid')}"
            procs.append({"pid": info.get("pid"), "name": name, "rss_bytes": int(rss)})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue
    procs.sort(key=lambda x: x["rss_bytes"], reverse=True)
    return procs[:n]


def _is_allowed(chat_id: int | str, cfg: Config) -> bool:
    if cfg.allow_any_chat:
        return True
    for allowed in cfg.allowed_chat_ids:
        if isinstance(allowed, int) and chat_id == allowed:
            return True
        if isinstance(allowed, str) and str(chat_id) == allowed:
            return True
    return False


@dataclass
class MonitoringService:
    cfg: Config
    state: StateStore
    client: NodeExporterClient
    log: logging.Logger = logging.getLogger("tgbot.monitoring")

    def build_router(self) -> Router:
        router = Router()

        @router.message(Command("status"))
        async def cmd_status(message: Message):
            if not _is_allowed(message.chat.id, self.cfg):
                return
            try:
                stats = await self.client.fetch_stats()
                thresholds = Thresholds(
                    cpu_load_per_core_warn=self.cfg.cpu_load_per_core_warn,
                    mem_available_pct_warn=self.cfg.mem_available_pct_warn,
                    disk_usage_pct_warn=self.cfg.disk_usage_pct_warn,
                    enable_inodes=self.cfg.enable_inodes,
                    inode_free_pct_warn=self.cfg.inode_free_pct_warn,
                    exclude_fs_types=self.cfg.exclude_fs_types,
                )
                results = evaluate(stats, thresholds)
                await message.answer(
                    _compose_status_message_html(
                        results, socket.gethostname(), stats.timestamp
                    ),
                    disable_web_page_preview=True,
                    parse_mode="HTML",
                )
            except Exception:
                self.log.exception("/status failed")
                await message.answer("Failed to collect status")

        return router

    async def run_loop(self, bot):
        cfg = self.cfg
        state = self.state
        thresholds = Thresholds(
            cpu_load_per_core_warn=cfg.cpu_load_per_core_warn,
            mem_available_pct_warn=cfg.mem_available_pct_warn,
            disk_usage_pct_warn=cfg.disk_usage_pct_warn,
            enable_inodes=cfg.enable_inodes,
            inode_free_pct_warn=cfg.inode_free_pct_warn,
            exclude_fs_types=cfg.exclude_fs_types,
        )
        host = socket.gethostname()
        while True:
            try:
                stats = await self.client.fetch_stats()
                results = evaluate(stats, thresholds)

                changes: List[Tuple[str, Dict]] = []
                for key, cur in results.items():
                    prev = await state.get_check(key)
                    prev_status = prev.get("status") if prev else "unknown"
                    consec = prev.get("consecutive", 0) if prev else 0

                    if cur["status"] == "alert":
                        consec = consec + 1 if prev_status == "alert" else 1
                        cur_state = {
                            "status": "alert",
                            "consecutive": consec,
                            "last_value": cur.get("value"),
                            "last_ts": time.time(),
                            "message": cur["message"],
                        }
                        if prev_status != "alert" and consec >= cfg.alert_min_consecutive:
                            changes.append(("ALERT", cur))
                        state.set_check(key, cur_state)
                    else:
                        if prev_status == "alert":
                            changes.append(("RECOVERED", cur))
                        cur_state = {
                            "status": "ok",
                            "consecutive": 1 if prev_status == "ok" else 0,
                            "last_value": cur.get("value"),
                            "last_ts": time.time(),
                            "message": cur["message"],
                        }
                        await state.set_check(key, cur_state)

                # Save state after processing all checks
                if hasattr(state, 'save'):
                    state.save()

                if changes:
                    target_chat = cfg.chat_id or cfg.control_chat_id
                    if not target_chat:
                        self.log.warning("No alert chat configured; skipping notification")
                    else:
                        await bot.send_message(
                            target_chat,
                            _compose_changes_message_html(changes, host),
                            disable_web_page_preview=True,
                            parse_mode="HTML",
                        )
            except Exception:
                self.log.warning("monitor loop iteration failed", exc_info=True)

            await asyncio.sleep(cfg.sample_interval_sec)
