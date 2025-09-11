from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.request import Request, urlopen


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


_METRIC_LINE_RE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{(?P<labels>[^}]*)\})?\s+(?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?|NaN|nan|Inf|-Inf)\s*$"
)
_LABEL_KV_RE = re.compile(r"\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\"([^\"]*)\"\s*")


def _parse_labels(s: str) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    if not s:
        return labels
    # Iterate over key="value" pairs; Prometheus escaping not fully handled, but safe for node_exporter
    idx = 0
    while idx < len(s):
        m = _LABEL_KV_RE.match(s, idx)
        if not m:
            break
        key, val = m.group(1), m.group(2)
        labels[key] = val
        # advance past this pair
        idx = m.end()
        if idx < len(s) and s[idx] == ',':
            idx += 1
    return labels


def fetch_metrics_text(url: str, timeout_sec: int) -> str:
    req = Request(url, headers={"User-Agent": "tg-monitor/1.0"})
    with urlopen(req, timeout=timeout_sec) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def parse_node_exporter_metrics(text: str) -> NodeStats:
    ts = time.time()
    cores: Set[str] = set()
    load5: Optional[float] = None
    mem_total: Optional[int] = None
    mem_avail: Optional[int] = None

    fs_map: Dict[Tuple[str, str, str], FileSystem] = {}

    for line in text.splitlines():
        if not line or line.startswith('#'):
            continue
        m = _METRIC_LINE_RE.match(line)
        if not m:
            continue
        name = m.group('name')
        labels_raw = m.group('labels') or ''
        labels = _parse_labels(labels_raw)
        v_raw = m.group('value')
        if v_raw.lower() in {"nan", "inf", "+inf", "-inf"}:
            # skip non-finite
            continue
        try:
            value = float(v_raw)
        except Exception:
            continue

        if name == 'node_load5':
            load5 = value
            continue

        if name == 'node_cpu_seconds_total':
            cpu = labels.get('cpu')
            if cpu is not None:
                cores.add(cpu)
            continue

        if name == 'node_memory_MemTotal_bytes':
            mem_total = int(value)
            continue
        if name == 'node_memory_MemAvailable_bytes':
            mem_avail = int(value)
            continue

        # filesystem metrics
        if name in (
            'node_filesystem_size_bytes',
            'node_filesystem_avail_bytes',
            'node_filesystem_files',
            'node_filesystem_files_free',
        ):
            device = labels.get('device') or ''
            mountpoint = labels.get('mountpoint') or ''
            fstype = labels.get('fstype') or ''
            key = (device, mountpoint, fstype)
            fs = fs_map.get(key)
            if fs is None:
                fs = FileSystem(device=device, mountpoint=mountpoint, fstype=fstype)
                fs_map[key] = fs
            if name == 'node_filesystem_size_bytes':
                fs.size_bytes = int(value)
            elif name == 'node_filesystem_avail_bytes':
                fs.avail_bytes = int(value)
            elif name == 'node_filesystem_files':
                fs.files_total = int(value)
            elif name == 'node_filesystem_files_free':
                fs.files_free = int(value)
            continue

    return NodeStats(
        timestamp=ts,
        cores=len(cores) if cores else 0,
        load5=load5,
        mem_total_bytes=mem_total,
        mem_available_bytes=mem_avail,
        filesystems=list(fs_map.values()),
    )

