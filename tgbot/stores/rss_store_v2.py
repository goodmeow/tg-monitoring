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

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from tgbot.core.database import DatabaseManager
from tgbot.core.repository import JsonRepository, NamespacedRepository
from tgbot.core.exceptions import StorageError

logger = logging.getLogger(__name__)


class PostgreSQLRssStore:
    """PostgreSQL-backed RSS store."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def add_feed(self, chat_id: int | str, url: str) -> None:
        """Add RSS feed for a chat."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            chat_id_int = int(chat_id)
            async with self.db_manager.connection() as conn:
                # Ensure chat exists
                await conn.execute(
                    """INSERT INTO chats (id) VALUES ($1) ON CONFLICT (id) DO NOTHING""",
                    chat_id_int
                )

                # Add feed
                await conn.execute(
                    """INSERT INTO rss_feeds (url, chat_id)
                       VALUES ($1, $2)
                       ON CONFLICT (url) DO UPDATE SET
                       chat_id = $2, is_active = true, updated_at = NOW()""",
                    url, chat_id_int
                )
        except Exception as e:
            logger.error(f"Failed to add feed {url} for chat {chat_id}: {e}")
            raise StorageError(f"Failed to add feed {url} for chat {chat_id}", {"chat_id": chat_id, "url": url}, e)

    async def remove_feed(self, chat_id: int | str, url: str) -> bool:
        """Remove RSS feed for a chat."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            chat_id_int = int(chat_id)
            async with self.db_manager.connection() as conn:
                result = await conn.execute(
                    "UPDATE rss_feeds SET is_active = false WHERE url = $1 AND chat_id = $2",
                    url, chat_id_int
                )
                return int(result.split()[-1]) > 0
        except Exception as e:
            logger.error(f"Failed to remove feed {url} for chat {chat_id}: {e}")
            raise StorageError(f"Failed to remove feed {url} for chat {chat_id}", {"chat_id": chat_id, "url": url}, e)

    async def get_feeds(self, chat_id: int | str) -> List[str]:
        """Get all active feeds for a chat."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            chat_id_int = int(chat_id)
            async with self.db_manager.connection() as conn:
                rows = await conn.fetch(
                    "SELECT url FROM rss_feeds WHERE chat_id = $1 AND is_active = true ORDER BY created_at",
                    chat_id_int
                )
                return [row['url'] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get feeds for chat {chat_id}: {e}")
            raise StorageError(f"Failed to get feeds for chat {chat_id}", {"chat_id": chat_id}, e)

    async def get_all_feeds(self) -> List[Dict[str, Any]]:
        """Get all active feeds across all chats."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            async with self.db_manager.connection() as conn:
                rows = await conn.fetch(
                    """SELECT id, url, title, description, chat_id, last_polled_at
                       FROM rss_feeds WHERE is_active = true ORDER BY created_at"""
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get all feeds: {e}")
            raise StorageError("Failed to get all feeds", cause=e)

    async def update_feed_metadata(self, url: str, title: Optional[str] = None, description: Optional[str] = None) -> None:
        """Update feed metadata."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            async with self.db_manager.connection() as conn:
                await conn.execute(
                    """UPDATE rss_feeds SET
                       title = COALESCE($2, title),
                       description = COALESCE($3, description),
                       last_polled_at = NOW(),
                       updated_at = NOW()
                       WHERE url = $1""",
                    url, title, description
                )
        except Exception as e:
            logger.error(f"Failed to update feed metadata for {url}: {e}")
            raise StorageError(f"Failed to update feed metadata for {url}", {"url": url}, e)

    async def add_item(self, feed_url: str, guid: str, title: str, link: str, description: str, pub_date: Optional[datetime] = None) -> bool:
        """Add RSS item if not already exists."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            async with self.db_manager.connection() as conn:
                # Get feed_id
                feed_row = await conn.fetchrow("SELECT id FROM rss_feeds WHERE url = $1", feed_url)
                if not feed_row:
                    return False

                feed_id = feed_row['id']

                # Insert item
                result = await conn.execute(
                    """INSERT INTO rss_items (feed_id, guid, title, link, description, pub_date)
                       VALUES ($1, $2, $3, $4, $5, $6)
                       ON CONFLICT (feed_id, guid) DO NOTHING""",
                    feed_id, guid, title, link, description, pub_date
                )
                return int(result.split()[-1]) > 0
        except Exception as e:
            logger.error(f"Failed to add item {guid} for feed {feed_url}: {e}")
            raise StorageError(f"Failed to add item {guid} for feed {feed_url}", {"feed_url": feed_url, "guid": guid}, e)

    async def get_unsent_items(self, chat_id: int | str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get unsent items for a chat."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            chat_id_int = int(chat_id)
            async with self.db_manager.connection() as conn:
                rows = await conn.fetch(
                    """SELECT i.id, i.guid, i.title, i.link, i.description, i.pub_date, f.url as feed_url
                       FROM rss_items i
                       JOIN rss_feeds f ON i.feed_id = f.id
                       WHERE f.chat_id = $1 AND f.is_active = true AND i.is_sent = false
                       ORDER BY i.pub_date DESC, i.created_at DESC
                       LIMIT $2""",
                    chat_id_int, limit
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get unsent items for chat {chat_id}: {e}")
            raise StorageError(f"Failed to get unsent items for chat {chat_id}", {"chat_id": chat_id}, e)

    async def mark_item_sent(self, item_id: int) -> None:
        """Mark RSS item as sent."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            async with self.db_manager.connection() as conn:
                await conn.execute("UPDATE rss_items SET is_sent = true WHERE id = $1", item_id)
        except Exception as e:
            logger.error(f"Failed to mark item {item_id} as sent: {e}")
            raise StorageError(f"Failed to mark item {item_id} as sent", {"item_id": item_id}, e)

    async def get_last_digest_time(self, chat_id: int | str) -> float:
        """Get last digest timestamp for a chat."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            chat_id_int = int(chat_id)
            async with self.db_manager.connection() as conn:
                row = await conn.fetchrow(
                    "SELECT value FROM monitoring_state WHERE key = $1 AND chat_id = $2",
                    f"rss_last_digest_{chat_id}", chat_id_int
                )
                if row:
                    value = json.loads(row['value']) if isinstance(row['value'], str) else row['value']
                    return float(value)
                return 0.0
        except Exception as e:
            logger.error(f"Failed to get last digest time for chat {chat_id}: {e}")
            return 0.0

    async def set_last_digest_time(self, chat_id: int | str, timestamp: float) -> None:
        """Set last digest timestamp for a chat."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            chat_id_int = int(chat_id)
            async with self.db_manager.connection() as conn:
                await conn.execute(
                    """INSERT INTO monitoring_state (key, value, chat_id)
                       VALUES ($1, $2, $3)
                       ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()""",
                    f"rss_last_digest_{chat_id}", json.dumps(timestamp), chat_id_int
                )
        except Exception as e:
            logger.error(f"Failed to set last digest time for chat {chat_id}: {e}")
            raise StorageError(f"Failed to set last digest time for chat {chat_id}", {"chat_id": chat_id}, e)


class HybridRssStore:
    """Hybrid RSS store that falls back to JSON if PostgreSQL is unavailable."""

    def __init__(self, db_manager: DatabaseManager, json_path: str, cache_size: int = 50, max_seen_ids: int = 50):
        self.pg_store = PostgreSQLRssStore(db_manager)
        self.json_store = AsyncRssStore(json_path, cache_size, max_seen_ids)
        self.db_manager = db_manager

    async def add_feed(self, chat_id: int | str, url: str) -> None:
        """Add RSS feed with fallback."""
        if self.db_manager.is_available:
            await self.pg_store.add_feed(chat_id, url)
        else:
            await self.json_store.add_feed(chat_id, url)

    async def remove_feed(self, chat_id: int | str, url: str) -> bool:
        """Remove RSS feed with fallback."""
        if self.db_manager.is_available:
            return await self.pg_store.remove_feed(chat_id, url)
        else:
            return await self.json_store.remove_feed(chat_id, url)

    async def get_feeds(self, chat_id: int | str) -> List[str]:
        """Get feeds with fallback."""
        if self.db_manager.is_available:
            return await self.pg_store.get_feeds(chat_id)
        else:
            return await self.json_store.get_feeds(chat_id)

    # Compatibility methods for existing services
    def all_feeds(self) -> List[str]:
        """Get all feed URLs across all chats (sync wrapper)."""
        import asyncio
        try:
            if self.db_manager.is_available:
                loop = asyncio.get_event_loop()
                feeds_data = loop.run_until_complete(self.pg_store.get_all_feeds())
                return [feed['url'] for feed in feeds_data]
            else:
                return self.json_store.all_feeds()
        except Exception:
            return []

    def get_feed_meta(self, url: str) -> Dict[str, Any]:
        """Get feed metadata (sync wrapper)."""
        try:
            if self.db_manager.is_available:
                # For PostgreSQL, return empty meta as it's handled differently
                return {"etag": None, "last_modified": None}
            else:
                return self.json_store.get_feed_meta(url)
        except Exception:
            return {"etag": None, "last_modified": None}

    def update_feed_meta(self, url: str, etag: str = None, last_modified: str = None) -> None:
        """Update feed metadata (sync wrapper)."""
        import asyncio
        try:
            if self.db_manager.is_available:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.pg_store.update_feed_metadata(url, None, None))
            else:
                self.json_store.update_feed_meta(url, etag, last_modified)
        except Exception:
            pass

    @property
    def data(self) -> Dict[str, Any]:
        """Compatibility property for direct data access."""
        try:
            if self.db_manager.is_available:
                # For PostgreSQL, we need to construct data structure on-the-fly
                import asyncio
                loop = asyncio.get_event_loop()

                # Get all feeds and group by chat_id
                feeds_data = loop.run_until_complete(self.pg_store.get_all_feeds())
                chats = {}
                for feed in feeds_data:
                    chat_id = str(feed['chat_id'])
                    if chat_id not in chats:
                        chats[chat_id] = {
                            "feeds": [],
                            "last_digest_ts": loop.run_until_complete(
                                self.pg_store.get_last_digest_time(chat_id)
                            )
                        }
                    chats[chat_id]["feeds"].append(feed['url'])

                return {"chats": chats, "feeds_meta": {}, "pending": {}}
            else:
                return self.json_store.data
        except Exception:
            return {"chats": {}, "feeds_meta": {}, "pending": {}}

    def get_last_digest(self, chat_id: int | str) -> float:
        """Get last digest timestamp (sync wrapper)."""
        import asyncio
        try:
            if self.db_manager.is_available:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self.pg_store.get_last_digest_time(chat_id))
            else:
                return self.json_store.get_last_digest(chat_id)
        except Exception:
            return 0.0

    def set_last_digest(self, chat_id: int | str, timestamp: float) -> None:
        """Set last digest timestamp (sync wrapper)."""
        import asyncio
        try:
            if self.db_manager.is_available:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.pg_store.set_last_digest_time(chat_id, timestamp))
            else:
                self.json_store.set_last_digest(chat_id, timestamp)
        except Exception:
            pass

    def pop_pending_digest(self, chat_id: int | str) -> Dict[str, List]:
        """Pop pending digest items (sync wrapper)."""
        try:
            if self.db_manager.is_available:
                # For PostgreSQL, get and mark items as sent
                import asyncio
                loop = asyncio.get_event_loop()
                items = loop.run_until_complete(self.pg_store.get_unsent_items(chat_id, 50))

                # Mark as sent
                for item in items:
                    loop.run_until_complete(self.pg_store.mark_item_sent(item['id']))

                # Group by feed URL
                result = {}
                for item in items:
                    feed_url = item['feed_url']
                    if feed_url not in result:
                        result[feed_url] = []
                    result[feed_url].append({
                        'title': item['title'],
                        'link': item['link'],
                        'description': item['description'],
                        'pub_date': item['pub_date']
                    })
                return result
            else:
                return self.json_store.pop_pending_digest(chat_id)
        except Exception:
            return {}

    def save(self) -> None:
        """Save data (compatibility method)."""
        try:
            if not self.db_manager.is_available:
                self.json_store.save()
        except Exception:
            pass


class AsyncRssStore:
    """JSON-based RSS store (legacy/fallback)."""

    def __init__(self, path: str, cache_size: int = 50, max_seen_ids: int = 50):
        self._repo = JsonRepository(path, cache_size)
        self._chats_repo = NamespacedRepository(self._repo, "chats")
        self._feeds_repo = NamespacedRepository(self._repo, "feeds_meta")
        self._pending_repo = NamespacedRepository(self._repo, "pending")
        self.max_seen_ids = max_seen_ids

    async def add_feed(self, chat_id: int | str, url: str):
        cid = str(chat_id)
        try:
            chat_data = await self._chats_repo.get(cid, {"feeds": [], "last_digest_ts": 0.0})
            feeds = chat_data.get("feeds", [])

            if url not in feeds:
                feeds.append(url)
                chat_data["feeds"] = feeds
                await self._chats_repo.set(cid, chat_data)

            feed_meta = await self._feeds_repo.get(url, {"etag": None, "last_modified": None, "seen_ids": []})
            await self._feeds_repo.set(url, feed_meta)
        except Exception as e:
            raise StorageError(f"Failed to add feed {url} for chat {chat_id}", {"chat_id": chat_id, "url": url}, e)

    async def remove_feed(self, chat_id: int | str, url: str) -> bool:
        cid = str(chat_id)
        try:
            chat_data = await self._chats_repo.get(cid, {"feeds": [], "last_digest_ts": 0.0})
            feeds = chat_data.get("feeds", [])

            if url in feeds:
                feeds.remove(url)
                chat_data["feeds"] = feeds
                await self._chats_repo.set(cid, chat_data)
                return True
            return False
        except Exception as e:
            raise StorageError(f"Failed to remove feed {url} for chat {chat_id}", {"chat_id": chat_id, "url": url}, e)

    async def get_feeds(self, chat_id: int | str) -> List[str]:
        cid = str(chat_id)
        try:
            chat_data = await self._chats_repo.get(cid, {"feeds": [], "last_digest_ts": 0.0})
            return chat_data.get("feeds", [])
        except Exception as e:
            raise StorageError(f"Failed to get feeds for chat {chat_id}", {"chat_id": chat_id}, e)

    def all_feeds(self) -> List[str]:
        """Get all feed URLs across all chats."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()

            # Get all chat data
            chat_keys = loop.run_until_complete(self._chats_repo.list_keys())
            urls = []
            for chat_id in chat_keys:
                chat_data = loop.run_until_complete(self._chats_repo.get(chat_id, {}))
                for url in chat_data.get("feeds", []):
                    if url not in urls:
                        urls.append(url)
            return urls
        except Exception:
            return []

    def get_feed_meta(self, url: str) -> Dict[str, Any]:
        """Get feed metadata."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._feeds_repo.get(url, {"etag": None, "last_modified": None, "seen_ids": []}))
        except Exception:
            return {"etag": None, "last_modified": None, "seen_ids": []}

    def update_feed_meta(self, url: str, etag: str = None, last_modified: str = None) -> None:
        """Update feed metadata."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            meta = loop.run_until_complete(self._feeds_repo.get(url, {"etag": None, "last_modified": None, "seen_ids": []}))
            if etag is not None:
                meta["etag"] = etag
            if last_modified is not None:
                meta["last_modified"] = last_modified
            loop.run_until_complete(self._feeds_repo.set(url, meta))
        except Exception:
            pass

    @property
    def data(self) -> Dict[str, Any]:
        """Direct access to underlying data."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._repo.get_all())
        except Exception:
            return {}

    def get_last_digest(self, chat_id: int | str) -> float:
        """Get last digest timestamp."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            cid = str(chat_id)
            chat_data = loop.run_until_complete(self._chats_repo.get(cid, {"last_digest_ts": 0.0}))
            return chat_data.get("last_digest_ts", 0.0)
        except Exception:
            return 0.0

    def set_last_digest(self, chat_id: int | str, timestamp: float) -> None:
        """Set last digest timestamp."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            cid = str(chat_id)
            chat_data = loop.run_until_complete(self._chats_repo.get(cid, {"feeds": [], "last_digest_ts": 0.0}))
            chat_data["last_digest_ts"] = timestamp
            loop.run_until_complete(self._chats_repo.set(cid, chat_data))
        except Exception:
            pass

    def pop_pending_digest(self, chat_id: int | str) -> Dict[str, List]:
        """Pop pending digest items."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            cid = str(chat_id)
            pending = loop.run_until_complete(self._pending_repo.get(cid, {}))
            # Clear pending after getting it
            loop.run_until_complete(self._pending_repo.set(cid, {}))
            return pending
        except Exception:
            return {}

    def save(self) -> None:
        """Save data to storage."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._repo.save())
        except Exception:
            pass

    async def list_feeds(self, chat_id: int | str) -> List[str]:
        cid = str(chat_id)
        try:
            chat_data = await self._chats_repo.get(cid, {"feeds": []})
            return list(chat_data.get("feeds", []))
        except Exception as e:
            raise StorageError(f"Failed to list feeds for chat {chat_id}", {"chat_id": chat_id}, e)

    async def all_feeds(self) -> List[str]:
        try:
            urls: List[str] = []
            chat_keys = await self._chats_repo.list_keys()

            for chat_key in chat_keys:
                chat_data = await self._chats_repo.get(chat_key, {"feeds": []})
                for url in chat_data.get("feeds", []):
                    if url not in urls:
                        urls.append(url)
            return urls
        except Exception as e:
            raise StorageError("Failed to get all feeds", cause=e)

    async def subscribers(self, url: str) -> List[str]:
        try:
            subs: List[str] = []
            chat_keys = await self._chats_repo.list_keys()

            for chat_key in chat_keys:
                chat_data = await self._chats_repo.get(chat_key, {"feeds": []})
                if url in chat_data.get("feeds", []):
                    subs.append(chat_key)
            return subs
        except Exception as e:
            raise StorageError(f"Failed to get subscribers for {url}", {"url": url}, e)

    async def add_pending_item(self, chat_id: int | str, url: str, item: Dict[str, Any]):
        cid = str(chat_id)
        key = f"{cid}:{url}"
        try:
            pending_items = await self._pending_repo.get(key, [])

            item_id = item.get("id")
            if item_id and any(x.get("id") == item_id for x in pending_items):
                return

            pending_items.append(item)
            await self._pending_repo.set(key, pending_items)
        except Exception as e:
            raise StorageError(f"Failed to add pending item for {chat_id}:{url}", {"chat_id": chat_id, "url": url}, e)

    async def pop_pending_digest(self, chat_id: int | str) -> Dict[str, List[Dict[str, Any]]]:
        cid = str(chat_id)
        try:
            digest = {}
            prefix = f"{cid}:"
            pending_keys = await self._pending_repo.list_keys(prefix)

            for key in pending_keys:
                url = key[len(prefix):]
                items = await self._pending_repo.get(key, [])
                if items:
                    digest[url] = items
                    await self._pending_repo.delete(key)

            return digest
        except Exception as e:
            raise StorageError(f"Failed to pop pending digest for chat {chat_id}", {"chat_id": chat_id}, e)

    async def get_pending_counts(self, chat_id: int | str) -> Dict[str, int]:
        cid = str(chat_id)
        try:
            counts = {}
            prefix = f"{cid}:"
            pending_keys = await self._pending_repo.list_keys(prefix)

            for key in pending_keys:
                url = key[len(prefix):]
                items = await self._pending_repo.get(key, [])
                counts[url] = len(items)

            return counts
        except Exception as e:
            raise StorageError(f"Failed to get pending counts for chat {chat_id}", {"chat_id": chat_id}, e)

    async def set_last_digest(self, chat_id: int | str, ts: float):
        cid = str(chat_id)
        try:
            chat_data = await self._chats_repo.get(cid, {"feeds": [], "last_digest_ts": 0.0})
            chat_data["last_digest_ts"] = ts
            await self._chats_repo.set(cid, chat_data)
        except Exception as e:
            raise StorageError(f"Failed to set last digest for chat {chat_id}", {"chat_id": chat_id, "ts": ts}, e)

    async def get_last_digest(self, chat_id: int | str) -> float:
        cid = str(chat_id)
        try:
            chat_data = await self._chats_repo.get(cid, {"last_digest_ts": 0.0})
            return float(chat_data.get("last_digest_ts", 0.0))
        except Exception as e:
            raise StorageError(f"Failed to get last digest for chat {chat_id}", {"chat_id": chat_id}, e)

    async def get_feed_meta(self, url: str) -> Dict[str, Any]:
        try:
            return await self._feeds_repo.get(url, {"etag": None, "last_modified": None, "seen_ids": []})
        except Exception as e:
            raise StorageError(f"Failed to get feed meta for {url}", {"url": url}, e)

    async def update_feed_meta(self, url: str, etag: Optional[str], last_modified: Optional[str]):
        try:
            meta = await self._feeds_repo.get(url, {"etag": None, "last_modified": None, "seen_ids": []})
            if etag is not None:
                meta["etag"] = etag
            if last_modified is not None:
                meta["last_modified"] = last_modified
            await self._feeds_repo.set(url, meta)
        except Exception as e:
            raise StorageError(f"Failed to update feed meta for {url}", {"url": url}, e)

    async def add_seen_id(self, url: str, item_id: str):
        try:
            meta = await self._feeds_repo.get(url, {"etag": None, "last_modified": None, "seen_ids": []})
            seen_ids = meta.get("seen_ids", [])

            if item_id in seen_ids:
                return

            seen_ids.append(item_id)
            if len(seen_ids) > self.max_seen_ids:
                seen_ids = seen_ids[-self.max_seen_ids:]

            meta["seen_ids"] = seen_ids
            await self._feeds_repo.set(url, meta)
        except Exception as e:
            raise StorageError(f"Failed to add seen ID for {url}", {"url": url, "item_id": item_id}, e)

    async def flush(self):
        try:
            await self._repo.flush()
        except Exception as e:
            raise StorageError("Failed to flush RSS store", cause=e)

    async def size(self) -> int:
        return await self._repo.size()


class RssStore:
    def __init__(self, path: str):
        self.path = path
        self._async_store = AsyncRssStore(path)

    def add_feed(self, chat_id: int | str, url: str):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_store.add_feed(chat_id, url))
        finally:
            loop.close()

    def remove_feed(self, chat_id: int | str, url: str):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_store.remove_feed(chat_id, url))
        finally:
            loop.close()

    def list_feeds(self, chat_id: int | str) -> List[str]:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._async_store.list_feeds(chat_id))
        finally:
            loop.close()

    def all_feeds(self) -> List[str]:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._async_store.all_feeds())
        finally:
            loop.close()

    def subscribers(self, url: str) -> List[str]:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._async_store.subscribers(url))
        finally:
            loop.close()

    def add_pending_item(self, chat_id: int | str, url: str, item: Dict[str, Any]):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_store.add_pending_item(chat_id, url, item))
        finally:
            loop.close()

    def pop_pending_digest(self, chat_id: int | str) -> Dict[str, List[Dict[str, Any]]]:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._async_store.pop_pending_digest(chat_id))
        finally:
            loop.close()

    def get_pending_counts(self, chat_id: int | str) -> Dict[str, int]:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._async_store.get_pending_counts(chat_id))
        finally:
            loop.close()

    def get_chat(self, chat_id: int | str) -> Dict[str, Any]:
        cid = str(chat_id)
        feeds = self.list_feeds(cid)
        last_digest_ts = self.get_last_digest(cid)
        pending_counts = self.get_pending_counts(cid)

        pending = {}
        for url, count in pending_counts.items():
            if count > 0:
                pending[url] = [{"placeholder": True}] * count

        return {
            "feeds": feeds,
            "last_digest_ts": last_digest_ts,
            "pending": pending
        }

    def set_last_digest(self, chat_id: int | str, ts: float):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_store.set_last_digest(chat_id, ts))
        finally:
            loop.close()

    def get_last_digest(self, chat_id: int | str) -> float:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._async_store.get_last_digest(chat_id))
        finally:
            loop.close()

    def get_feed_meta(self, url: str) -> Dict[str, Any]:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._async_store.get_feed_meta(url))
        finally:
            loop.close()

    def update_feed_meta(self, url: str, etag: Optional[str], last_modified: Optional[str]):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_store.update_feed_meta(url, etag, last_modified))
        finally:
            loop.close()

    def add_seen_id(self, url: str, iid: str, max_keep: int = 200):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_store.add_seen_id(url, iid))
        finally:
            loop.close()

    def save(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_store.flush())
        finally:
            loop.close()

    def load(self):
        pass