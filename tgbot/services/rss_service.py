from __future__ import annotations

import asyncio
import html as _html
import time as _time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlparse

import feedparser
import logging
import socket
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from monitor.config import Config
from tgbot.clients.feed_client import FeedClient
from tgbot.stores.rss_store import RssStore


def _is_allowed(chat_id: int | str, allowed_list: List[int | str]) -> bool:
    for allowed in allowed_list:
        if isinstance(allowed, int) and chat_id == allowed:
            return True
        if isinstance(allowed, str) and str(chat_id) == allowed:
            return True
    return False


def _valid_url_http_https(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in {"http", "https"} and bool(p.netloc)
    except Exception:
        return False


def _compose_rss_digest_html(hostname: str, items_by_feed: Dict[str, List[Dict]], cfg: Config) -> str:
    total = 0
    lines: List[str] = []
    ts_local = datetime.now(tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines.append(f"<b>RSS Digest — {hostname}</b>\n<i>{ts_local}</i>")
    for url, items in items_by_feed.items():
        if not items:
            continue
        items = sorted(items, key=lambda x: x.get("published_ts", 0))
        cap = min(len(items), cfg.rss_digest_items_per_feed)
        lines.append(f"\n<b>{_html.escape(url)}</b>")
        for it in items[:cap]:
            title = _html.escape(it.get("title") or "(no title)")
            link = _html.escape(it.get("link") or "")
            author = _html.escape(it.get("author") or "")
            t = it.get("published_ts")
            tstr = (
                datetime.fromtimestamp(t, tz=timezone.utc)
                .astimezone()
                .strftime("%H:%M %Z")
                if t
                else ""
            )
            lines.append(f"• <a href=\"{link}\">{title}</a> — {author} ({tstr})")
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


@dataclass
class RssService:
    cfg: Config
    rss: RssStore
    client: FeedClient
    log: logging.Logger = logging.getLogger("tgbot.rss")

    def build_router(self) -> Router:
        router = Router()

        @router.message(Command("rss_add"))
        async def rss_add(message: Message):
            if not _is_allowed(message.chat.id, self.cfg.allowed_chat_ids):
                return
            parts = (message.text or "").split(maxsplit=1)
            if len(parts) < 2:
                await message.answer("Usage: /rss_add <url>")
                return
            url = parts[1].strip()
            if len(url) > 2000 or not _valid_url_http_https(url):
                await message.answer("Invalid URL (only http/https)")
                return
            self.rss.add_feed(message.chat.id, url)
            self.rss.save()
            await message.answer(f"Subscribed to feed:\n{_html.escape(url)}")

        @router.message(Command("rss_rm"))
        async def rss_rm(message: Message):
            if not _is_allowed(message.chat.id, self.cfg.allowed_chat_ids):
                return
            parts = (message.text or "").split(maxsplit=1)
            if len(parts) < 2:
                await message.answer("Usage: /rss_rm <url>")
                return
            url = parts[1].strip()
            self.rss.remove_feed(message.chat.id, url)
            self.rss.save()
            await message.answer(f"Unsubscribed:\n{_html.escape(url)}")

        @router.message(Command("rss_ls"))
        async def rss_ls(message: Message):
            if not _is_allowed(message.chat.id, self.cfg.allowed_chat_ids):
                return
            feeds = self.rss.list_feeds(message.chat.id)
            counts = self.rss.get_pending_counts(message.chat.id)
            last = self.rss.get_last_digest(message.chat.id)
            next_ts = last + self.cfg.rss_digest_interval_sec
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

    async def poll_loop(self):
        cfg = self.cfg
        rss = self.rss
        while True:
            try:
                feeds = rss.all_feeds()
                for url in feeds:
                    meta = rss.get_feed_meta(url)
                    try:
                        parsed = self.client.parse(
                            url,
                            etag=meta.get("etag"),
                            last_modified=meta.get("last_modified"),
                        )
                    except Exception:
                        self.log.warning("feed parse failed: %s", url, exc_info=True)
                        continue
                    try:
                        etag = getattr(parsed, "etag", None)
                    except Exception:
                        etag = None
                    try:
                        modified = getattr(parsed, "modified", None)
                    except Exception:
                        modified = None
                    if etag or modified:
                        rss.update_feed_meta(url, etag, modified)

                    entries = list(getattr(parsed, "entries", []) or [])
                    for e in entries:
                        iid = (
                            getattr(e, "id", None)
                            or getattr(e, "link", None)
                            or str(getattr(e, "published_parsed", None))
                        )
                        if not iid:
                            continue
                        # seen dedupe
                        seen = rss.get_feed_meta(url).get("seen_ids", [])
                        if iid in seen:
                            continue
                        title = getattr(e, "title", None) or "(no title)"
                        link = getattr(e, "link", None) or ""
                        author = getattr(e, "author", None) or ""
                        ts = 0
                        try:
                            ts = int(_time.mktime(getattr(e, "published_parsed", None)))
                        except Exception:
                            ts = int(_time.time())
                        item = {
                            "id": iid,
                            "title": title,
                            "link": link,
                            "author": author,
                            "published_ts": ts,
                        }
                        for cid in rss.subscribers(url):
                            rss.add_pending_item(cid, url, item)
                        rss.add_seen_id(url, iid)
                rss.save()
            except Exception:
                self.log.warning("rss poll iteration failed", exc_info=True)
            await asyncio.sleep(cfg.rss_poll_interval_sec)

    async def digest_loop(self, bot):
        cfg = self.cfg
        rss = self.rss
        host = socket.gethostname()
        while True:
            try:
                chats = list((rss.data.get("chats") or {}).keys())
                now = _time.time()
                for cid in chats:
                    last = rss.get_last_digest(cid)
                    if now - last < cfg.rss_digest_interval_sec:
                        continue
                    pending = rss.pop_pending_digest(cid)
                    if not any(pending.values()):
                        rss.set_last_digest(cid, now)
                        rss.save()
                        continue
                    msg = _compose_rss_digest_html(host, pending, cfg)
                    await bot.send_message(
                        cid, msg, parse_mode="HTML", disable_web_page_preview=True
                    )
                    rss.set_last_digest(cid, now)
                    rss.save()
            except Exception:
                self.log.warning("rss digest iteration failed", exc_info=True)
            await asyncio.sleep(300)
