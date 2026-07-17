from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

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

    builder = _NodeStatsBuilder()

    for family in text_string_to_metric_families(text):
        _process_family(family, builder)

    return builder.build(timestamp=ts)


class _NodeStatsBuilder:
    def __init__(self) -> None:
        self.cores: Set[str] = set()
        self.load5: Optional[float] = None
        self.mem_total: Optional[int] = None
        self.mem_avail: Optional[int] = None
        self._fs_map: Dict[Tuple[str, str, str], FileSystem] = {}

    def build(self, *, timestamp: float) -> NodeStats:
        return NodeStats(
            timestamp=timestamp,
            cores=len(self.cores) if self.cores else 0,
            load5=self.load5,
            mem_total_bytes=self.mem_total,
            mem_available_bytes=self.mem_avail,
            filesystems=list(self._fs_map.values()),
        )

    def filesystem_for(self, labels: Optional[Dict[str, str]]) -> FileSystem:
        labels = labels or {}
        key = (
            labels.get("device", ""),
            labels.get("mountpoint", ""),
            labels.get("fstype", ""),
        )
        fs = self._fs_map.get(key)
        if fs is None:
            fs = FileSystem(device=key[0], mountpoint=key[1], fstype=key[2])
            self._fs_map[key] = fs
        return fs


def _process_family(family, builder: _NodeStatsBuilder) -> None:
    handler = _FAMILY_HANDLERS.get(family.name)
    if handler is not None:
        handler(family, builder)
        return

    fs_attr = _FILESYSTEM_ATTRS.get(family.name)
    if fs_attr is not None:
        _apply_filesystem_metric(family.samples, builder, fs_attr)


def _handle_load5(family, builder: _NodeStatsBuilder) -> None:
    value = _last_valid_float(sample.value for sample in family.samples)
    if value is not None:
        builder.load5 = value


def _handle_cpu_seconds_total(family, builder: _NodeStatsBuilder) -> None:
    for sample in family.samples:
        labels = sample.labels or {}
        cpu = labels.get("cpu")
        if cpu is not None:
            builder.cores.add(cpu)


def _handle_mem_total(family, builder: _NodeStatsBuilder) -> None:
    value = _last_valid_int(sample.value for sample in family.samples)
    if value is not None:
        builder.mem_total = value


def _handle_mem_available(family, builder: _NodeStatsBuilder) -> None:
    value = _last_valid_int(sample.value for sample in family.samples)
    if value is not None:
        builder.mem_avail = value


def _apply_filesystem_metric(samples, builder: _NodeStatsBuilder, attr: str) -> None:
    for sample in samples:
        value = _safe_int(sample.value)
        if value is None:
            continue
        fs = builder.filesystem_for(sample.labels)
        setattr(fs, attr, value)


def _last_valid_float(values: Iterable[object]) -> Optional[float]:
    result: Optional[float] = None
    for value in values:
        converted = _safe_float(value)
        if converted is not None:
            result = converted
    return result


def _last_valid_int(values: Iterable[object]) -> Optional[int]:
    result: Optional[int] = None
    for value in values:
        converted = _safe_int(value)
        if converted is not None:
            result = converted
    return result


def _safe_float(value: object) -> Optional[float]:
    try:
        return float(value)
    except Exception:  # noqa: BLE001 - maintain legacy tolerance
        return None


def _safe_int(value: object) -> Optional[int]:
    float_value = _safe_float(value)
    if float_value is None:
        return None
    try:
        return int(float_value)
    except Exception:  # noqa: BLE001 - maintain legacy tolerance
        return None


_FAMILY_HANDLERS = {
    "node_load5": _handle_load5,
    "node_cpu_seconds_total": _handle_cpu_seconds_total,
    "node_memory_MemTotal_bytes": _handle_mem_total,
    "node_memory_MemAvailable_bytes": _handle_mem_available,
}


_FILESYSTEM_ATTRS = {
    "node_filesystem_size_bytes": "size_bytes",
    "node_filesystem_avail_bytes": "avail_bytes",
    "node_filesystem_files": "files_total",
    "node_filesystem_files_free": "files_free",
}
