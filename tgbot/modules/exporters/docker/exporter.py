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
Docker-based Node Exporter implementation
Wrapper untuk existing Docker node-exporter container
"""

import asyncio
import subprocess
import json
from typing import Dict, Any, Optional

from ..base import ExporterBase, ExporterType


class DockerExporter(ExporterBase):
    """Docker-based implementation of Node Exporter"""
    
    CONTAINER_NAME = "node-exporter"
    IMAGE_NAME = "prom/node-exporter:latest"
    
    def __init__(self, port: int = 9100, host: str = "0.0.0.0"):
        super().__init__(port, host)
        self.container_id = None
        self._check_existing_container()
        
    @property
    def exporter_type(self) -> ExporterType:
        return ExporterType.DOCKER
        
    def _check_existing_container(self):
        """Check if container already exists and get its state"""
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={self.CONTAINER_NAME}", "--format", "{{.ID}}"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                self.container_id = result.stdout.strip()
                
                # Check if running
                status_result = subprocess.run(
                    ["docker", "inspect", self.CONTAINER_NAME, "--format", "{{.State.Running}}"],
                    capture_output=True, text=True, timeout=5
                )
                if status_result.returncode == 0:
                    self.is_running = status_result.stdout.strip().lower() == "true"
                    
        except Exception as e:
            self.logger.debug(f"Error checking existing container: {e}")
    
    async def start(self) -> bool:
        """Start the Docker exporter container"""
        if self.is_running:
            self.logger.info("Docker exporter already running")
            return True
        
        try:
            # Check Docker availability
            result = await asyncio.create_subprocess_exec(
                "docker", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            
            if result.returncode != 0:
                self.logger.error("Docker is not available")
                return False
            
            # If container exists, just start it
            if self.container_id:
                self.logger.info(f"Starting existing container: {self.CONTAINER_NAME}")
                result = await asyncio.create_subprocess_exec(
                    "docker", "start", self.CONTAINER_NAME,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.wait()
                
                if result.returncode == 0:
                    self.is_running = True
                    await asyncio.sleep(2)
                    self.logger.info("Docker exporter started (existing container)")
                    return True
            
            # Create new container
            self.logger.info("Creating new Docker exporter container")
            
            # Remove old container if exists
            if self.container_id:
                await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", self.CONTAINER_NAME,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            # Run new container
            cmd = [
                "docker", "run", "-d",
                "--name", self.CONTAINER_NAME,
                "--restart", "unless-stopped",
                "-p", f"{self.port}:9100",
                "-v", "/:/host:ro,rslave",
                self.IMAGE_NAME,
                "--path.rootfs=/host",
                "--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($|/)"
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                self.container_id = stdout.decode().strip()
                self.is_running = True
                await asyncio.sleep(3)
                self.logger.info(f"Docker exporter created and started: {self.container_id[:12]}")
                return True
            else:
                self.logger.error(f"Failed to start Docker exporter: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting Docker exporter: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the Docker exporter container"""
        if not self.is_running:
            return True
        
        try:
            # Stop container (don't remove)
            result = await asyncio.create_subprocess_exec(
                "docker", "stop", self.CONTAINER_NAME,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            
            if result.returncode == 0:
                self.is_running = False
                self.logger.info("Docker exporter stopped")
                return True
            else:
                self.logger.error("Failed to stop Docker exporter")
                return False
                
        except Exception as e:
            self.logger.error(f"Error stopping Docker exporter: {e}")
            return False
    
    def status(self) -> Dict[str, Any]:
        """Get exporter status"""
        container_info = self._get_container_info()
        
        status_dict = {
            "type": self.exporter_type.value,
            "running": self.is_running,
            "port": self.port,
            "host": self.host,
            "container_id": self.container_id,
            "container_name": self.CONTAINER_NAME,
            "image": self.IMAGE_NAME,
            "metrics_url": self.metrics_url
        }
        
        if container_info:
            status_dict.update({
                "container_status": container_info.get("State", {}).get("Status"),
                "container_created": container_info.get("Created")
            })
        
        return status_dict
    
    async def health_check(self) -> bool:
        """Check if exporter is healthy"""
        if not self.is_running:
            return False
        
        # Check container status
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "inspect", self.CONTAINER_NAME, "--format", "{{.State.Running}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode != 0 or stdout.decode().strip().lower() != "true":
                self.is_running = False
                return False
        except:
            return False
        
        # Check metrics endpoint
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(self.metrics_url)
                return response.status_code == 200 and "node_" in response.text
        except:
            return False
    
    def _get_container_info(self) -> Optional[dict]:
        """Get container information (sync method for status)"""
        try:
            result = subprocess.run(
                ["docker", "inspect", self.CONTAINER_NAME],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                containers = json.loads(result.stdout)
                return containers[0] if containers else None
        except:
            pass
        
        return None
    
    async def remove_container(self) -> bool:
        """Remove the container completely"""
        try:
            if self.is_running:
                await self.stop()
            
            result = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", self.CONTAINER_NAME,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            
            if result.returncode == 0:
                self.container_id = None
                self.logger.info("Docker exporter container removed")
                return True
                
        except Exception as e:
            self.logger.error(f"Error removing container: {e}")
            
        return False
