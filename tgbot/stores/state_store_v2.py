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
from typing import Any, Dict, Optional, AsyncIterator

from tgbot.core.database import DatabaseManager
from tgbot.core.repository import JsonRepository, NamespacedRepository
from tgbot.core.exceptions import StorageError

logger = logging.getLogger(__name__)


class PostgreSQLStateStore:
    """PostgreSQL-backed state store for monitoring data."""

    def __init__(self, db_manager: DatabaseManager, chat_id: Optional[int] = None):
        self.db_manager = db_manager
        self.chat_id = chat_id

    async def get_check(self, key: str) -> Dict[str, Any]:
        """Get monitoring check state."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            async with self.db_manager.connection() as conn:
                row = await conn.fetchrow(
                    "SELECT value FROM monitoring_state WHERE key = $1 AND (chat_id = $2 OR chat_id IS NULL)",
                    f"check_{key}", self.chat_id
                )
                if row:
                    return json.loads(row['value']) if isinstance(row['value'], str) else row['value']
                return {}
        except Exception as e:
            logger.error(f"Failed to get check {key}: {e}")
            raise StorageError(f"Failed to get check {key}", {"key": key}, e)

    async def set_check(self, key: str, value: Dict[str, Any]) -> None:
        """Set monitoring check state."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            async with self.db_manager.connection() as conn:
                await conn.execute(
                    """INSERT INTO monitoring_state (key, value, chat_id)
                       VALUES ($1, $2, $3)
                       ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()""",
                    f"check_{key}", json.dumps(value), self.chat_id
                )
        except Exception as e:
            logger.error(f"Failed to set check {key}: {e}")
            raise StorageError(f"Failed to set check {key}", {"key": key}, e)

    async def iter_checks(self) -> AsyncIterator[tuple[str, Dict[str, Any]]]:
        """Iterate over all monitoring checks."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            async with self.db_manager.connection() as conn:
                async with conn.transaction():
                    cursor = await conn.cursor(
                        "SELECT key, value FROM monitoring_state WHERE key LIKE 'check_%' AND (chat_id = $1 OR chat_id IS NULL)",
                        self.chat_id
                    )
                    async for row in cursor:
                        key = row['key'].replace('check_', '', 1)
                        value = json.loads(row['value']) if isinstance(row['value'], str) else row['value']
                        yield key, value
        except Exception as e:
            logger.error(f"Failed to iterate checks: {e}")
            raise StorageError("Failed to iterate checks", cause=e)

    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a general setting."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            async with self.db_manager.connection() as conn:
                row = await conn.fetchrow("SELECT value FROM settings WHERE key = $1", key)
                if row:
                    return json.loads(row['value']) if isinstance(row['value'], str) else row['value']
                return default
        except Exception as e:
            logger.error(f"Failed to get setting {key}: {e}")
            raise StorageError(f"Failed to get setting {key}", {"key": key}, e)

    async def set_setting(self, key: str, value: Any) -> None:
        """Set a general setting."""
        if not self.db_manager.is_available:
            raise StorageError("Database not available")

        try:
            async with self.db_manager.connection() as conn:
                await conn.execute(
                    """INSERT INTO settings (key, value)
                       VALUES ($1, $2)
                       ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()""",
                    key, json.dumps(value)
                )
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            raise StorageError(f"Failed to set setting {key}", {"key": key}, e)


class HybridStateStore:
    """Hybrid state store that falls back to JSON if PostgreSQL is unavailable."""

    def __init__(self, db_manager: DatabaseManager, json_path: str, cache_size: int = 50, chat_id: Optional[int] = None):
        self.pg_store = PostgreSQLStateStore(db_manager, chat_id)
        self.json_store = AsyncStateStore(json_path, cache_size)
        self.db_manager = db_manager

    async def get_check(self, key: str) -> Dict[str, Any]:
        """Get monitoring check state with fallback."""
        if self.db_manager.is_available:
            return await self.pg_store.get_check(key)
        return await self.json_store.get_check(key)

    async def set_check(self, key: str, value: Dict[str, Any]) -> None:
        """Set monitoring check state with fallback."""
        if self.db_manager.is_available:
            await self.pg_store.set_check(key, value)
        else:
            await self.json_store.set_check(key, value)

    async def iter_checks(self) -> AsyncIterator[tuple[str, Dict[str, Any]]]:
        """Iterate over monitoring checks with fallback."""
        if self.db_manager.is_available:
            async for item in self.pg_store.iter_checks():
                yield item
        else:
            async for item in self.json_store.iter_checks():
                yield item


class AsyncStateStore:
    """JSON-based state store (legacy/fallback)."""

    def __init__(self, path: str, cache_size: int = 50):
        self._repo = JsonRepository(path, cache_size)
        self._checks_repo = NamespacedRepository(self._repo, "checks")

    async def get_check(self, key: str) -> Dict[str, Any]:
        try:
            return await self._checks_repo.get(key, {})
        except Exception as e:
            raise StorageError(f"Failed to get check {key}", {"key": key}, e)

    async def set_check(self, key: str, value: Dict[str, Any]):
        try:
            await self._checks_repo.set(key, value)
        except Exception as e:
            raise StorageError(f"Failed to set check {key}", {"key": key}, e)

    async def iter_checks(self) -> AsyncIterator[tuple[str, Dict[str, Any]]]:
        try:
            keys = await self._checks_repo.list_keys()
            for key in keys:
                value = await self._checks_repo.get(key, {})
                yield key, value
        except Exception as e:
            raise StorageError("Failed to iterate checks", cause=e)

    async def set_last_update_id(self, update_id: Optional[int]):
        try:
            await self._repo.set("last_update_id", update_id)
        except Exception as e:
            raise StorageError("Failed to set last_update_id", {"update_id": update_id}, e)

    async def get_last_update_id(self) -> Optional[int]:
        try:
            return await self._repo.get("last_update_id")
        except Exception as e:
            raise StorageError("Failed to get last_update_id", cause=e)

    async def flush(self):
        try:
            await self._repo.flush()
        except Exception as e:
            raise StorageError("Failed to flush state store", cause=e)

    async def size(self) -> int:
        return await self._repo.size()


class StateStore:
    def __init__(self, path: str):
        self.path = path
        self._async_store = AsyncStateStore(path)
        self._sync_cache: Dict[str, Any] = {}
        self._cache_dirty = False

    async def _sync_to_async(self):
        if not self._cache_dirty:
            return

        for key, value in self._sync_cache.items():
            if key.startswith("check:"):
                check_key = key[6:]
                await self._async_store.set_check(check_key, value)
            elif key == "last_update_id":
                await self._async_store.set_last_update_id(value)

        await self._async_store.flush()
        self._cache_dirty = False

    def get_check(self, key: str) -> Dict[str, Any]:
        cache_key = f"check:{key}"
        if cache_key in self._sync_cache:
            return dict(self._sync_cache[cache_key])
        return {}

    def set_check(self, key: str, value: Dict[str, Any]):
        cache_key = f"check:{key}"
        self._sync_cache[cache_key] = dict(value)
        self._cache_dirty = True

    def iter_checks(self):
        for key, value in self._sync_cache.items():
            if key.startswith("check:"):
                check_key = key[6:]
                yield check_key, dict(value)

    def set_last_update_id(self, update_id: Optional[int]):
        self._sync_cache["last_update_id"] = update_id
        self._cache_dirty = True

    def get_last_update_id(self) -> Optional[int]:
        return self._sync_cache.get("last_update_id")

    def save(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._sync_to_async())
        finally:
            loop.close()

    def load(self):
        pass