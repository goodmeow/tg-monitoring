from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .metrics import NodeStats, FileSystem


@dataclass
class Thresholds:
    cpu_load_per_core_warn: float
    mem_available_pct_warn: float
    disk_usage_pct_warn: float
    enable_inodes: bool
    inode_free_pct_warn: float
    exclude_fs_types: list[str]


def _fmt_pct(x: float) -> str:
    return f"{x*100:.0f}%"


def evaluate(stats: NodeStats, t: Thresholds) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}

    def is_excluded(fs: FileSystem) -> bool:
        # Simple filter based on mount or fstype (fstype not currently parsed)
        excluded = set(t.exclude_fs_types or [])
        if fs.mount in {"/proc", "/sys", "/dev", "/run"}:
            return True
        return False

    # CPU
    cpu = stats.cpu_load_per_core
    out["cpu"] = {
        "type": "cpu",
        "status": "alert" if cpu >= t.cpu_load_per_core_warn else "ok",
        "value": cpu,
        "message": f"Load1 per core: {_fmt_pct(cpu)} (warn {_fmt_pct(t.cpu_load_per_core_warn)})",
        "meta": {},
    }

    # Memory
    mem_avail = stats.mem_available_pct
    out["mem"] = {
        "type": "mem",
        "status": "alert" if mem_avail <= t.mem_available_pct_warn else "ok",
        "value": mem_avail,
        "message": f"Mem available: {_fmt_pct(mem_avail)} (warn <= {_fmt_pct(t.mem_available_pct_warn)})",
        "meta": {
            "available_bytes": None,
            "total_bytes": None,
        },
    }

    # Disk
    alerts = []
    for fs in stats.disks:
        if is_excluded(fs):
            continue
        used_fraction = 1.0 - (fs.avail_bytes / fs.size_bytes) if fs.size_bytes > 0 else 0.0
        if used_fraction >= t.disk_usage_pct_warn:
            alerts.append(f"{fs.mount} used {_fmt_pct(used_fraction)} (warn {_fmt_pct(t.disk_usage_pct_warn)})")
    out["disk"] = {
        "type": "disk",
        "status": "alert" if alerts else "ok",
        "value": 1.0 if alerts else 0.0,
        "message": "\n".join(alerts) or "OK",
        "meta": {},
    }

    # Inodes (optional)
    out["inode"] = {
        "type": "inode",
        "status": "ok",
        "value": 0.0,
        "message": "disabled" if not t.enable_inodes else "not implemented",
        "meta": {},
    }

    return out
