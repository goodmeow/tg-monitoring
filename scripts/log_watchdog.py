#!/usr/bin/env python3
"""Log watchdog for tg-monitoring.

Checks the tg-monitoring log for the most recent handled update and
alerts via Telegram if no handled updates are seen within a threshold.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib import parse, request


UPDATE_RE = re.compile(r"Update id=\d+ is handled")
RESPONSE_RE = re.compile(r"response_sent")
HEARTBEAT_RE = re.compile(r"Bot heartbeat: running")
TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})")


def _env_get(name: str) -> str | None:
    """Return environment variable value, checking lowercase fallback."""
    return os.environ.get(name) or os.environ.get(name.lower())


def _env_bool(name: str, default: bool = False) -> bool:
    """Return environment variable parsed as boolean."""
    val = _env_get(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    """Return environment variable parsed as int."""
    val = _env_get(name)
    if val is None:
        return default
    try:
        return int(val)
    except Exception:
        return default


def _host_display_name() -> str:
    """Return configured host label or OS hostname for watchdog alerts."""
    return _env_get("HOST_DISPLAY_NAME") or os.uname().nodename


@dataclass
class WatchdogConfig:
    """Configuration for watchdog execution."""
    log_path: Path
    state_path: Path
    idle_min: int
    cooldown_min: int
    restart_cooldown_min: int
    max_bytes: int
    response_re: re.Pattern
    request_re: re.Pattern
    heartbeat_re: re.Pattern
    require_requests: bool
    require_heartbeat: bool
    restart_on_idle: bool
    restart_cmd: str
    restart_timeout_sec: int
    token: str
    chat_id: str


def _read_range(path: Path, start: int, max_bytes: int) -> tuple[str, int]:
    """Read up to max_bytes from path starting at offset."""
    if not path.exists():
        return "", 0
    size = path.stat().st_size
    if start < 0 or start > size:
        start = 0
    with path.open("rb") as f:
        if start == 0 and size > max_bytes:
            start = size - max_bytes
        f.seek(start)
        data = f.read()
    try:
        text = data.decode("utf-8", errors="replace")
    except Exception:
        text = data.decode(errors="replace")
    return text, start + len(data)


def _extract_timestamp(line: str) -> float | None:
    """Extract log timestamp from a line."""
    match = TS_RE.search(line)
    if not match:
        return None
    stamp = f"{match.group(1)},{match.group(2)}"
    try:
        return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S,%f").timestamp()
    except Exception:
        return None


def _scan_lines(
    text: str,
    response_re: re.Pattern,
    request_re: re.Pattern,
    heartbeat_re: re.Pattern,
) -> tuple[float | None, float | None, float | None]:
    """Return latest response, request, and heartbeat timestamps."""
    last_response = None
    last_request = None
    last_heartbeat = None
    for line in text.splitlines():
        ts = _extract_timestamp(line)
        if ts is None:
            continue
        if response_re.search(line):
            last_response = ts
        if request_re.search(line):
            last_request = ts
        if heartbeat_re.search(line):
            last_heartbeat = ts
    return last_response, last_request, last_heartbeat


def _load_state(path: Path) -> dict:
    """Load watchdog state from JSON file."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _save_state(path: Path, state: dict) -> None:
    """Persist watchdog state to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def _send_telegram(token: str, chat_id: str, text: str) -> None:
    """Send a Telegram message using Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = request.Request(url, data=data, method="POST")
    with request.urlopen(req, timeout=10) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"telegram http {resp.status}")


def _config_from_env(args: argparse.Namespace) -> WatchdogConfig:
    """Build watchdog config from CLI args and environment."""
    log_path = Path(_env_get("WATCHDOG_LOG_PATH") or args.log_path)
    state_path = Path(_env_get("WATCHDOG_STATE_PATH") or args.state_path)
    idle_min = _env_int("WATCHDOG_IDLE_MIN", args.idle_min)
    cooldown_min = _env_int("WATCHDOG_COOLDOWN_MIN", args.cooldown_min)
    restart_cooldown_min = _env_int("WATCHDOG_RESTART_COOLDOWN_MIN", 30)
    max_bytes = _env_int("WATCHDOG_MAX_BYTES", args.max_bytes)
    response_pat = _env_get("WATCHDOG_RESPONSE_REGEX") or RESPONSE_RE.pattern
    request_pat = _env_get("WATCHDOG_REQUEST_REGEX") or UPDATE_RE.pattern
    heartbeat_pat = _env_get("WATCHDOG_HEARTBEAT_REGEX") or HEARTBEAT_RE.pattern
    require_requests = _env_bool("WATCHDOG_REQUIRE_REQUESTS", True)
    require_heartbeat = _env_bool("WATCHDOG_REQUIRE_HEARTBEAT", False)
    restart_on_idle = _env_bool("WATCHDOG_RESTART_ON_IDLE", False)
    restart_cmd = _env_get("WATCHDOG_RESTART_CMD") or "/bin/systemctl restart tg-monitor.service"
    restart_timeout_sec = _env_int("WATCHDOG_RESTART_TIMEOUT_SEC", 60)
    token = _env_get("WATCHDOG_TOKEN") or args.token or _env_get("BOT_TOKEN")
    chat_id = (
        _env_get("WATCHDOG_CHAT_ID")
        or args.chat_id
        or _env_get("CHAT_ID")
        or _env_get("CONTROL_CHAT_ID")
    )

    if not token or not chat_id:
        raise ValueError("missing BOT_TOKEN/CHAT_ID (or WATCHDOG_TOKEN/WATCHDOG_CHAT_ID)")

    return WatchdogConfig(
        log_path=log_path,
        state_path=state_path,
        idle_min=idle_min,
        cooldown_min=cooldown_min,
        restart_cooldown_min=restart_cooldown_min,
        max_bytes=max_bytes,
        response_re=re.compile(response_pat),
        request_re=re.compile(request_pat),
        heartbeat_re=re.compile(heartbeat_pat),
        require_requests=require_requests,
        require_heartbeat=require_heartbeat,
        restart_on_idle=restart_on_idle,
        restart_cmd=restart_cmd,
        restart_timeout_sec=restart_timeout_sec,
        token=token,
        chat_id=chat_id,
    )


def main() -> int:
    """Run watchdog checks and alert/restart when idle."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-path", default="/home/ubuntu/tg-monitoring/logs/tg-monitoring.log")
    parser.add_argument("--state-path", default="/home/ubuntu/tg-monitoring/data/log_watchdog_state.json")
    parser.add_argument("--idle-min", type=int, default=10)
    parser.add_argument("--cooldown-min", type=int, default=10)
    parser.add_argument("--max-bytes", type=int, default=2 * 1024 * 1024)
    parser.add_argument("--token", default=None)
    parser.add_argument("--chat-id", default=None)
    args = parser.parse_args()
    try:
        cfg = _config_from_env(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    state = _load_state(cfg.state_path)
    last_offset = int(state.get("last_offset", 0) or 0)
    last_response = state.get("last_response_ts")
    last_request = state.get("last_request_ts")
    last_heartbeat = state.get("last_heartbeat_ts")
    last_alert = float(state.get("last_alert_ts", 0.0) or 0.0)
    last_restart = float(state.get("last_restart_ts", 0.0) or 0.0)

    size = cfg.log_path.stat().st_size if cfg.log_path.exists() else 0
    if last_offset > size:
        last_offset = 0

    text, new_offset = _read_range(cfg.log_path, last_offset, cfg.max_bytes)
    resp_ts, req_ts, hb_ts = _scan_lines(
        text, cfg.response_re, cfg.request_re, cfg.heartbeat_re
    )

    if resp_ts is not None:
        last_response = resp_ts
    if req_ts is not None:
        last_request = req_ts
    if hb_ts is not None:
        last_heartbeat = hb_ts

    now = time.time()
    idle_sec = cfg.idle_min * 60
    cooldown_sec = cfg.cooldown_min * 60
    restart_cooldown_sec = cfg.restart_cooldown_min * 60

    should_check = True
    if cfg.require_requests:
        should_check = bool(last_request) and (now - float(last_request) <= idle_sec)
    if cfg.require_heartbeat and should_check:
        should_check = bool(last_heartbeat) and (now - float(last_heartbeat) <= idle_sec)

    if should_check and (not last_response or now - float(last_response) >= idle_sec):
        if cfg.restart_on_idle and now - last_restart >= restart_cooldown_sec:
            try:
                subprocess.run(
                    cfg.restart_cmd,
                    shell=True,
                    check=True,
                    timeout=cfg.restart_timeout_sec,
                )
                state["last_restart_ts"] = now
            except Exception as exc:
                print(f"restart failed: {exc}", file=sys.stderr)
        if now - last_alert >= cooldown_sec:
            last_resp_str = (
                datetime.fromtimestamp(float(last_response)).isoformat()
                if last_response
                else "never"
            )
            text = (
                "tg-monitoring watchdog: no responses sent in the last "
                f"{cfg.idle_min} minutes on {_host_display_name()}. "
                f"Last response: {last_resp_str}."
            )
            _send_telegram(cfg.token, str(cfg.chat_id), text)
            state["last_alert_ts"] = now

    state["last_offset"] = new_offset
    if last_response:
        state["last_response_ts"] = last_response
    if last_request:
        state["last_request_ts"] = last_request
    if last_heartbeat:
        state["last_heartbeat_ts"] = last_heartbeat
    _save_state(cfg.state_path, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
