# tg-monitoring

Lightweight Telegram bot for single-server operations. It reads Node Exporter
metrics, evaluates thresholds, sends Telegram alerts on state changes, and
provides operator commands for status, RSS digests, QR codes, and sticker packs.

## Business Process

1. `tgbot.main` loads `.env`/environment config and takes a PID lock.
2. `App` builds the Telegram bot, dispatcher, database manager, stores, clients,
   logging middleware, and configured modules.
3. Default modules are `monitoring,rss,help,stickers,qrcode`.
4. Routers handle Telegram commands and callbacks.
5. Background loops poll metrics and RSS feeds.
6. PostgreSQL is used when `DATABASE_URL` is configured; JSON files in `data/`
   are the fallback backend.
7. Alerts and command responses are sent back to the configured Telegram chat.

## Features

- Scrapes Node Exporter metrics from `NODE_EXPORTER_URL`.
- Evaluates CPU load per core, memory, disk, and optional inode thresholds.
- Sends `ALERT` and `RECOVERED` Telegram messages only on state changes.
- Supports `/status` for live server snapshots.
- Supports per-chat RSS subscriptions and scheduled digest delivery.
- Supports `/help`, `/version`, `/qrcode`, and `/kang`.
- Runs as a Docker Compose stack managed by systemd.
- Uses PostgreSQL, or JSON fallback when `DATABASE_URL` is intentionally unset.

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
```

Set at least:

```dotenv
bot_token=123456789:AA...
chat_id=-1001234567890
POSTGRES_DB=tgmonitoring
POSTGRES_USER=tgmonitor
POSTGRES_PASSWORD=change_this_password
```

For the bundled Docker Compose stack with PostgreSQL, set or uncomment
`DATABASE_URL` to use the Compose service name:

```dotenv
DATABASE_URL=postgresql://tgmonitor:change_this_password@postgres:5432/tgmonitoring
NODE_EXPORTER_URL=http://node-exporter:9100/metrics
NODE_EXPORTER_TYPE=auto
```

If `DATABASE_URL` is unset, that is an intentional JSON fallback and the bot
starts with JSON storage in `data/`.

### 2. Build And Start

Install the systemd unit, then use the Makefile targets.

```bash
sudo cp systemd/tg-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload

make build
make up
```

Operational commands:

```bash
make status
make logs
make restart
make down
make full-stop
```

The systemd unit starts `docker compose -f docker-compose.yml up -d`. The stack
contains the bot container, PostgreSQL container, and Node Exporter container.
`make full-stop` is for watchdog-managed deployments.

### 3. Server Host Metrics Exporter

The bot should monitor the server host, not the bot container. In this repo,
server host means the Ubuntu/VPS machine running Docker, and bot container means
the `tg-monitoring` container. Docker Compose starts a `prom/node-exporter`
service with the host PID namespace and read-only mounts for the server host
root filesystem, `/proc`, and `/sys`. The bot scrapes it on the private Compose
network.

The important parts are `-v /:/host:ro,rslave`, `/proc:/host/proc:ro`,
`/sys:/host/sys:ro`, `--path.rootfs=/host`, `--path.procfs=/host/proc`, and
`--path.sysfs=/host/sys`; these make Node Exporter report server host CPU,
memory, disk, filesystem, network, and boot metrics instead of the exporter
container's filesystem view.

Configure the bot to scrape the Compose-managed exporter by service name:

```dotenv
NODE_EXPORTER_URL=http://node-exporter:9100/metrics
NODE_EXPORTER_TYPE=auto
```

With `NODE_EXPORTER_TYPE=auto`, the app does not start an exporter; it only
scrapes `NODE_EXPORTER_URL`. Use this for the normal server-host monitoring
deployment.

If you previously started a manual `node-exporter` container on port 9100, it is
no longer needed after `NODE_EXPORTER_URL` points to
`http://node-exporter:9100/metrics`. The Compose-managed exporter is only on the
private Compose network and does not publish port `9100` to the public server
interface.

Advanced modes:

- `NODE_EXPORTER_TYPE=docker`: the app tries to manage a separate
  `prom/node-exporter` container. This duplicates Compose ownership and needs
  Docker access from the app process, so it is not recommended for this
  deployment.
- `NODE_EXPORTER_TYPE=python`: the app starts a Python exporter process. When the
  bot runs inside Docker, this reports container-local metrics from the bot
  container, so it is not recommended for server-host monitoring.

## Configuration

Common settings:

- `bot_token`: Telegram bot token.
- `chat_id`: default alert/control chat.
- `CONTROL_CHAT_ID`: optional control chat override.
- `HOST_DISPLAY_NAME`: optional display name override for `/status`, alerts, and RSS digests.
- `ALLOW_ANY_CHAT`: allow the bot to respond outside configured chats.
- `ALLOWED_CHATS`: comma-separated extra allowed chats.
- `MODULES`: comma-separated modules; default is `monitoring,rss,help,stickers,qrcode`.
- `NODE_EXPORTER_URL`: Prometheus metrics endpoint.
- `NODE_EXPORTER_TYPE`: `auto`, `docker`, or `python`; use `auto` with an
  external server-host Node Exporter for normal server-host monitoring.
- `SAMPLE_INTERVAL_SEC`: monitoring poll interval.
- `ALERT_MIN_CONSECUTIVE`: alert debounce threshold.
- `CPU_LOAD_PER_CORE_WARN`: CPU load-per-core alert threshold.
- `MEM_AVAILABLE_PCT_WARN`: available memory warning threshold.
- `DISK_USAGE_PCT_WARN`: disk used warning threshold.
- `ENABLE_INODES`: enable inode checks.
- `DATABASE_URL`: PostgreSQL URL; unset means JSON fallback.
- `STATE_FILE`: JSON state fallback path.
- `RSS_STORE_FILE`: JSON RSS fallback path.

## Bot Commands

- `/status`: get current system metrics.
- `/help`: show command menu with inline buttons.
- `/version`: show build/version info.
- `/rss_add <url>`: subscribe this chat to one or more RSS feeds.
- `/rss_rm <url>`: remove a feed from this chat.
- `/rss_ls`: list feeds, pending counts, and next digest time.
- `/qrcode <text>`: generate a QR code from text or a replied message.
- `/kang <optional_suffix>`: add the replied sticker to a user sticker pack.

## Monitoring Flow

`MonitoringService` periodically fetches Node Exporter metrics, evaluates them
with configured thresholds, persists per-check state, and notifies the alert chat
when a check enters or leaves alert state. `/status` performs the same fetch and
evaluation on demand, then returns a formatted snapshot.

## RSS Flow

RSS subscriptions are scoped per chat. The poll loop parses all active feeds,
deduplicates seen items, and queues new items for each subscribed chat. The digest
loop periodically sends queued items, splitting messages to stay under Telegram's
HTML message limit.

## Storage

The app creates a `DatabaseManager` on startup.

- If `DATABASE_URL` is set and reachable, PostgreSQL stores monitoring state,
  RSS feeds, and RSS items.
- If `DATABASE_URL` is unset, hybrid stores intentionally fall back to JSON
  files.
- If `DATABASE_URL` is set but bad or unreachable during startup, startup can
  fail instead of silently falling back.
- `schema.sql` is applied automatically by the app and mounted into the
  PostgreSQL container for initial database creation.

Known implementation note: some RSS PostgreSQL helper methods are less detailed
than the JSON fallback, so verify both backends when changing RSS behavior.

## Deployment

The primary deployment path is:

```text
systemd tg-monitor.service
  -> docker compose up -d
     -> tg-monitoring container
     -> postgres container
     -> node-exporter container
```

The service also creates the external Docker network `tg-monitoring_net` before
starting Compose. Because the unit currently runs Compose in detached mode, use
`docker ps`, `docker logs`, or `make logs` to inspect container health.
The provided unit hardcodes `/home/ubuntu/tg-monitoring` and `User=ubuntu` /
`Group=ubuntu`; edit `systemd/tg-monitor.service` before installing it if your
path, user, or group differ.

Related units in `systemd/`:

- `tg-monitoring-log.service`: follows container logs into `logs/tg-monitoring.log`.
- `tg-monitoring-watchdog.timer`: runs the log watchdog every minute.
- `tg-monitoring-daily.timer`: restarts the stack daily at 02:00.

## Daily Restart

Preferred path: enable `tg-monitoring-daily.timer`. Cron is only an optional
fallback for hosts that do not use the bundled systemd timer.
The daily restart is a defensive workaround for the current unknown hang/dead
state failure mode. Keep `tg-monitoring-watchdog.timer` enabled as well so the
next incident leaves request/response/heartbeat evidence for root-cause analysis
instead of only relying on scheduled restarts.

```cron
0 2 * * * /home/ubuntu/tg-monitoring/scripts/daily_restart.sh
```

Or install it manually with:

```bash
crontab -e
```

`make daily-restart` restarts `tg-monitor.service`.
Cron must be able to run `sudo systemctl` non-interactively.

## Development

Run the bot directly only for local debugging:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m tgbot.main
```

Useful scripts:

```bash
python3 scripts/test_rss_store.py
python3 scripts/test_rss_add_remove.py
python3 scripts/migrate_rss_to_postgres.py --dry-run
python3 scripts/migrate_rss_to_postgres.py
python3 scripts/migrate_rss_schema.py
python3 scripts/test_exporters.py
```

Project structure:

```text
tgbot/
├── core/           # app lifecycle, DB, logging, middleware
├── domain/         # config, metrics model/parser, threshold evaluator
├── modules/        # module adapters and exporter implementations
├── services/       # Telegram command and background business logic
├── stores/         # PostgreSQL/JSON persistence
└── clients/        # Node Exporter and RSS clients
```

Each major directory includes an `AGENTS.md` file with contributor guidance.

## Requirements

- Docker and Docker Compose plugin for deployment.
- systemd for the provided service file.
- Python 3.10+ for local development.
- Telegram bot token and allowed chat ID.

## License

This project is licensed under the GNU General Public License v3.0 or later.
See `LICENSE.md` and the license headers in source files for details.

## Contributors

- Author: Claude (Anthropic AI Assistant)
- Co-author: goodmeow (Harun Al Rasyid) <aarunalr@pm.me>

## Credits

- QR code generation uses the MIT-licensed [`QR-Code-generator`](https://github.com/nayuki/QR-Code-generator) by Project Nayuki.
