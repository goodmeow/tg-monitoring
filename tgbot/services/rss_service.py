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
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from tgbot.domain.config import Config
from tgbot.domain.hostname import fetch_host_display_name, resolve_host_display_name
from tgbot.clients.feed_client import FeedClient, ensure_public_url
from tgbot.clients.node_exporter import NodeExporterClient
from tgbot.stores.rss_store_v2 import HybridRssStore


def _valid_url_http_https(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in {"http", "https"} and bool(p.netloc)
    except Exception:
        return False


def _next_digest_text(last: float, now: float, interval_sec: float) -> str:
    """Human-readable countdown; a chat without a digest yet is due now."""
    elapsed = now - last
    if last <= 0 or elapsed < 0 or elapsed >= interval_sec:
        return "Next digest: due now"
    rem = int(interval_sec - elapsed)
    if rem < 60:
        return "Next digest in <1 min"
    return f"Next digest in ~{rem // 60} min"


TELEGRAM_HTML_HARD_LIMIT = 4096
TELEGRAM_HTML_CHUNK_LIMIT = 3600


def _compose_rss_digest_html(
    hostname: str, items_by_feed: Dict[str, List[Dict]], cfg: Config
) -> tuple[str, Dict[str, List[str]]]:
    total = 0
    lines: List[str] = []
    delivered: Dict[str, List[str]] = {}
    ts_local = datetime.now(tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    feed_count = sum(1 for items in items_by_feed.values() if items)
    item_count = sum(len(items) for items in items_by_feed.values())
    lines.append(f"<b>📰 RSS Digest — {_html.escape(hostname)}</b>")
    lines.append(
        f"<i>{ts_local}</i> · {item_count} new item"
        f"{'' if item_count == 1 else 's'} from {feed_count} feed"
        f"{'' if feed_count == 1 else 's'}"
    )

    def _feed_label(url: str) -> str:
        parsed = urlparse(url)
        host = parsed.netloc or url
        path = parsed.path.rstrip("/")
        generic_paths = {"/feed", "/rss", "/atom.xml", "/feed.xml", "/rss.xml"}
        if path and path not in generic_paths:
            label = f"{host}{path}"
        else:
            label = host
        return label[:80].rstrip("/") or url

    def _format_meta(author: str, ts_value: int | None) -> str:
        parts: List[str] = []
        if author:
            parts.append(author)
        if ts_value:
            try:
                parts.append(
                    datetime.fromtimestamp(ts_value, tz=timezone.utc)
                    .astimezone()
                    .strftime("%d %b %H:%M %Z")
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
        items = sorted(items, key=lambda x: x.get("published_ts", 0), reverse=True)
        cap = min(len(items), cfg.rss_digest_items_per_feed)

        escaped_url = _html.escape(url)
        escaped_label = _html.escape(_feed_label(url))
        lines.append("")
        lines.append(f"<b>🌐 {escaped_label}</b> <i>({len(items)} new)</i>")
        lines.append(f"<code>{escaped_url}</code>")

        included = 0
        for idx, it in enumerate(items[:cap], start=1):
            if total >= cfg.rss_digest_max_total:
                break
            title = _html.escape(" ".join(str(it.get("title") or "(no title)").split()))
            link = _html.escape(it.get("link") or "")
            author = _html.escape(it.get("author") or "")
            ts_value = it.get("published_ts")
            meta = _format_meta(author, ts_value)

            if link:
                header = f"{idx}. <a href=\"{link}\">{title}</a>"
            else:
                header = f"{idx}. <b>{title}</b>"
            if meta:
                header += f" <i>({meta})</i>"
            lines.append(header)

            raw_desc = it.get("description") or ""
            if raw_desc:
                snippet = _trim_snippet(raw_desc)
                if snippet:
                    lines.append(f"   ⤷ {_html.escape(snippet)}")

            total += 1
            included += 1
            if it.get("id"):
                delivered.setdefault(url, []).append(it["id"])

        more = max(0, len(items) - included)
        if more:
            lines.append(f"   ⤷ (+{more} more in the next digest)")

        if total >= cfg.rss_digest_max_total:
            omitted = max(0, item_count - total)
            if omitted:
                lines.append("")
                suffix = "" if omitted == 1 else "s"
                lines.append(
                    f"<i>Digest limit reached; {omitted} item{suffix} deferred to the next digest.</i>"
                )
            break

    if total == 0:
        return "(no new items)", {}
    return "\n".join(lines), delivered


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
    node_client: NodeExporterClient | None = None
    log: logging.Logger = logging.getLogger("tgbot.rss")

    def build_router(self) -> Router:
        router = Router()

        def _extract_urls(text: str) -> List[str]:
            """Extract http/https URLs from free-form text."""
            raw = re.findall(r"https?://\S+", text)
            cleaned: List[str] = []
            for url in raw:
                cleaned.append(url.rstrip(").,]>}\"'"))
            if cleaned:
                return cleaned
            # Fallback: parse per-line in case formatting hides URLs from regex
            candidates: List[str] = []
            for line in text.splitlines():
                line = line.strip().lstrip("•-*").strip()
                if not line:
                    continue
                candidates.append(line)
            return candidates

        @router.message(Command("rss_add"))
        async def rss_add(message: Message):
            if not self.cfg.is_chat_allowed(message.chat.id):
                return
            text = message.text or ""
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                await message.answer("Usage: /rss_add <url> (or multiple URLs, one per line)")
                return
            raw_payload = parts[1].strip()
            urls = _extract_urls(raw_payload)
            if not urls:
                await message.answer("Invalid URL (only http/https). Example:\n/rss_add https://example.com/feed")
                return

            try:
                existing_feeds = set(await self.rss.get_feeds(message.chat.id))
                added: List[str] = []
                skipped: List[str] = []
                invalid: List[str] = []
                failed: List[str] = []

                for url in urls:
                    if len(url) > 2000 or not _valid_url_http_https(url):
                        invalid.append(url)
                        continue
                    try:
                        await ensure_public_url(url)
                    except ValueError:
                        invalid.append(url)
                        continue
                    if url in existing_feeds or url in added:
                        skipped.append(url)
                        continue
                    try:
                        await self.rss.add_feed(message.chat.id, url)
                        added.append(url)
                    except Exception:
                        failed.append(url)

                updated_feeds = await self.rss.get_feeds(message.chat.id)
                lines = [f"✅ Added: {len(added)}", f"Total feeds: {len(updated_feeds)}"]
                if skipped:
                    lines.append(f"Skipped (already): {len(skipped)}")
                if invalid:
                    lines.append(f"Invalid: {len(invalid)}")
                if failed:
                    lines.append(f"Failed: {len(failed)}")
                if added:
                    lines.append("")
                    lines.append("Added feeds:")
                    for url in added:
                        lines.append(f"• {_html.escape(url)}")
                await message.answer("\n".join(lines))
            except Exception as e:
                self.log.error(f"Failed to add RSS feeds: {e}")
                await message.answer("❌ Failed to add feed(s). Please try again.")

        @router.message(Command("rss_rm"))
        async def rss_rm(message: Message):
            if not self.cfg.is_chat_allowed(message.chat.id):
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
            if not self.cfg.is_chat_allowed(message.chat.id):
                return
            feeds = await self.rss.get_feeds(message.chat.id)
            counts = await self.rss.get_pending_counts(message.chat.id)
            last = await self.rss.get_last_digest(message.chat.id)
            now = _time.time()
            lines = ["<b>RSS Subscriptions</b>"]
            if feeds:
                for u in feeds:
                    c = counts.get(u, 0)
                    lines.append(f"• {_html.escape(u)} (pending: {c})")
            else:
                lines.append("(none)")
            lines.append("\n" + _next_digest_text(last, now, self.cfg.rss_digest_interval_sec))
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
                            parsed, etag, modified = await self.client.parse(
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
                    await rss.update_feed_meta(url, etag, modified)

                    entries = list(getattr(parsed, "entries", []) or [])
                    meta = await rss.get_feed_meta(url)
                    seen = set(meta.get("seen_ids", []))
                    subscribers = await rss.subscribers(url)
                    for e in entries:
                        iid = (
                            getattr(e, "id", None)
                            or getattr(e, "link", None)
                            or str(getattr(e, "published_parsed", None))
                        )
                        if not iid:
                            continue
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
                        for cid in subscribers:
                            await rss.add_pending_item(cid, url, item)
                        await rss.add_seen_id(url, iid)
                        seen.add(iid)
                await rss.save()
                await rss.prune_sent_items()
            except Exception:
                self.log.warning("rss poll iteration failed", exc_info=True)
            await asyncio.sleep(cfg.rss_poll_interval_sec)

    async def send_digest(self, bot, cid, host, now: float) -> None:
        """Send one chat's pending digest, then acknowledge only what was sent."""
        pending = await self.rss.get_pending_digest(cid)
        if not any(pending.values()):
            await self.rss.set_last_digest(cid, now)
            await self.rss.save()
            return

        msg, delivered = _compose_rss_digest_html(host, pending, self.cfg)
        parts = _split_html_message(msg)
        payloads: List[tuple[int, str]] = []
        for idx, part in enumerate(parts, start=1):
            part_label = f" (Part {idx}/{len(parts)})" if len(parts) > 1 else ""
            payload = part + part_label
            if len(payload) > TELEGRAM_HTML_HARD_LIMIT:
                payload = payload[: TELEGRAM_HTML_HARD_LIMIT - 1] + "…"
            payloads.append((idx, payload))

        for idx, payload in payloads:
            self.log.debug(
                "Sending RSS digest chunk",
                extra={
                    "chat_id": cid,
                    "chunk_index": idx,
                    "chunk_total": len(payloads),
                    "chunk_length": len(payload),
                    "chunk_preview": payload[:120],
                },
            )
            if len(payload) >= TELEGRAM_HTML_HARD_LIMIT:
                self.log.warning(
                    "Digest chunk trimmed to telegram ceiling",
                    extra={
                        "chat_id": cid,
                        "chunk_index": idx,
                        "chunk_total": len(payloads),
                        "chunk_length": len(payload),
                        "chunk_preview": payload[:120],
                    },
                )
            await bot.send_message(
                cid,
                payload,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

        # Only now drop the items; a failed send leaves them pending for retry.
        await self.rss.remove_pending_items(cid, delivered)
        await self.rss.set_last_digest(cid, now)
        await self.rss.save()

    async def digest_loop(self, bot):
        cfg = self.cfg
        rss = self.rss
        while True:
            try:
                host = (
                    await fetch_host_display_name(
                        self.node_client,
                        self.cfg.host_display_name,
                    )
                    if self.node_client
                    else resolve_host_display_name(self.cfg.host_display_name)
                )
                # Find all chats that have RSS feeds
                chats = await rss.get_chat_ids()
                now = _time.time()
                for cid in chats:
                    last = await rss.get_last_digest(cid)
                    if now - last < cfg.rss_digest_interval_sec:
                        continue
                    try:
                        await self.send_digest(bot, cid, host, now)
                    except Exception:
                        # Keep this chat's pending items for the next attempt.
                        self.log.warning(
                            "rss digest delivery failed",
                            extra={"chat_id": cid},
                            exc_info=True,
                        )
            except Exception:
                self.log.warning("rss digest iteration failed", exc_info=True)
            await asyncio.sleep(cfg.rss_digest_interval_sec)
