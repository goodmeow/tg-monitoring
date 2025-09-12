from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import feedparser


@dataclass
class FeedClient:
    """Thin wrapper around feedparser to allow mocking and retries later."""

    def parse(self, url: str, *, etag: Optional[str] = None, last_modified: Optional[str] = None) -> Any:
        return feedparser.parse(url, etag=etag, modified=last_modified)

