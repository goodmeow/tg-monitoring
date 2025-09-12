from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

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
        # Filter by fstype and known ephemeral mounts
        excluded = set(t.exclude_fs_types or [])
        try:
            if getattr(fs, "fstype", "") in excluded:
                return True
        except Exception:
            pass
        m = fs.mount or ""
        if m in {"/proc", "/sys", "/dev", "/run"}:
            return True
        if m.startswith("/run/") or m.startswith("/proc/") or m.startswith("/sys/") or m.startswith("/dev/"):
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
    alerts: List[str] = []
    disk_meta: Dict[str, List[Dict]] = {"by_mount": []}
    for fs in stats.disks:
        if is_excluded(fs):
            continue
        used_fraction = 1.0 - (fs.avail_bytes / fs.size_bytes) if fs.size_bytes > 0 else 0.0
        # Always include bar data for visibility
        disk_meta["by_mount"].append({"mount": fs.mount, "value": used_fraction})
        if used_fraction >= t.disk_usage_pct_warn:
            alerts.append(f"{fs.mount} used {_fmt_pct(used_fraction)} (warn {_fmt_pct(t.disk_usage_pct_warn)})")
            disk_meta["by_mount"].append({"mount": fs.mount, "value": used_fraction})
    out["disk"] = {
        "type": "disk",
        "status": "alert" if alerts else "ok",
        "value": 1.0 if alerts else 0.0,
        "message": "\n".join(alerts) or "OK",
        "meta": disk_meta,
    }

    # Inodes (optional)
    inode_meta: Dict[str, List[Dict]] = {"by_mount": []}
    inode_alerts: List[str] = []
    inode_status = "ok"
    inode_value = 0.0
    if t.enable_inodes:
        for fs in stats.disks:
            if is_excluded(fs):
                continue
            if fs.inode_free_pct is None:
                continue
            free = fs.inode_free_pct
            # Always include bar data
            inode_meta["by_mount"].append({"mount": fs.mount, "value": free})
            if free <= t.inode_free_pct_warn:
                inode_alerts.append(
                    f"{fs.mount} free {_fmt_pct(free)} (warn <= {_fmt_pct(t.inode_free_pct_warn)})"
                )
        if inode_alerts:
            inode_status = "alert"
            inode_value = 1.0
        inode_msg = "\n".join(inode_alerts) or "OK"
    else:
        inode_msg = "disabled"
    out["inode"] = {
        "type": "inode",
        "status": inode_status,
        "value": inode_value,
        "message": inode_msg,
        "meta": inode_meta,
    }

    return out
