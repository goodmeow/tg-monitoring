"""
Node Exporter Module
Provides flexible node metrics collection via Docker or Native Python

Usage:
    from tgbot.modules.exporters import create_exporter, ExporterType
    
    # Auto-select best available
    exporter = create_exporter()
    
    # Or specify type
    exporter = create_exporter(ExporterType.PYTHON)
    exporter = create_exporter(ExporterType.DOCKER)
    
    # Start exporter
    await exporter.start()
    
    # Check status
    status = exporter.status()
    
    # Stop when done
    await exporter.stop()
"""

from .base import ExporterBase, ExporterType
from .factory import (
    create_exporter, 
    get_current_exporter, 
    switch_exporter,
    get_available_exporters,
    get_exporter_config
)

__all__ = [
    "ExporterBase",
    "ExporterType", 
    "create_exporter",
    "get_current_exporter",
    "switch_exporter",
    "get_available_exporters",
    "get_exporter_config"
]
