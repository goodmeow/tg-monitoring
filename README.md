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
  - `chat_id=...` (group id)
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

Install deps (recommended venv)
- `python3 -m venv .venv && . .venv/bin/activate`
- `pip install -r requirements.txt`

Run locally
- `. .venv/bin/activate && python -m monitor.main`

Modular architecture (draft)
- New OOP+Modular skeleton lives under `tgbot/`.
- You can try the new entrypoint:
  - `. .venv/bin/activate && python -m tgbot.main`
- Enable/disable features via `MODULES` env (comma-separated). Shorthand names resolve to `tgbot.modules.<name>`.
- Example: `MODULES=monitoring,rss`.


Systemd
- Copy `systemd/tg-monitor.service` to `~/.config/systemd/user/` or `/etc/systemd/system/`
- `systemctl --user daemon-reload && systemctl --user enable --now tg-monitor.service`

Notes
- Uses `aiogram` for bot, `httpx` for HTTP, and `prometheus-client` parser.
- Node Exporter port is mapped to 9100 per `/home/ubuntu/monitoring/docker-compose.yml`.
- The bot only sends on state changes; use `/status` anytime for a snapshot.
