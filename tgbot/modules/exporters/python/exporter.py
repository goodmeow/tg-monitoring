"""
Python-based Node Exporter implementation
100% compatible drop-in replacement for Docker node_exporter
"""

import asyncio
import os
import time
import subprocess
import signal
from typing import Dict, Any, Optional
from pathlib import Path

from ..base import ExporterBase, ExporterType


class PythonExporter(ExporterBase):
    """Native Python implementation of Node Exporter"""
    
    def __init__(self, port: int = 9100, host: str = "0.0.0.0"):
        super().__init__(port, host)
        self._process: Optional[subprocess.Popen] = None
        self._script_path = Path("/tmp/node_exporter_python.py")
        
    @property
    def exporter_type(self) -> ExporterType:
        return ExporterType.PYTHON
        
    async def start(self) -> bool:
        """Start the Python exporter as subprocess"""
        if self.is_running:
            self.logger.warning("Python exporter already running")
            return True
        
        try:
            # Create standalone script
            self._create_standalone_script()
            
            # Start as subprocess
            self._process = subprocess.Popen(
                ["python3", str(self._script_path), str(self.port), self.host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for startup
            await asyncio.sleep(2)
            
            if self._process.poll() is None:
                self.is_running = True
                self.logger.info(f"Python exporter started on {self.host}:{self.port} (PID: {self._process.pid})")
                return True
            else:
                stderr = self._process.stderr.read().decode() if self._process.stderr else ""
                self.logger.error(f"Failed to start Python exporter: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting Python exporter: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the Python exporter"""
        if not self.is_running:
            return True
        
        try:
            if self._process:
                # Send SIGTERM to process group
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if not stopped
                    os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                    self._process.wait(timeout=2)
                
            self.is_running = False
            self.logger.info("Python exporter stopped")
            
            # Cleanup script file
            if self._script_path.exists():
                self._script_path.unlink()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping Python exporter: {e}")
            # Force cleanup
            if self._process:
                try:
                    os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                except:
                    pass
            self.is_running = False
            return False
    
    def status(self) -> Dict[str, Any]:
        """Get exporter status"""
        return {
            "type": self.exporter_type.value,
            "running": self.is_running,
            "port": self.port,
            "host": self.host,
            "pid": self._process.pid if self._process else None,
            "metrics_url": self.metrics_url,
            "process_alive": self._process.poll() is None if self._process else False
        }
    
    async def health_check(self) -> bool:
        """Check if exporter is healthy"""
        if not self.is_running or not self._process:
            return False
        
        # Check if process is still alive
        if self._process.poll() is not None:
            self.is_running = False
            return False
        
        # Check metrics endpoint
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(self.metrics_url)
                return response.status_code == 200 and "node_" in response.text
        except:
            return False
    
    def _create_standalone_script(self):
        """Create standalone exporter script"""
        from .standalone_script import STANDALONE_SCRIPT
        self._script_path.write_text(STANDALONE_SCRIPT)
        self._script_path.chmod(0o755)
