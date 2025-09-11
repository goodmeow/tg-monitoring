from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Tuple

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from .config import load_config
from .evaluator import Thresholds, evaluate
from .metrics import fetch_node_stats
from .state import StateStore


def _compose_changes_message(changes: List[Tuple[str, Dict]]) -> str:
    lines = []
    for change, entry in changes:
        emoji = "🔴" if change == "ALERT" else "🟢"
        lines.append(f"{emoji} {change} — {entry['message']}")
    return "\n".join(lines)


def _compose_status_message(results: Dict[str, Dict]) -> str:
    lines: List[str] = []
    if "cpu" in results:
        r = results["cpu"]
        emoji = "🔴" if r["status"] == "alert" else "🟢"
        lines.append(f"{emoji} {r['message']}")
    if "mem" in results:
        r = results["mem"]
        emoji = "🔴" if r["status"] == "alert" else "🟢"
        lines.append(f"{emoji} {r['message']}")
    disks = [(k, v) for k, v in results.items() if k.startswith("disk:")]
    disks.sort(key=lambda kv: kv[1].get("value", 0.0), reverse=True)
    for _, r in disks[:8]:
        emoji = "🔴" if r["status"] == "alert" else "🟢"
        lines.append(f"{emoji} {r['message']}")
    inodes = [(k, v) for k, v in results.items() if k.startswith("inode:")]
    inodes.sort(key=lambda kv: kv[1].get("value", 0.0))
    for _, r in inodes[:8]:
        emoji = "🔴" if r["status"] == "alert" else "🟢"
        lines.append(f"{emoji} {r['message']}")
    return "\n".join(lines) or "No metrics available"


async def monitor_task(cfg, state: StateStore, bot: Bot):
    thresholds = Thresholds(
        cpu_load_per_core_warn=cfg.cpu_load_per_core_warn,
        mem_available_pct_warn=cfg.mem_available_pct_warn,
        disk_usage_pct_warn=cfg.disk_usage_pct_warn,
        enable_inodes=cfg.enable_inodes,
        inode_free_pct_warn=cfg.inode_free_pct_warn,
        exclude_fs_types=cfg.exclude_fs_types,
    )
    while True:
        try:
            stats = await fetch_node_stats(cfg.node_exporter_url, timeout_sec=cfg.http_timeout_sec)
            results = evaluate(stats, thresholds)

            changes: List[Tuple[str, Dict]] = []
            for key, cur in results.items():
                prev = state.get_check(key)
                prev_status = prev.get("status") if prev else "unknown"
                consec = prev.get("consecutive", 0)

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
                    state.set_check(key, cur_state)

            state.save()

            if changes:
                await bot.send_message(cfg.chat_id, _compose_changes_message(changes), disable_web_page_preview=True)
        except Exception:
            # optional: send a one-time unreachable warning with debounce
            pass

        await asyncio.sleep(cfg.sample_interval_sec)


def _is_allowed(chat_id: int | str, allowed_list: List[int | str]) -> bool:
    for allowed in allowed_list:
        if isinstance(allowed, int) and chat_id == allowed:
            return True
        if isinstance(allowed, str) and str(chat_id) == allowed:
            return True
    return False


def build_router(cfg, state: StateStore) -> Router:
    router = Router()

    @router.message(Command("status"))
    async def cmd_status(message: Message):
        if not _is_allowed(message.chat.id, cfg.allowed_chat_ids):
            return
        try:
            stats = await fetch_node_stats(cfg.node_exporter_url, timeout_sec=cfg.http_timeout_sec)
            thresholds = Thresholds(
                cpu_load_per_core_warn=cfg.cpu_load_per_core_warn,
                mem_available_pct_warn=cfg.mem_available_pct_warn,
                disk_usage_pct_warn=cfg.disk_usage_pct_warn,
                enable_inodes=cfg.enable_inodes,
                inode_free_pct_warn=cfg.inode_free_pct_warn,
                exclude_fs_types=cfg.exclude_fs_types,
            )
            results = evaluate(stats, thresholds)
            await message.answer(_compose_status_message(results), disable_web_page_preview=True)
        except Exception:
            await message.answer("Failed to collect status")

    return router


async def amain():
    cfg = load_config()
    state = StateStore(cfg.state_file)
    bot = Bot(cfg.bot_token)
    dp = Dispatcher()
    dp.include_router(build_router(cfg, state))

    task = asyncio.create_task(monitor_task(cfg, state, bot))
    try:
        await dp.start_polling(bot, allowed_updates=["message"])
    finally:
        task.cancel()
        with contextlib.suppress(Exception):
            await task


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
