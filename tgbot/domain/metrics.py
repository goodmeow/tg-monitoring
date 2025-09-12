from __future__ import annotations

from dataclasses import dataclass
from typing import List
import httpx


@dataclass
class FileSystem:
    mount: str
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
    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        text = resp.text

    # Very lightweight parsing; assumes Node Exporter exposition format
    import time

    cpu_load_per_core = 0.0
    mem_total = 0.0
    mem_available = 0.0
    disks: List[FileSystem] = []
    inode_free_pct_map: dict[str, float] = {}

    for line in text.splitlines():
        if line.startswith("#"):
            continue
        if line.startswith("node_load1 "):
            try:
                load1 = float(line.split()[1])
                # assuming average over all cores ~ load1/cores; we don't have cores, keep as is
                cpu_load_per_core = load1  # heuristic
            except Exception:
                pass
        elif line.startswith("node_memory_MemTotal_bytes"):
            try:
                mem_total = float(line.split()[-1])
            except Exception:
                pass
        elif line.startswith("node_memory_MemAvailable_bytes"):
            try:
                mem_available = float(line.split()[-1])
            except Exception:
                pass
        elif line.startswith("node_filesystem_size_bytes"):
            # node_filesystem_size_bytes{mountpoint="/",fstype="ext4",...} 1.23e+11
            try:
                before, val = line.rsplit(" ", 1)
                size = float(val)
                mount = "/"
                if 'mountpoint="' in before:
                    mount = before.split('mountpoint="', 1)[1].split('"', 1)[0]
                disks.append(FileSystem(mount=mount, size_bytes=size, avail_bytes=0.0))
            except Exception:
                pass
        elif line.startswith("node_filesystem_avail_bytes"):
            try:
                before, val = line.rsplit(" ", 1)
                avail = float(val)
                mount = "/"
                if 'mountpoint="' in before:
                    mount = before.split('mountpoint="', 1)[1].split('"', 1)[0]
                for d in disks:
                    if d.mount == mount:
                        d.avail_bytes = avail
                        break
            except Exception:
                pass
        elif line.startswith("node_filesystem_files_free"):
            # approximate inode free percentage later
            try:
                before, val = line.rsplit(" ", 1)
                free = float(val)
                mount = "/"
                if 'mountpoint="' in before:
                    mount = before.split('mountpoint="', 1)[1].split('"', 1)[0]
                inode_free_pct_map.setdefault(mount, free)
            except Exception:
                pass

    mem_available_pct = (mem_available / mem_total) if mem_total > 0 else 0.0
    ts = time.time()
    return NodeStats(cpu_load_per_core=cpu_load_per_core, mem_available_pct=mem_available_pct, disks=disks, timestamp=ts)

