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

import os
from dataclasses import dataclass
from typing import List, Optional


def _load_dotenv(path: str) -> dict:
    data: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                data[k] = v
    except FileNotFoundError:
        pass
    return data


def _get(env: dict, name: str, default: Optional[str] = None) -> Optional[str]:
    # Support lowercase and uppercase keys
    return os.environ.get(name) or os.environ.get(name.upper()) or env.get(name) or env.get(name.upper()) or default


def _get_bool(env: dict, name: str, default: bool = False) -> bool:
    val = _get(env, name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(env: dict, name: str, default: int) -> int:
    val = _get(env, name)
    if val is None:
        return default
    try:
        return int(val)
    except Exception:
        return default


def _get_float(env: dict, name: str, default: float) -> float:
    val = _get(env, name)
    if val is None:
        return default
    try:
        return float(val)
    except Exception:
        return default


def _get_list(env: dict, name: str, default: List[str]) -> List[str]:
    val = _get(env, name)
    if val is None:
        return default
    parts = [p.strip() for p in val.split(",")]
    return [p for p in parts if p]


@dataclass
class Config:
    bot_token: str
    chat_id: str  # accept numeric or @channel username
    node_exporter_url: str = "http://127.0.0.1:9100/metrics"

    sample_interval_sec: int = 15
    alert_min_consecutive: int = 3

    cpu_load_per_core_warn: float = 0.9
    mem_available_pct_warn: float = 0.10
    disk_usage_pct_warn: float = 0.85
    enable_inodes: bool = False
    inode_free_pct_warn: float = 0.10

    exclude_fs_types: List[str] = None  # set in factory
    state_file: str = "data/state.json"

    http_timeout_sec: int = 5
    long_poll_timeout_sec: int = 50
    control_chat_id: Optional[str] = None  # if None, fallback to chat_id

    # RSS settings
    rss_store_file: str = "data/rss.json"
    rss_poll_interval_sec: int = 300  # 5 minutes
    rss_digest_interval_sec: int = 3600  # 1 hour
    rss_digest_items_per_feed: int = 5
    rss_digest_max_total: int = 40

    @property
    def allowed_chat_ids(self) -> List[int | str]:
        ids: List[int | str] = []
        for c in [self.chat_id, self.control_chat_id or self.chat_id]:
            if c is None:
                continue
            try:
                ids.append(int(c))
            except Exception:
                ids.append(c)
        return list(dict.fromkeys(ids))  # dedupe


def load_config() -> Config:
    envfile = os.environ.get("ENV_FILE", ".env")
    env = _load_dotenv(envfile)

    bot_token = _get(env, "bot_token")
    chat_id = _get(env, "chat_id")
    if not bot_token or not chat_id:
        raise RuntimeError("bot_token and chat_id must be set in .env or environment")

    node_exporter_url = _get(env, "NODE_EXPORTER_URL", "http://127.0.0.1:9100/metrics")
    sample_interval_sec = _get_int(env, "SAMPLE_INTERVAL_SEC", 15)
    alert_min_consecutive = _get_int(env, "ALERT_MIN_CONSECUTIVE", 3)

    cpu_load_per_core_warn = _get_float(env, "CPU_LOAD_PER_CORE_WARN", 0.9)
    mem_available_pct_warn = _get_float(env, "MEM_AVAILABLE_PCT_WARN", 0.10)
    disk_usage_pct_warn = _get_float(env, "DISK_USAGE_PCT_WARN", 0.85)
    enable_inodes = _get_bool(env, "ENABLE_INODES", False)
    inode_free_pct_warn = _get_float(env, "INODE_FREE_PCT_WARN", 0.10)

    exclude_fs_types = _get_list(
        env,
        "EXCLUDE_FS_TYPES",
        [
            "tmpfs",
            "devtmpfs",
            "overlay",
            "squashfs",
            "proc",
            "sysfs",
            "cgroup",
            "cgroup2",
            "debugfs",
            "rpc_pipefs",
            "nsfs",
            "autofs",
            "tracefs",
            "fusectl",
            "configfs",
            "binfmt_misc",
        ],
    )

    state_file = _get(env, "STATE_FILE", "data/state.json")
    http_timeout_sec = _get_int(env, "HTTP_TIMEOUT_SEC", 5)
    long_poll_timeout_sec = _get_int(env, "LONG_POLL_TIMEOUT_SEC", 50)
    control_chat_id = _get(env, "CONTROL_CHAT_ID", None)

    # RSS
    rss_store_file = _get(env, "RSS_STORE_FILE", "data/rss.json")
    rss_poll_interval_sec = _get_int(env, "RSS_POLL_INTERVAL_SEC", 300)
    rss_digest_interval_sec = _get_int(env, "RSS_DIGEST_INTERVAL_SEC", 3600)
    rss_digest_items_per_feed = _get_int(env, "RSS_DIGEST_ITEMS_PER_FEED", 5)
    rss_digest_max_total = _get_int(env, "RSS_DIGEST_MAX_TOTAL", 40)

    return Config(
        bot_token=bot_token,
        chat_id=chat_id,
        node_exporter_url=node_exporter_url,
        sample_interval_sec=sample_interval_sec,
        alert_min_consecutive=alert_min_consecutive,
        cpu_load_per_core_warn=cpu_load_per_core_warn,
        mem_available_pct_warn=mem_available_pct_warn,
        disk_usage_pct_warn=disk_usage_pct_warn,
        enable_inodes=enable_inodes,
        inode_free_pct_warn=inode_free_pct_warn,
        exclude_fs_types=exclude_fs_types,
        state_file=state_file,
        http_timeout_sec=http_timeout_sec,
        long_poll_timeout_sec=long_poll_timeout_sec,
        control_chat_id=control_chat_id,
        rss_store_file=rss_store_file,
        rss_poll_interval_sec=rss_poll_interval_sec,
        rss_digest_interval_sec=rss_digest_interval_sec,
        rss_digest_items_per_feed=rss_digest_items_per_feed,
        rss_digest_max_total=rss_digest_max_total,
    )

