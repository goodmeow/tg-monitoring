from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import httpx
from prometheus_client.parser import text_string_to_metric_families


@dataclass
class FileSystem:
    mount: str
    fstype: str
    size_bytes: float
    avail_bytes: float
    inode_free_pct: float | None = None


@dataclass
class NodeStats:
    cpu_load_per_core: float
    mem_available_pct: float
    disks: List[FileSystem]
    timestamp: float


async def fetch_node_stats(url: str, timeout_sec: int) -> NodeStats:
    async with httpx.AsyncClient(timeout=timeout_sec, headers={"User-Agent": "tg-monitor/1.0"}) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        text = resp.text

    import time

    cores: set[str] = set()
    load1: Optional[float] = None
    mem_total: Optional[float] = None
    mem_available: Optional[float] = None

    fs_map: Dict[Tuple[str, str], FileSystem] = {}
    inode_totals: Dict[str, float] = {}
    inode_free: Dict[str, float] = {}

    for family in text_string_to_metric_families(text):
        name = family.name
        if name == "node_cpu_seconds_total":
            for s in family.samples:
                cpu = s.labels.get("cpu") if s.labels else None
                if cpu is not None:
                    cores.add(cpu)
        elif name == "node_load1":
            for s in family.samples:
                try:
                    load1 = float(s.value)
                except Exception:
                    pass
        elif name == "node_memory_MemTotal_bytes":
            for s in family.samples:
                try:
                    mem_total = float(s.value)
                except Exception:
                    pass
        elif name == "node_memory_MemAvailable_bytes":
            for s in family.samples:
                try:
                    mem_available = float(s.value)
                except Exception:
                    pass
        elif name in (
            "node_filesystem_size_bytes",
            "node_filesystem_avail_bytes",
            "node_filesystem_files",
            "node_filesystem_files_free",
        ):
            for s in family.samples:
                labels = s.labels or {}
                mount = labels.get("mountpoint", "")
                fstype = labels.get("fstype", "")
                key = (mount, fstype)
                fs = fs_map.get(key)
                if fs is None:
                    fs = FileSystem(mount=mount or "/", fstype=fstype or "", size_bytes=0.0, avail_bytes=0.0)
                    fs_map[key] = fs
                try:
                    val = float(s.value)
                except Exception:
                    continue
                if name == "node_filesystem_size_bytes":
                    fs.size_bytes = val
                elif name == "node_filesystem_avail_bytes":
                    fs.avail_bytes = val
                elif name == "node_filesystem_files":
                    inode_totals[fs.mount] = val
                elif name == "node_filesystem_files_free":
                    inode_free[fs.mount] = val

    # Compute inode free pct per mount where possible
    for m, tot in inode_totals.items():
        free = inode_free.get(m)
        if free is None or tot <= 0:
            continue
        for fs in fs_map.values():
            if fs.mount == m:
                try:
                    fs.inode_free_pct = max(0.0, min(1.0, float(free) / float(tot)))
                except Exception:
                    fs.inode_free_pct = None
                break

    cpu_load_per_core = 0.0
    if load1 is not None:
        try:
            c = max(1, len(cores) or 1)
            cpu_load_per_core = float(load1) / c
        except Exception:
            cpu_load_per_core = float(load1)

    mem_available_pct = 0.0
    if mem_total and mem_total > 0 and mem_available is not None:
        mem_available_pct = float(mem_available) / float(mem_total)

    ts = time.time()
    return NodeStats(
        cpu_load_per_core=cpu_load_per_core,
        mem_available_pct=mem_available_pct,
        disks=list(fs_map.values()),
        timestamp=ts,
    )
