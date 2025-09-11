# tg-monitoring

Lightweight Telegram notifier for a single server using Node Exporter metrics.

What it does:
- Scrapes `http://127.0.0.1:9100/metrics` (Node Exporter)
- Evaluates CPU, memory, and disk thresholds
- Sends Telegram alerts on state changes (ALERT/RECOVERED)
- Responds to `/status` in your ops group with a current summary

Quick start
- Create `.env` with at least:
  - `bot_token=...`
  - `chat_id=...` (group/channel id)
- Optional tuning (defaults in code):
  - `SAMPLE_INTERVAL_SEC=15`
  - `ALERT_MIN_CONSECUTIVE=3`
  - `NODE_EXPORTER_URL=http://127.0.0.1:9100/metrics`
  - `CPU_LOAD_PER_CORE_WARN=0.9`
  - `MEM_AVAILABLE_PCT_WARN=0.10`
  - `DISK_USAGE_PCT_WARN=0.85`
  - `ENABLE_INODES=false`
  - `INODE_FREE_PCT_WARN=0.10`
  - `STATE_FILE=data/state.json`

Run locally
- `python3 -m monitor.main`

Systemd
- Copy `systemd/tg-monitor.service` to `~/.config/systemd/user/` or `/etc/systemd/system/`
- `systemctl --user daemon-reload && systemctl --user enable --now tg-monitor.service`

Notes
- Only built-in Python libs are used; no extra dependencies.
- Node Exporter port is mapped to 9100 per `/home/ubuntu/monitoring/docker-compose.yml`.
- The bot only sends on state changes; use `/status` anytime for a snapshot.

