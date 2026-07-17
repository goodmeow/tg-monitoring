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
import gc
import os
import psutil
import resource
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable
from tgbot.core.exceptions import MemoryError


@dataclass
class MemoryStats:
    rss_mb: float
    vms_mb: float
    percent: float
    available_mb: float
    gc_objects: int
    gc_collections: tuple[int, int, int]


class MemoryMonitor:
    def __init__(self, alert_threshold_mb: int = 100, warning_threshold_mb: int = 50):
        self.alert_threshold_mb = alert_threshold_mb
        self.warning_threshold_mb = warning_threshold_mb
        self._callbacks: Dict[str, Callable[[MemoryStats], None]] = {}
        self._process = psutil.Process(os.getpid())

    def add_callback(self, name: str, callback: Callable[[MemoryStats], None]):
        self._callbacks[name] = callback

    def remove_callback(self, name: str):
        self._callbacks.pop(name, None)

    def get_stats(self) -> MemoryStats:
        try:
            mem_info = self._process.memory_info()
            system_mem = psutil.virtual_memory()
            gc_stats = gc.get_stats()

            return MemoryStats(
                rss_mb=mem_info.rss / 1024 / 1024,
                vms_mb=mem_info.vms / 1024 / 1024,
                percent=self._process.memory_percent(),
                available_mb=system_mem.available / 1024 / 1024,
                gc_objects=len(gc.get_objects()),
                gc_collections=tuple(stat['collections'] for stat in gc_stats)
            )
        except Exception as e:
            raise MemoryError("Failed to get memory stats", cause=e)

    def check_thresholds(self, stats: MemoryStats) -> Optional[str]:
        if stats.rss_mb > self.alert_threshold_mb:
            return "alert"
        elif stats.rss_mb > self.warning_threshold_mb:
            return "warning"
        return None

    def force_gc(self) -> int:
        collected = gc.collect()
        return collected

    def get_memory_usage_by_type(self) -> Dict[str, int]:
        type_counts = {}
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        return dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    async def monitor_loop(self, interval_seconds: int = 30):
        while True:
            try:
                stats = self.get_stats()
                level = self.check_thresholds(stats)

                if level:
                    for callback in self._callbacks.values():
                        try:
                            callback(stats)
                        except Exception:
                            pass

                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(interval_seconds)

    def get_resource_limits(self) -> Dict[str, Any]:
        try:
            return {
                "max_memory_mb": resource.getrlimit(resource.RLIMIT_AS)[0] / 1024 / 1024 if resource.getrlimit(resource.RLIMIT_AS)[0] != resource.RLIM_INFINITY else None,
                "max_processes": resource.getrlimit(resource.RLIMIT_NPROC)[0] if resource.getrlimit(resource.RLIMIT_NPROC)[0] != resource.RLIM_INFINITY else None,
                "max_open_files": resource.getrlimit(resource.RLIMIT_NOFILE)[0] if resource.getrlimit(resource.RLIMIT_NOFILE)[0] != resource.RLIM_INFINITY else None,
            }
        except Exception as e:
            raise MemoryError("Failed to get resource limits", cause=e)