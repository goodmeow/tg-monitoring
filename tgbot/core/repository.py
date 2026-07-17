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
import os
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager


class RepositoryError(Exception):
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}


class Repository(ABC):
    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> List[str]:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    async def size(self) -> int:
        pass

    @asynccontextmanager
    async def transaction(self):
        yield self


class JsonRepository(Repository):
    def __init__(self, file_path: str, cache_size: int = 100):
        self.file_path = file_path
        self.cache_size = cache_size
        self._cache: Dict[str, Any] = {}
        self._cache_order: List[str] = []
        self._lock = asyncio.Lock()
        self._dirty_keys: set[str] = set()
        self._ensure_dir()

    def _ensure_dir(self):
        d = os.path.dirname(self.file_path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    async def _load_data(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(self.file_path):
                return {}

            if os.path.getsize(self.file_path) == 0:
                return {}

            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
        except Exception as e:
            raise RepositoryError(f"Failed to load {self.file_path}", {"error": str(e)})

    async def _save_data(self, data: Dict[str, Any]) -> None:
        tmp_path = self.file_path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.file_path)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise RepositoryError(f"Failed to save {self.file_path}", {"error": str(e)})

    def _evict_cache(self):
        while len(self._cache) >= self.cache_size:
            oldest_key = self._cache_order.pop(0)
            self._cache.pop(oldest_key, None)
            self._dirty_keys.discard(oldest_key)

    def _touch_cache(self, key: str):
        if key in self._cache_order:
            self._cache_order.remove(key)
        self._cache_order.append(key)

    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            if key in self._cache:
                self._touch_cache(key)
                return self._cache[key]

            data = await self._load_data()
            value = data.get(key, default)

            self._evict_cache()
            self._cache[key] = value
            self._touch_cache(key)

            return value

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._evict_cache()
            self._cache[key] = value
            self._touch_cache(key)
            self._dirty_keys.add(key)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            data = await self._load_data()
            existed = key in data

            if existed:
                del data[key]
                await self._save_data(data)

            self._cache.pop(key, None)
            if key in self._cache_order:
                self._cache_order.remove(key)
            self._dirty_keys.discard(key)

            return existed

    async def exists(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                return True
            data = await self._load_data()
            return key in data

    async def list_keys(self, prefix: str = "") -> List[str]:
        async with self._lock:
            data = await self._load_data()
            return [k for k in data.keys() if k.startswith(prefix)]

    async def clear(self) -> None:
        async with self._lock:
            await self._save_data({})
            self._cache.clear()
            self._cache_order.clear()
            self._dirty_keys.clear()

    async def size(self) -> int:
        async with self._lock:
            data = await self._load_data()
            return len(data)

    async def flush(self) -> None:
        async with self._lock:
            if not self._dirty_keys:
                return

            data = await self._load_data()
            for key in self._dirty_keys:
                if key in self._cache:
                    data[key] = self._cache[key]

            await self._save_data(data)
            self._dirty_keys.clear()

    @asynccontextmanager
    async def transaction(self):
        async with self._lock:
            try:
                yield self
            finally:
                await self.flush()


class NamespacedRepository:
    def __init__(self, repo: Repository, namespace: str):
        self.repo = repo
        self.namespace = namespace

    def _key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        return await self.repo.get(self._key(key), default)

    async def set(self, key: str, value: Any) -> None:
        await self.repo.set(self._key(key), value)

    async def delete(self, key: str) -> bool:
        return await self.repo.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        return await self.repo.exists(self._key(key))

    async def list_keys(self, prefix: str = "") -> List[str]:
        full_prefix = self._key(prefix)
        keys = await self.repo.list_keys(full_prefix)
        ns_len = len(self.namespace) + 1
        return [k[ns_len:] for k in keys]

    async def clear(self) -> None:
        keys = await self.list_keys()
        for key in keys:
            await self.delete(key)

    async def size(self) -> int:
        keys = await self.list_keys()
        return len(keys)

    @asynccontextmanager
    async def transaction(self):
        async with self.repo.transaction():
            yield self