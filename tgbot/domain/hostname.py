from __future__ import annotations

import logging
import socket
from typing import Protocol

from tgbot.domain.metrics import NodeStats

log = logging.getLogger(__name__)


class StatsClient(Protocol):
    async def fetch_stats(self) -> NodeStats:
        ...


def resolve_host_display_name(
    configured_hostname: str | None = None,
    stats: NodeStats | None = None,
) -> str:
    """Resolve the server-host display name with safe fallbacks."""
    if configured_hostname:
        return configured_hostname
    if stats and stats.hostname:
        return stats.hostname
    return socket.gethostname()


async def fetch_host_display_name(
    client: StatsClient,
    configured_hostname: str | None = None,
) -> str:
    """Resolve host name from config or node_exporter when possible."""
    if configured_hostname:
        return configured_hostname
    try:
        stats = await client.fetch_stats()
    except Exception:
        log.debug("failed to fetch node stats for hostname", exc_info=True)
        return socket.gethostname()
    return resolve_host_display_name(None, stats)
