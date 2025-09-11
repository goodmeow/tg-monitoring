from __future__ import annotations

import signal
import threading
import time
from typing import Dict, List, Tuple

from .config import Config, load_config
from .evaluator import Thresholds, evaluate
from .metrics import NodeStats, fetch_metrics_text, parse_node_exporter_metrics
from .state import StateStore
from .telegram_client import TelegramClient


def _compose_changes_message(changes: List[Tuple[str, Dict]]) -> str:
    # changes: list of (change_type, entry), where change_type in {'ALERT','RECOVERED'}
    lines = []
    for change, entry in changes:
        emoji = "🔴" if change == 'ALERT' else "🟢"
        lines.append(f"{emoji} {change} — {entry['message']}")
    return "\n".join(lines)


def _compose_status_message(results: Dict[str, Dict]) -> str:
    # Present CPU, Mem first, then top 5 disks by usage
    lines: List[str] = []
    if 'cpu' in results:
        r = results['cpu']
        emoji = '🔴' if r['status'] == 'alert' else '🟢'
        lines.append(f"{emoji} {r['message']}")
    if 'mem' in results:
        r = results['mem']
        emoji = '🔴' if r['status'] == 'alert' else '🟢'
        lines.append(f"{emoji} {r['message']}")
    # disks
    disks = [(k, v) for k, v in results.items() if k.startswith('disk:')]
    disks.sort(key=lambda kv: kv[1].get('value', 0.0), reverse=True)
    for k, r in disks[:8]:
        emoji = '🔴' if r['status'] == 'alert' else '🟢'
        lines.append(f"{emoji} {r['message']}")
    # inodes if present
    inodes = [(k, v) for k, v in results.items() if k.startswith('inode:')]
    inodes.sort(key=lambda kv: kv[1].get('value', 0.0))  # lower free is worse
    for k, r in inodes[:8]:
        emoji = '🔴' if r['status'] == 'alert' else '🟢'
        lines.append(f"{emoji} {r['message']}")
    return "\n".join(lines) or "No metrics available"


def monitor_loop(cfg: Config, state: StateStore, tg: TelegramClient, stop_event: threading.Event):
    thresholds = Thresholds(
        cpu_load_per_core_warn=cfg.cpu_load_per_core_warn,
        mem_available_pct_warn=cfg.mem_available_pct_warn,
        disk_usage_pct_warn=cfg.disk_usage_pct_warn,
        enable_inodes=cfg.enable_inodes,
        inode_free_pct_warn=cfg.inode_free_pct_warn,
        exclude_fs_types=cfg.exclude_fs_types,
    )

    while not stop_event.is_set():
        try:
            text = fetch_metrics_text(cfg.node_exporter_url, timeout_sec=cfg.http_timeout_sec)
            stats: NodeStats = parse_node_exporter_metrics(text)
            results = evaluate(stats, thresholds)

            # Build state transitions
            changes: List[Tuple[str, Dict]] = []
            for key, cur in results.items():
                prev = state.get_check(key)
                prev_status = prev.get('status') if prev else 'unknown'
                consec = prev.get('consecutive', 0)
                last_value = prev.get('last_value')

                if cur['status'] == 'alert':
                    consec = consec + 1 if prev_status == 'alert' else 1
                    cur_state = {
                        'status': 'alert',
                        'consecutive': consec,
                        'last_value': cur.get('value'),
                        'last_ts': time.time(),
                        'message': cur['message'],
                    }
                    # Trigger alert only on transition after reaching min consecutive
                    if prev_status != 'alert' and consec >= cfg.alert_min_consecutive:
                        changes.append(('ALERT', cur))
                    state.set_check(key, cur_state)
                else:
                    # ok
                    # If was alert before, mark recovered
                    if prev_status == 'alert':
                        changes.append(('RECOVERED', cur))
                    cur_state = {
                        'status': 'ok',
                        'consecutive': 1 if prev_status == 'ok' else 0,
                        'last_value': cur.get('value'),
                        'last_ts': time.time(),
                        'message': cur['message'],
                    }
                    state.set_check(key, cur_state)

            # Persist state
            state.save()

            # Send notifications if any changes
            if changes:
                msg = _compose_changes_message(changes)
                tg.send_message(cfg.chat_id, msg)

        except Exception:
            # Avoid crashing the loop; could log in future
            pass

        stop_event.wait(cfg.sample_interval_sec)


def updates_loop(cfg: Config, state: StateStore, tg: TelegramClient, stop_event: threading.Event):
    last_update_id = state.get_last_update_id()
    while not stop_event.is_set():
        try:
            res = tg.get_updates(offset=(last_update_id + 1) if last_update_id is not None else None, timeout=cfg.long_poll_timeout_sec, allowed_updates=["message"])
            if not res.get('ok'):
                # brief backoff
                stop_event.wait(2)
                continue
            updates = res.get('result', [])
            for upd in updates:
                last_update_id = max(last_update_id or 0, upd.get('update_id', 0))
                msg = upd.get('message') or {}
                chat = msg.get('chat') or {}
                chat_id = chat.get('id')
                text = (msg.get('text') or '').strip()

                # Allow only configured chat id
                allowed = False
                for allowed_id in cfg.allowed_chat_ids:
                    if isinstance(allowed_id, int) and chat_id == allowed_id:
                        allowed = True
                        break
                    if isinstance(allowed_id, str) and str(chat_id) == allowed_id:
                        allowed = True
                        break
                if not allowed:
                    continue

                if text.startswith('/status'):
                    try:
                        ttext = fetch_metrics_text(cfg.node_exporter_url, timeout_sec=cfg.http_timeout_sec)
                        stats = parse_node_exporter_metrics(ttext)
                        thresholds = Thresholds(
                            cpu_load_per_core_warn=cfg.cpu_load_per_core_warn,
                            mem_available_pct_warn=cfg.mem_available_pct_warn,
                            disk_usage_pct_warn=cfg.disk_usage_pct_warn,
                            enable_inodes=cfg.enable_inodes,
                            inode_free_pct_warn=cfg.inode_free_pct_warn,
                            exclude_fs_types=cfg.exclude_fs_types,
                        )
                        results = evaluate(stats, thresholds)
                        msg_text = _compose_status_message(results)
                    except Exception:
                        msg_text = "Failed to collect status"
                    tg.send_message(cfg.chat_id, msg_text)

            if last_update_id is not None:
                state.set_last_update_id(last_update_id)
                state.save()

        except Exception:
            # swallow and retry
            stop_event.wait(2)


def main():
    cfg = load_config()
    state = StateStore(cfg.state_file)
    tg = TelegramClient(cfg.bot_token, timeout_sec=cfg.http_timeout_sec)

    stop_event = threading.Event()

    def handle_sig(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    t1 = threading.Thread(target=monitor_loop, args=(cfg, state, tg, stop_event), name="monitor", daemon=True)
    t2 = threading.Thread(target=updates_loop, args=(cfg, state, tg, stop_event), name="updates", daemon=True)
    t1.start()
    t2.start()

    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    finally:
        stop_event.set()
        t1.join(timeout=2)
        t2.join(timeout=2)


if __name__ == "__main__":
    main()

