from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tgbot.domain.metrics import fetch_node_stats, NodeStats


@dataclass
class NodeExporterClient:
    url: str
    timeout_sec: int = 5

    async def fetch_stats(self, url: Optional[str] = None, timeout_sec: Optional[int] = None) -> NodeStats:
        return await fetch_node_stats(url or self.url, timeout_sec=timeout_sec or self.timeout_sec)
