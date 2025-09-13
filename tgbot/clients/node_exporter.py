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

from dataclasses import dataclass
from typing import Optional

from tgbot.domain.metrics import fetch_node_stats, NodeStats


@dataclass
class NodeExporterClient:
    url: str
    timeout_sec: int = 5

    async def fetch_stats(self, url: Optional[str] = None, timeout_sec: Optional[int] = None) -> NodeStats:
        return await fetch_node_stats(url or self.url, timeout_sec=timeout_sec or self.timeout_sec)
