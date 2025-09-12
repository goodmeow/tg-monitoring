from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Tuple

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
import contextlib
import socket
from datetime import datetime, timezone
import psutil
import time as _time
import html as _html
import feedparser

from .config import load_config
from .evaluator import Thresholds, evaluate
from .metrics import fetch_node_stats
from .state import StateStore
from .rss_store import RssStore


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


def _human_gib(n: float) -> str:
    return f"{n/1024**3:.2f} GiB"


def _human_mib(n: float) -> str:
    return f"{n/1024**2:.0f} MiB"


def _compose_status_message_html(results: Dict[str, Dict], hostname: str, ts: float) -> str:
    # Convert to local timezone and include TZ name
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
        # Top 3 processes by RSS
        try:
            top = _top_mem_processes(3)
            if top:
                lines.append("Top RAM users:")
                for p in top:
                    lines.append(f"• {p['name']} (pid {p['pid']}): {_human_mib(p['rss_bytes'])}")
        except Exception:
            pass

    disks = [(k, v) for k, v in results.items() if k.startswith("disk:")]
    disks.sort(key=lambda kv: kv[1].get("value", 0.0), reverse=True)
    if disks:
        lines.append("\n<b>Disks</b>")
        for _, r in disks[:8]:
            lines.append(f"• {_decorate_with_bar(r)}")

    inodes = [(k, v) for k, v in results.items() if k.startswith("inode:")]
    inodes.sort(key=lambda kv: kv[1].get("value", 0.0))
    if inodes:
        lines.append("\n<b>Inodes</b>")
        for _, r in inodes[:8]:
            lines.append(f"• {r['message']}")

    return "\n".join(lines) or "No metrics available"


def _bar(pct: float, width: int = 10) -> str:
    try:
        p = max(0.0, min(1.0, float(pct)))
    except Exception:
        p = 0.0
    used = int(round(p * width))
    used = max(0, min(width, used))
    return ("▓" * used) + ("░" * (width - used))


def _decorate_with_bar(entry: Dict) -> str:
    """Prefix message with a usage bar for disk and memory entries.
    - Disk: entry.value is used fraction (0..1)
    - Memory: entry.value is available fraction (invert to used)
    Other entries return message unchanged.
    """
    try:
        meta = entry.get("meta") or {}
        val = float(entry.get("value", 0.0))
        if "size_bytes" in meta and "avail_bytes" in meta:
            # Disk: value is used fraction
            return f"[{_bar(val)}] {entry['message']}"
        if "available_bytes" in meta and "total_bytes" in meta:
            # Memory: value is available fraction -> invert to used
            used = 1.0 - val
            return f"[{_bar(used)}] {entry['message']}"
    except Exception:
        pass
    return entry.get("message", "")


def _top_mem_processes(n: int = 3):
    procs = []
    for p in psutil.process_iter(attrs=["pid", "name", "memory_info"]):
        try:
            info = p.info
            rss = getattr(info.get("memory_info"), "rss", None)
            if rss is None:
                continue
            name = info.get("name") or f"pid{info.get('pid')}"
            procs.append({"pid": info.get("pid"), "name": name, "rss_bytes": int(rss)})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue
    procs.sort(key=lambda x: x["rss_bytes"], reverse=True)
    return procs[:n]


async def monitor_task(cfg, state: StateStore, bot: Bot):
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
                await bot.send_message(
                    cfg.chat_id,
                    _compose_changes_message_html(changes, host),
                    disable_web_page_preview=True,
                    parse_mode="HTML",
                )
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
            await message.answer(
                _compose_status_message_html(results, socket.gethostname(), stats.timestamp),
                disable_web_page_preview=True,
                parse_mode="HTML",
            )
        except Exception:
            await message.answer("Failed to collect status")

    return router


# ===== RSS features =====

def build_rss_router(cfg, rss: RssStore) -> Router:
    router = Router()

    @router.message(Command("rss_add"))
    async def rss_add(message: Message):
        if not _is_allowed(message.chat.id, cfg.allowed_chat_ids):
            return
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Usage: /rss_add <url>")
            return
        url = parts[1].strip()
        rss.add_feed(message.chat.id, url)
        rss.save()
        await message.answer(f"Subscribed to feed:\n{_html.escape(url)}")

    @router.message(Command("rss_rm"))
    async def rss_rm(message: Message):
        if not _is_allowed(message.chat.id, cfg.allowed_chat_ids):
            return
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Usage: /rss_rm <url>")
            return
        url = parts[1].strip()
        rss.remove_feed(message.chat.id, url)
        rss.save()
        await message.answer(f"Unsubscribed:\n{_html.escape(url)}")

    @router.message(Command("rss_ls"))
    async def rss_ls(message: Message):
        if not _is_allowed(message.chat.id, cfg.allowed_chat_ids):
            return
        feeds = rss.list_feeds(message.chat.id)
        counts = rss.get_pending_counts(message.chat.id)
        last = rss.get_last_digest(message.chat.id)
        next_ts = last + cfg.rss_digest_interval_sec
        now = _time.time()
        rem = max(0, int(next_ts - now))
        mins = rem // 60
        lines = ["<b>RSS Subscriptions</b>"]
        if feeds:
            for u in feeds:
                c = counts.get(u, 0)
                lines.append(f"• {_html.escape(u)} (pending: {c})")
        else:
            lines.append("(none)")
        lines.append(f"\nNext digest in ~{mins} min")
        await message.answer("\n".join(lines), parse_mode="HTML")

    return router


async def rss_poll_task(cfg, rss: RssStore):
    while True:
        try:
            feeds = rss.all_feeds()
            for url in feeds:
                meta = rss.get_feed_meta(url)
                try:
                    parsed = feedparser.parse(url, etag=meta.get("etag"), modified=meta.get("last_modified"))
                except Exception:
                    continue
                status = getattr(parsed, "status", 200)
                if status == 304:
                    continue
                rss.update_feed_meta(url, getattr(parsed, "etag", None), getattr(parsed, "modified", None))

                entries = getattr(parsed, "entries", []) or []
                seen = set(meta.get("seen_ids") or [])
                new_items = []
                for e in entries:
                    iid = e.get("id") or e.get("link") or (e.get("title") or "") + str(e.get("published"))
                    if not iid or iid in seen:
                        continue
                    # published timestamp
                    ts = None
                    if e.get("published_parsed"):
                        try:
                            ts = _time.mktime(e.published_parsed)
                        except Exception:
                            ts = None
                    item = {
                        "id": iid,
                        "title": e.get("title") or "(no title)",
                        "link": e.get("link") or "",
                        "author": e.get("author") or "",
                        "published_ts": ts or _time.time(),
                        "feed_title": getattr(parsed.feed, "title", ""),
                    }
                    new_items.append(item)
                    rss.add_seen_id(url, iid)

                if not new_items:
                    continue

                subs = rss.subscribers(url)
                for cid in subs:
                    for it in new_items:
                        rss.add_pending_item(cid, url, it)
                rss.save()
        except Exception:
            pass
        await asyncio.sleep(cfg.rss_poll_interval_sec)


def _compose_rss_digest_html(hostname: str, items_by_feed: Dict[str, List[Dict]], cfg) -> str:
    # Flatten count and cap per feed and total
    total = 0
    lines: List[str] = []
    ts_local = datetime.now(tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines.append(f"<b>RSS Digest — {hostname}</b>\n<i>{ts_local}</i>")
    for url, items in items_by_feed.items():
        if not items:
            continue
        # sort by published_ts ascending
        items = sorted(items, key=lambda x: x.get("published_ts", 0))
        cap = min(len(items), cfg.rss_digest_items_per_feed)
        shown = 0
        lines.append(f"\n<b>{_html.escape(url)}</b>")
        for it in items[:cap]:
            title = _html.escape(it.get("title") or "(no title)")
            link = _html.escape(it.get("link") or "")
            author = _html.escape(it.get("author") or "")
            t = it.get("published_ts")
            tstr = datetime.fromtimestamp(t, tz=timezone.utc).astimezone().strftime("%H:%M %Z") if t else ""
            lines.append(f"• <a href=\"{link}\">{title}</a> — {author} ({tstr})")
            shown += 1
            total += 1
            if total >= cfg.rss_digest_max_total:
                break
        more = max(0, len(items) - cap)
        if more:
            lines.append(f"(+{more} more)")
        if total >= cfg.rss_digest_max_total:
            break
    if total == 0:
        return "(no new items)"
    return "\n".join(lines)


async def rss_digest_task(cfg, rss: RssStore, bot: Bot):
    host = socket.gethostname()
    while True:
        try:
            # iterate over chats
            chats = list((rss.data.get("chats") or {}).keys())
            now = _time.time()
            for cid in chats:
                last = rss.get_last_digest(cid)
                if now - last < cfg.rss_digest_interval_sec:
                    continue
                pending = rss.pop_pending_digest(cid)
                if not any(pending.values()):
                    # nothing to send; update last_digest to avoid spinning
                    rss.set_last_digest(cid, now)
                    rss.save()
                    continue
                msg = _compose_rss_digest_html(host, pending, cfg)
                await bot.send_message(cid, msg, parse_mode="HTML", disable_web_page_preview=True)
                rss.set_last_digest(cid, now)
                rss.save()
        except Exception:
            pass
        await asyncio.sleep(300)  # check every 5 minutes


async def amain():
    cfg = load_config()
    state = StateStore(cfg.state_file)
    rss = RssStore(cfg.rss_store_file)
    bot = Bot(cfg.bot_token)
    dp = Dispatcher()
    dp.include_router(build_router(cfg, state))
    dp.include_router(build_rss_router(cfg, rss))

    task = asyncio.create_task(monitor_task(cfg, state, bot))
    rss_poll = asyncio.create_task(rss_poll_task(cfg, rss))
    rss_digest = asyncio.create_task(rss_digest_task(cfg, rss, bot))
    try:
        await dp.start_polling(bot, allowed_updates=["message"])
    finally:
        task.cancel()
        rss_poll.cancel()
        rss_digest.cancel()
        with contextlib.suppress(Exception):
            await task
        with contextlib.suppress(Exception):
            await rss_poll
        with contextlib.suppress(Exception):
            await rss_digest


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
