"""
Factory for creating and managing exporters
"""

import os
import subprocess
from typing import Optional, Dict, Any
from .base import ExporterBase, ExporterType
from .python import PythonExporter
from .docker import DockerExporter

# Global instance holder
_current_exporter: Optional[ExporterBase] = None


def create_exporter(
    exporter_type: Optional[ExporterType] = None,
    port: int = 9100,
    host: str = "0.0.0.0"
) -> ExporterBase:
    """
    Create an exporter instance based on type or environment
    
    Args:
        exporter_type: Type of exporter (ExporterType.DOCKER or ExporterType.PYTHON)
        port: Port to expose metrics (default: 9100)
        host: Host to bind (default: 0.0.0.0)
    
    Returns:
        ExporterBase instance
    """
    global _current_exporter
    
    # Get type from env if not provided
    if exporter_type is None:
        env_type = os.environ.get("NODE_EXPORTER_TYPE", "").lower()
        if env_type == "python":
            exporter_type = ExporterType.PYTHON
        elif env_type == "docker":
            exporter_type = ExporterType.DOCKER
        else:
            # Auto-detect best option
            exporter_type = _auto_select_type()
    
    # Create exporter based on type
    if exporter_type == ExporterType.DOCKER:
        _current_exporter = DockerExporter(port=port, host=host)
    elif exporter_type == ExporterType.PYTHON:
        _current_exporter = PythonExporter(port=port, host=host)
    else:
        raise ValueError(f"Unknown exporter type: {exporter_type}")
    
    return _current_exporter


def get_current_exporter() -> Optional[ExporterBase]:
    """Get the currently active exporter instance"""
    return _current_exporter


async def switch_exporter(
    new_type: ExporterType,
    port: int = 9100,
    host: str = "0.0.0.0"
) -> ExporterBase:
    """
    Switch to a different exporter type
    
    Args:
        new_type: New exporter type to switch to
        port: Port for the new exporter
        host: Host for the new exporter
    
    Returns:
        New ExporterBase instance
    """
    global _current_exporter
    
    # Stop current exporter if exists
    if _current_exporter and _current_exporter.is_running:
        await _current_exporter.stop()
    
    # Create new exporter
    _current_exporter = create_exporter(new_type, port, host)
    
    # Start new exporter
    await _current_exporter.start()
    
    return _current_exporter


def get_available_exporters() -> Dict[str, bool]:
    """
    Check which exporters are available on the system
    
    Returns:
        Dict with availability status for each exporter type
    """
    availability = {}
    
    # Check Docker availability
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            timeout=5
        )
        availability["docker"] = result.returncode == 0
    except:
        availability["docker"] = False
    
    # Check Python dependencies
    try:
        import psutil
        import flask
        import prometheus_client
        availability["python"] = True
    except ImportError:
        availability["python"] = False
    
    return availability


def _auto_select_type() -> ExporterType:
    """
    Automatically select the best available exporter type
    
    Priority:
    1. If Docker container already running - use Docker
    2. If Docker available - use Docker
    3. If Python dependencies available - use Python
    4. Raise error if nothing available
    """
    # Check if Docker container already running
    try:
        result = subprocess.run(
            ["docker", "inspect", "node-exporter", "--format", "{{.State.Running}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip().lower() == "true":
            return ExporterType.DOCKER
    except:
        pass
    
    # Check availability
    available = get_available_exporters()
    
    # Prefer Docker if available
    if available.get("docker", False):
        return ExporterType.DOCKER
    
    # Fall back to Python
    if available.get("python", False):
        return ExporterType.PYTHON
    
    # Nothing available
    raise RuntimeError(
        "No exporter available! "
        "Install Docker or Python dependencies (prometheus-client, psutil, flask)"
    )


def get_exporter_config() -> Dict[str, Any]:
    """
    Get current exporter configuration
    
    Returns:
        Configuration dictionary
    """
    config = {
        "available": get_available_exporters(),
        "current": None,
        "env_type": os.environ.get("NODE_EXPORTER_TYPE", "auto")
    }
    
    if _current_exporter:
        config["current"] = {
            "type": _current_exporter.exporter_type.value,
            "status": _current_exporter.status()
        }
    
    return config
