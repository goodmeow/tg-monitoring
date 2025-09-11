from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .metrics import FileSystem, NodeStats


@dataclass
class Thresholds:
    cpu_load_per_core_warn: float
    mem_available_pct_warn: float
    disk_usage_pct_warn: float
    enable_inodes: bool
    inode_free_pct_warn: float
    exclude_fs_types: List[str]


def _fmt_pct(x: float) -> str:
    return f"{x*100:.1f}%"


def evaluate(stats: NodeStats, t: Thresholds) -> Dict[str, Dict]:
    """
    Produce current check statuses keyed by check id.
    Each value contains: status ('ok'|'alert'), value (float), message (str), meta (dict).
    """
    results: Dict[str, Dict] = {}

    # CPU
    if stats.cores and stats.load5 is not None and stats.cores > 0:
        per_core = stats.load5 / max(1, stats.cores)
        status = 'alert' if per_core > t.cpu_load_per_core_warn else 'ok'
        msg = f"CPU load5/core: {_fmt_pct(per_core)} (load5={stats.load5:.2f}, cores={stats.cores})"
        results['cpu'] = {
            'status': status,
            'value': per_core,
            'message': msg,
            'meta': {'load5': stats.load5, 'cores': stats.cores},
        }

    # Memory
    if stats.mem_total_bytes and stats.mem_total_bytes > 0 and stats.mem_available_bytes is not None:
        avail_pct = stats.mem_available_bytes / stats.mem_total_bytes
        status = 'alert' if avail_pct < t.mem_available_pct_warn else 'ok'
        msg = (
            f"Mem available: {_fmt_pct(avail_pct)} "
            f"({stats.mem_available_bytes/1024**3:.2f} GiB of {stats.mem_total_bytes/1024**3:.2f} GiB)"
        )
        results['mem'] = {
            'status': status,
            'value': avail_pct,
            'message': msg,
            'meta': {
                'available_bytes': stats.mem_available_bytes,
                'total_bytes': stats.mem_total_bytes,
            },
        }

    # Filesystems
    def is_excluded(fs: FileSystem) -> bool:
        return (fs.fstype in t.exclude_fs_types) or (not fs.mountpoint) or fs.mountpoint.startswith('/proc') or fs.mountpoint.startswith('/sys') or fs.mountpoint.startswith('/run')

    for fs in stats.filesystems:
        if is_excluded(fs):
            continue
        if fs.size_bytes and fs.size_bytes > 0 and fs.avail_bytes is not None:
            used_pct = 1.0 - (fs.avail_bytes / fs.size_bytes)
            status = 'alert' if used_pct > t.disk_usage_pct_warn else 'ok'
            cid = f"disk:{fs.mountpoint}"
            msg = (
                f"Disk {fs.mountpoint}: {_fmt_pct(used_pct)} used "
                f"({(fs.size_bytes - fs.avail_bytes)/1024**3:.2f}/{fs.size_bytes/1024**3:.2f} GiB)"
            )
            results[cid] = {
                'status': status,
                'value': used_pct,
                'message': msg,
                'meta': {
                    'mountpoint': fs.mountpoint,
                    'fstype': fs.fstype,
                    'device': fs.device,
                    'size_bytes': fs.size_bytes,
                    'avail_bytes': fs.avail_bytes,
                },
            }

        if t.enable_inodes and fs.files_total and fs.files_total > 0 and fs.files_free is not None:
            free_pct = fs.files_free / fs.files_total
            status = 'alert' if free_pct < t.inode_free_pct_warn else 'ok'
            cid = f"inode:{fs.mountpoint}"
            msg = f"Inodes {fs.mountpoint}: {_fmt_pct(free_pct)} free ({fs.files_free}/{fs.files_total})"
            results[cid] = {
                'status': status,
                'value': free_pct,
                'message': msg,
                'meta': {
                    'mountpoint': fs.mountpoint,
                    'fstype': fs.fstype,
                    'device': fs.device,
                    'files_total': fs.files_total,
                    'files_free': fs.files_free,
                },
            }

    return results

