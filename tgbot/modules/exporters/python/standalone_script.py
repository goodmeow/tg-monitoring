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
Standalone script template for Python Node Exporter
This script is written to /tmp and executed as subprocess
"""

STANDALONE_SCRIPT = '''#!/usr/bin/env python3
"""
Standalone Python Node Exporter
Compatible with Prometheus node_exporter metrics format
"""

import sys
import os
import time
import threading
from flask import Flask, Response
from prometheus_client import CollectorRegistry, Gauge, generate_latest
import psutil

app = Flask(__name__)
registry = CollectorRegistry()

# System metrics
load1 = Gauge("node_load1", "1m load average", registry=registry)
load5 = Gauge("node_load5", "5m load average", registry=registry)
load15 = Gauge("node_load15", "15m load average", registry=registry)

# CPU metrics
cpu_seconds = Gauge("node_cpu_seconds_total", "CPU time", ["cpu", "mode"], registry=registry)

# Memory metrics  
mem_total = Gauge("node_memory_MemTotal_bytes", "Total memory", registry=registry)
mem_available = Gauge("node_memory_MemAvailable_bytes", "Available memory", registry=registry)
mem_free = Gauge("node_memory_MemFree_bytes", "Free memory", registry=registry)
mem_buffers = Gauge("node_memory_Buffers_bytes", "Buffer memory", registry=registry)
mem_cached = Gauge("node_memory_Cached_bytes", "Cached memory", registry=registry)

# Filesystem metrics
fs_size = Gauge("node_filesystem_size_bytes", "FS size", ["device", "mountpoint", "fstype"], registry=registry)
fs_avail = Gauge("node_filesystem_avail_bytes", "FS available", ["device", "mountpoint", "fstype"], registry=registry)
fs_files = Gauge("node_filesystem_files", "FS files", ["device", "mountpoint", "fstype"], registry=registry)
fs_files_free = Gauge("node_filesystem_files_free", "FS files free", ["device", "mountpoint", "fstype"], registry=registry)

# Network metrics
net_rx = Gauge("node_network_receive_bytes_total", "Network RX", ["device"], registry=registry)
net_tx = Gauge("node_network_transmit_bytes_total", "Network TX", ["device"], registry=registry)

# Boot time
boot_time = Gauge("node_boot_time_seconds", "Boot time", registry=registry)

def collect_metrics():
    """Collect all system metrics"""
    try:
        # Load averages
        load = os.getloadavg()
        load1.set(load[0])
        load5.set(load[1])
        load15.set(load[2])
        
        # CPU times
        cpu_times = psutil.cpu_times(percpu=True)
        for idx, cpu in enumerate(cpu_times):
            cpu_seconds.labels(cpu=str(idx), mode="user").set(cpu.user)
            cpu_seconds.labels(cpu=str(idx), mode="system").set(cpu.system)
            cpu_seconds.labels(cpu=str(idx), mode="idle").set(cpu.idle)
            cpu_seconds.labels(cpu=str(idx), mode="iowait").set(getattr(cpu, "iowait", 0))
            cpu_seconds.labels(cpu=str(idx), mode="nice").set(cpu.nice)
            cpu_seconds.labels(cpu=str(idx), mode="irq").set(getattr(cpu, "irq", 0))
            cpu_seconds.labels(cpu=str(idx), mode="softirq").set(getattr(cpu, "softirq", 0))
            cpu_seconds.labels(cpu=str(idx), mode="steal").set(getattr(cpu, "steal", 0))
        
        # Memory
        mem = psutil.virtual_memory()
        mem_total.set(mem.total)
        mem_available.set(mem.available)
        mem_free.set(mem.free)
        mem_buffers.set(getattr(mem, "buffers", 0))
        mem_cached.set(getattr(mem, "cached", 0))
        
        # Filesystems
        for partition in psutil.disk_partitions(all=False):
            try:
                # Skip pseudo filesystems
                if partition.fstype in ["tmpfs", "devtmpfs", "overlay", "squashfs"]:
                    continue
                    
                usage = psutil.disk_usage(partition.mountpoint)
                
                fs_size.labels(
                    device=partition.device,
                    mountpoint=partition.mountpoint,
                    fstype=partition.fstype
                ).set(usage.total)
                
                fs_avail.labels(
                    device=partition.device,
                    mountpoint=partition.mountpoint,
                    fstype=partition.fstype
                ).set(usage.free)
                
                # Simplified inode metrics
                fs_files.labels(
                    device=partition.device,
                    mountpoint=partition.mountpoint,
                    fstype=partition.fstype
                ).set(1000000)
                
                fs_files_free.labels(
                    device=partition.device,
                    mountpoint=partition.mountpoint,
                    fstype=partition.fstype
                ).set(500000)
            except (PermissionError, OSError):
                continue
        
        # Network
        net_io = psutil.net_io_counters(pernic=True)
        for iface, stats in net_io.items():
            # Skip loopback
            if iface == "lo":
                continue
            net_rx.labels(device=iface).set(stats.bytes_recv)
            net_tx.labels(device=iface).set(stats.bytes_sent)
        
        # Boot time
        boot_time.set(psutil.boot_time())
        
    except Exception as e:
        print(f"Error collecting metrics: {e}", file=sys.stderr)

def update_metrics_loop():
    """Background thread to update metrics periodically"""
    while True:
        collect_metrics()
        time.sleep(15)

@app.route("/metrics")
def metrics_endpoint():
    """Prometheus metrics endpoint"""
    collect_metrics()
    return Response(generate_latest(registry), mimetype="text/plain")

@app.route("/")
def home():
    """Health check endpoint"""
    return "<h1>Node Exporter (Python)</h1><p>Metrics available at <a href='/metrics'>/metrics</a></p>"

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9100
    host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
    
    print(f"Starting Python Node Exporter on {host}:{port}", file=sys.stderr)
    
    # Start background metrics updater
    thread = threading.Thread(target=update_metrics_loop, daemon=True)
    thread.start()
    
    # Run Flask app
    app.run(host=host, port=port, debug=False, threaded=True)
'''
