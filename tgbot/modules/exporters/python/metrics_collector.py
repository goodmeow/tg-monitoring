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
Metrics collector utilities for Python exporter
"""

import os
import psutil
from typing import Dict, List, Any


class MetricsCollector:
    """Collects system metrics in Prometheus format"""
    
    @staticmethod
    def get_load_averages() -> Dict[str, float]:
        """Get system load averages"""
        load = os.getloadavg()
        return {
            "load1": load[0],
            "load5": load[1],
            "load15": load[2]
        }
    
    @staticmethod
    def get_cpu_metrics() -> List[Dict[str, Any]]:
        """Get CPU metrics per core"""
        metrics = []
        cpu_times = psutil.cpu_times(percpu=True)
        
        for idx, cpu in enumerate(cpu_times):
            metrics.append({
                "cpu": str(idx),
                "user": cpu.user,
                "system": cpu.system,
                "idle": cpu.idle,
                "iowait": getattr(cpu, "iowait", 0),
                "nice": cpu.nice,
                "irq": getattr(cpu, "irq", 0),
                "softirq": getattr(cpu, "softirq", 0),
                "steal": getattr(cpu, "steal", 0)
            })
        
        return metrics
    
    @staticmethod
    def get_memory_metrics() -> Dict[str, int]:
        """Get memory metrics in bytes"""
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "free": mem.free,
            "buffers": getattr(mem, "buffers", 0),
            "cached": getattr(mem, "cached", 0),
            "used": mem.used,
            "percent": mem.percent
        }
    
    @staticmethod
    def get_filesystem_metrics() -> List[Dict[str, Any]]:
        """Get filesystem metrics"""
        metrics = []
        
        for partition in psutil.disk_partitions(all=False):
            # Skip pseudo filesystems
            if partition.fstype in ["tmpfs", "devtmpfs", "overlay", "squashfs"]:
                continue
            
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                metrics.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "size_bytes": usage.total,
                    "avail_bytes": usage.free,
                    "used_bytes": usage.used,
                    "percent": usage.percent
                })
            except (PermissionError, OSError):
                continue
        
        return metrics
    
    @staticmethod
    def get_network_metrics() -> Dict[str, Dict[str, int]]:
        """Get network interface metrics"""
        metrics = {}
        net_io = psutil.net_io_counters(pernic=True)
        
        for iface, stats in net_io.items():
            # Skip loopback
            if iface == "lo":
                continue
            
            metrics[iface] = {
                "rx_bytes": stats.bytes_recv,
                "tx_bytes": stats.bytes_sent,
                "rx_packets": stats.packets_recv,
                "tx_packets": stats.packets_sent,
                "rx_errors": stats.errin,
                "tx_errors": stats.errout,
                "rx_dropped": stats.dropin,
                "tx_dropped": stats.dropout
            }
        
        return metrics
    
    @staticmethod
    def get_boot_time() -> float:
        """Get system boot time as timestamp"""
        return psutil.boot_time()
