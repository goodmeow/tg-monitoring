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

"""
Base class and types for node exporters
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ExporterType(Enum):
    """Available exporter types"""
    PYTHON = "python"
    DOCKER = "docker"
    
    @classmethod
    def from_string(cls, value: str) -> 'ExporterType':
        """Create from string value"""
        value = value.lower().strip()
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"Invalid exporter type: {value}")


class ExporterBase(ABC):
    """Base class for all node exporters"""
    
    def __init__(self, port: int = 9100, host: str = "0.0.0.0"):
        self.port = port
        self.host = host
        self.is_running = False
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    async def start(self) -> bool:
        """Start the exporter service asynchronously"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop the exporter service asynchronously"""
        pass
    
    @abstractmethod
    def status(self) -> Dict[str, Any]:
        """Get exporter status"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if exporter is healthy"""
        pass
    
    @property
    def metrics_url(self) -> str:
        """Get metrics endpoint URL"""
        return f"http://127.0.0.1:{self.port}/metrics"
    
    @property
    def exporter_type(self) -> ExporterType:
        """Get the exporter type"""
        raise NotImplementedError
    
    async def restart(self) -> bool:
        """Restart the exporter"""
        self.logger.info(f"Restarting {self.exporter_type.value} exporter...")
        await self.stop()
        return await self.start()
    
    async def __aenter__(self):
        """Async context manager support"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager cleanup"""
        await self.stop()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(port={self.port}, host={self.host}, running={self.is_running})"
