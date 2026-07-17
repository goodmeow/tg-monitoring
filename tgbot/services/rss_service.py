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
import html as _html
import re
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

from tgbot.domain.config import Config
from tgbot.clients.feed_client import FeedClient
from tgbot.stores.rss_store_v2 import HybridRssStore


def _is_allowed(chat_id: int | str, cfg: Config) -> bool:
    if cfg.allow_any_chat:
        return True
    for allowed in cfg.allowed_chat_ids:
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

TELEGRAM_HTML_HARD_LIMIT = 4096
TELEGRAM_HTML_CHUNK_LIMIT = 3600


def _compose_rss_digest_html(hostname: str, items_by_feed: Dict[str, List[Dict]], cfg: Config) -> str:
    total = 0
    lines: List[str] = []
    ts_local = datetime.now(tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines.append(f"<b>📰 RSS Digest — {hostname}</b>")
    lines.append(f"<i>{ts_local}</i>")

    def _format_meta(author: str, ts_value: int | None) -> str:
        parts: List[str] = []
        if author:
            parts.append(author)
        if ts_value:
            try:
                parts.append(
                    datetime.fromtimestamp(ts_value, tz=timezone.utc)
                    .astimezone()
                    .strftime("%H:%M %Z")
                )
            except Exception:
                pass
        return " — ".join(parts)

    def _trim_snippet(raw: str) -> str:
        text = _html.unescape(raw)
        text = re.sub(r"<[^>]+>", " ", text)
        text = " ".join(text.split())
        if len(text) > 160:
            text = text[:157].rstrip() + "…"
        return text

    for url, items in items_by_feed.items():
        if not items:
            continue
        items = sorted(items, key=lambda x: x.get("published_ts", 0))
        cap = min(len(items), cfg.rss_digest_items_per_feed)

        escaped_url = _html.escape(url)
        lines.append("")
        lines.append(f"<b>🌐 {escaped_url}</b> <i>({len(items)} new)</i>")

        for it in items[:cap]:
            title = _html.escape(it.get("title") or "(no title)")
            link = _html.escape(it.get("link") or "")
            author = _html.escape(it.get("author") or "")
            ts_value = it.get("published_ts")
            meta = _format_meta(author, ts_value)

            header = f"• <a href=\"{link}\">{title}</a>"
            if meta:
                header += f" <i>({meta})</i>"
            lines.append(header)

            raw_desc = it.get("description") or ""
            if raw_desc:
                snippet = _trim_snippet(raw_desc)
                if snippet:
                    lines.append(f"   ⤷ {snippet}")

            total += 1
            if total >= cfg.rss_digest_max_total:
                break

        more = max(0, len(items) - cap)
        if more:
            lines.append(f"   ⤷ (+{more} more)")

        if total >= cfg.rss_digest_max_total:
            break

    if total == 0:
        return "(no new items)"
    return "\n".join(lines)


def _split_html_message(payload: str, *, limit: int = TELEGRAM_HTML_CHUNK_LIMIT) -> List[str]:
    max_limit = TELEGRAM_HTML_HARD_LIMIT - 512  # reserve space for final annotations/markup
    limit = max(1, min(limit, max_limit))
    if len(payload) <= limit:
        return [payload]

    chunks: List[str] = []
    current_lines: List[str] = []
    current_len = 0

    for line in payload.split("\n"):
        additional_len = len(line)
        if current_lines:
            additional_len += 1  # newline separator
        if current_len + additional_len > limit and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = [line]
            current_len = len(line)
        elif len(line) > limit:
            if current_lines:
                chunks.append("\n".join(current_lines))
                current_lines = []
                current_len = 0
            for start in range(0, len(line), limit):
                chunks.append(line[start:start + limit])
            current_lines = []
            current_len = 0
        else:
            current_lines.append(line)
            current_len += additional_len

    if current_lines:
        chunks.append("\n".join(current_lines))

    result: List[str] = []
    for chunk in chunks:
        if not chunk:
            continue
        if len(chunk) > TELEGRAM_HTML_HARD_LIMIT:
            for start in range(0, len(chunk), TELEGRAM_HTML_HARD_LIMIT - 1):
                piece = chunk[start:start + TELEGRAM_HTML_HARD_LIMIT - 1]
                if len(piece) == TELEGRAM_HTML_HARD_LIMIT - 1 and start + TELEGRAM_HTML_HARD_LIMIT - 1 < len(chunk):
                    piece = piece[:-1] + "…"
                result.append(piece)
            continue
        result.append(chunk)
    return result


@dataclass
class RssService:
    cfg: Config
    rss: HybridRssStore
    client: FeedClient
    log: logging.Logger = logging.getLogger("tgbot.rss")

    def build_router(self) -> Router:
        router = Router()

        @router.message(Command("rss_add"))
        async def rss_add(message: Message):
            if not _is_allowed(message.chat.id, self.cfg):
                return
            parts = (message.text or "").split(maxsplit=1)
            if len(parts) < 2:
                await message.answer("Usage: /rss_add <url>")
                return
            url = parts[1].strip()
            if len(url) > 2000 or not _valid_url_http_https(url):
                await message.answer("Invalid URL (only http/https)")
                return

            try:
                # Check if feed already exists for this chat
                existing_feeds = await self.rss.get_feeds(message.chat.id)
                if url in existing_feeds:
                    await message.answer(f"Feed already subscribed:\n{_html.escape(url)}")
                    return

                # Add the feed
                await self.rss.add_feed(message.chat.id, url)
                # Note: PostgreSQL operations auto-commit, JSON fallback handled in store

                # Get updated feed count
                updated_feeds = await self.rss.get_feeds(message.chat.id)
                await message.answer(
                    f"✅ Subscribed to feed:\n{_html.escape(url)}\n\n"
                    f"Total feeds: {len(updated_feeds)}"
                )
            except Exception as e:
                self.log.error(f"Failed to add RSS feed {url}: {e}")
                await message.answer(f"❌ Failed to add feed. Please try again.")

        @router.message(Command("rss_rm"))
        async def rss_rm(message: Message):
            if not _is_allowed(message.chat.id, self.cfg):
                return
            parts = (message.text or "").split(maxsplit=1)
            if len(parts) < 2:
                await message.answer("Usage: /rss_rm <url>")
                return
            url = parts[1].strip()

            try:
                # Check if feed exists for this chat
                existing_feeds = await self.rss.get_feeds(message.chat.id)
                if url not in existing_feeds:
                    await message.answer(f"Feed not found:\n{_html.escape(url)}")
                    return

                # Remove the feed
                success = await self.rss.remove_feed(message.chat.id, url)
                # Note: PostgreSQL operations auto-commit, JSON fallback handled in store

                if success:
                    # Get updated feed count
                    updated_feeds = await self.rss.get_feeds(message.chat.id)
                    await message.answer(
                        f"✅ Unsubscribed from:\n{_html.escape(url)}\n\n"
                        f"Remaining feeds: {len(updated_feeds)}"
                    )
                else:
                    await message.answer(f"❌ Failed to remove feed:\n{_html.escape(url)}")
            except Exception as e:
                self.log.error(f"Failed to remove RSS feed {url}: {e}")
                await message.answer(f"❌ Failed to remove feed. Please try again.")

        @router.message(Command("rss_ls"))
        async def rss_ls(message: Message):
            if not _is_allowed(message.chat.id, self.cfg):
                return
            feeds = await self.rss.get_feeds(message.chat.id)
            counts = await self.rss.get_pending_counts(message.chat.id)
            last = await self.rss.get_last_digest(message.chat.id)
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
                feeds = await rss.all_feeds()
                for url in feeds:
                    meta = await rss.get_feed_meta(url)
                    attempt = 0
                    backoff_sec = 1
                    parsed = None
                    while attempt <= 3 and parsed is None:
                        try:
                            parsed = self.client.parse(
                                url,
                                etag=meta.get("etag"),
                                last_modified=meta.get("last_modified"),
                            )
                        except Exception as exc:
                            attempt += 1
                            if attempt > 3:
                                self.log.warning(
                                    "feed parse failed after retries",
                                    extra={"url": url, "attempts": attempt},
                                    exc_info=True,
                                )
                                break
                            self.log.warning(
                                "feed parse error, retrying",
                                extra={"url": url, "attempt": attempt},
                                exc_info=True,
                            )
                            await asyncio.sleep(backoff_sec)
                            backoff_sec = min(backoff_sec * 2, 60)
                            continue
                    if parsed is None:
                        continue
                    try:
                        etag = getattr(parsed, "etag", None)
                    except Exception:
                        etag = None
                    try:
                        modified = getattr(parsed, "modified", None)
                    except Exception:
                        modified = None
                    await rss.update_feed_meta(url, etag, modified)

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
                        meta = await rss.get_feed_meta(url)
                        seen = meta.get("seen_ids", [])
                        if iid in seen:
                            continue
                        title = getattr(e, "title", None) or "(no title)"
                        link = getattr(e, "link", None) or ""
                        author = getattr(e, "author", None) or ""
                        description = getattr(e, "summary", None) or getattr(e, "description", None) or ""
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
                            "description": description,
                            "published_ts": ts,
                        }
                        subscribers = await rss.subscribers(url)
                        for cid in subscribers:
                            await rss.add_pending_item(cid, url, item)
                        await rss.add_seen_id(url, iid)
                await rss.save()
            except Exception:
                self.log.warning("rss poll iteration failed", exc_info=True)
            await asyncio.sleep(cfg.rss_poll_interval_sec)

    async def digest_loop(self, bot):
        cfg = self.cfg
        rss = self.rss
        host = self.cfg.host_display_name or socket.gethostname()
        while True:
            try:
                # Find all chats that have RSS feeds
                chats = await rss.get_chat_ids()
                now = _time.time()
                for cid in chats:
                    last = await rss.get_last_digest(cid)
                    if now - last < cfg.rss_digest_interval_sec:
                        continue
                    pending = await rss.pop_pending_digest(cid)
                    if not any(pending.values()):
                        await rss.set_last_digest(cid, now)
                        await rss.save()
                        continue
                    msg = _compose_rss_digest_html(host, pending, cfg)
                    parts = _split_html_message(msg)
                    payloads: List[tuple[int, str]] = []
                    for idx, part in enumerate(parts, start=1):
                        part_label = f" (Part {idx}/{len(parts)})" if len(parts) > 1 else ""
                        payload = part + part_label
                        chunk_len = len(payload)
                        if chunk_len > TELEGRAM_HTML_HARD_LIMIT:
                            payload = payload[: TELEGRAM_HTML_HARD_LIMIT - 1] + "…"
                        payloads.append((idx, payload))

                    for idx, payload in payloads:
                        chunk_len = len(payload)
                        self.log.debug(
                            "Sending RSS digest chunk",
                            extra={
                                "chat_id": cid,
                                "chunk_index": idx,
                                "chunk_total": len(payloads),
                                "chunk_length": chunk_len,
                                "chunk_preview": payload[:120],
                            },
                        )
                        if chunk_len >= TELEGRAM_HTML_HARD_LIMIT:
                            self.log.warning(
                                "Digest chunk trimmed to telegram ceiling",
                                extra={
                                    "chat_id": cid,
                                    "chunk_index": idx,
                                    "chunk_total": len(payloads),
                                    "chunk_length": chunk_len,
                                    "chunk_preview": payload[:120],
                                },
                            )
                        await bot.send_message(
                            cid,
                            payload,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                        )
                    await rss.set_last_digest(cid, now)
                    await rss.save()
            except Exception:
                self.log.warning("rss digest iteration failed", exc_info=True)
            await asyncio.sleep(cfg.rss_digest_interval_sec)
