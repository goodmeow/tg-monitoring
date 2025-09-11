from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import httpx
from prometheus_client.parser import text_string_to_metric_families


@dataclass
class FileSystem:
    device: str
    mountpoint: str
    fstype: str
    size_bytes: Optional[int] = None
    avail_bytes: Optional[int] = None
    files_total: Optional[int] = None
    files_free: Optional[int] = None


@dataclass
class NodeStats:
    timestamp: float
    cores: int
    load5: Optional[float]
    mem_total_bytes: Optional[int]
    mem_available_bytes: Optional[int]
    filesystems: List[FileSystem]


async def fetch_node_stats(url: str, timeout_sec: int) -> NodeStats:
    ts = time.time()
    async with httpx.AsyncClient(timeout=timeout_sec, headers={"User-Agent": "tg-monitor/1.0"}) as client:
        r = await client.get(url)
        r.raise_for_status()
        text = r.text

    cores: Set[str] = set()
    load5: Optional[float] = None
    mem_total: Optional[int] = None
    mem_avail: Optional[int] = None
    fs_map: Dict[Tuple[str, str, str], FileSystem] = {}

    for family in text_string_to_metric_families(text):
        name = family.name
        if name == "node_load5":
            for sample in family.samples:
                try:
                    load5 = float(sample.value)
                except Exception:
                    pass
        elif name == "node_cpu_seconds_total":
            for sample in family.samples:
                cpu = sample.labels.get("cpu") if sample.labels else None
                if cpu is not None:
                    cores.add(cpu)
        elif name == "node_memory_MemTotal_bytes":
            for sample in family.samples:
                try:
                    mem_total = int(float(sample.value))
                except Exception:
                    pass
        elif name == "node_memory_MemAvailable_bytes":
            for sample in family.samples:
                try:
                    mem_avail = int(float(sample.value))
                except Exception:
                    pass
        elif name in (
            "node_filesystem_size_bytes",
            "node_filesystem_avail_bytes",
            "node_filesystem_files",
            "node_filesystem_files_free",
        ):
            for sample in family.samples:
                labels = sample.labels or {}
                device = labels.get("device", "")
                mountpoint = labels.get("mountpoint", "")
                fstype = labels.get("fstype", "")
                key = (device, mountpoint, fstype)
                fs = fs_map.get(key)
                if fs is None:
                    fs = FileSystem(device=device, mountpoint=mountpoint, fstype=fstype)
                    fs_map[key] = fs
                try:
                    val = int(float(sample.value))
                except Exception:
                    continue
                if name == "node_filesystem_size_bytes":
                    fs.size_bytes = val
                elif name == "node_filesystem_avail_bytes":
                    fs.avail_bytes = val
                elif name == "node_filesystem_files":
                    fs.files_total = val
                elif name == "node_filesystem_files_free":
                    fs.files_free = val

    return NodeStats(
        timestamp=ts,
        cores=len(cores) if cores else 0,
        load5=load5,
        mem_total_bytes=mem_total,
        mem_available_bytes=mem_avail,
        filesystems=list(fs_map.values()),
    )
