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
import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

import feedparser
import httpx

log = logging.getLogger(__name__)

# A feed larger than this is not worth 2 MB of bot memory.
MAX_FEED_BYTES = 2 * 1024 * 1024


async def ensure_public_url(url: str) -> None:
    """Reject feed URLs that point inside the host or private networks."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only http/https URLs are supported")
    host = parsed.hostname
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except OSError as exc:
        raise ValueError(f"cannot resolve host: {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ValueError(f"private or loopback address not allowed: {host}")


@dataclass
class FeedClient:
    timeout_sec: int = 10
    max_bytes: int = MAX_FEED_BYTES

    async def parse(
        self,
        url: str,
        *,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
    ) -> Tuple[Optional[Any], Optional[str], Optional[str]]:
        """Fetch and parse a feed without blocking the event loop.

        Returns (parsed, etag, last_modified); parsed is None on HTTP 304.
        """
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        async with httpx.AsyncClient(
            timeout=self.timeout_sec, follow_redirects=True
        ) as client:
            async with client.stream("GET", url, headers=headers) as response:
                if response.status_code == 304:
                    return None, etag, last_modified
                response.raise_for_status()
                # shortcut: a redirect to a private host is followed by httpx,
                # upgrade to a per-hop guard if feeds ever come from untrusted users.
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise ValueError("feed response too large")
                    chunks.append(chunk)
                data = b"".join(chunks)
                return (
                    feedparser.parse(data),
                    response.headers.get("etag"),
                    response.headers.get("last-modified"),
                )
