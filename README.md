# tg-monitoring

Lightweight Telegram notifier for a single server using Node Exporter metrics.

## Features

- Scrapes `http://127.0.0.1:9100/metrics` (Node Exporter)
- Evaluates CPU, memory, and disk thresholds
- Sends Telegram alerts on state changes (ALERT/RECOVERED)
- Responds to `/status` in your ops group with a current summary
- Provides `/help` with inline buttons for quick actions (Status, RSS List)
- **NEW**: PostgreSQL hybrid storage with automatic fallback to JSON
- **NEW**: Enhanced RSS service with per-chat feed management
- **NEW**: Flexible metrics collection via Docker or Native Python exporters

## Quick Start

### 1. Configure the environment

```bash
cp .env.example .env
```

Open `.env` and set at minimum:
- `bot_token=...` (the Telegram bot token)
- `chat_id=...` (the Telegram group or channel that should receive alerts)

Common adjustments (defaults already shipped in the codebase):
- `NODE_EXPORTER_URL=http://127.0.0.1:9100/metrics`
- `NODE_EXPORTER_TYPE=auto` (auto/docker/python) **NEW**
- `DATABASE_URL=` (PostgreSQL connection string, optional) **NEW**
- `POSTGRES_DB=` / `POSTGRES_USER=` / `POSTGRES_PASSWORD=` (required when using the bundled PostgreSQL Compose file; choose strong, unique secrets)
- `SAMPLE_INTERVAL_SEC=15`
- `ALERT_MIN_CONSECUTIVE=3`
- `CPU_LOAD_PER_CORE_WARN=0.9`
- `MEM_AVAILABLE_PCT_WARN=0.10` (warn when free memory ≤ 10%; dashboards report percentage used)
- `DISK_USAGE_PCT_WARN=0.85`
- `ENABLE_INODES=false`
- `INODE_FREE_PCT_WARN=0.10`
- `STATE_FILE=data/state.json`
- `LOCK_FILE=data/tg-monitor.pid`
- `ALLOW_ANY_CHAT=false` (set to true if the bot should respond in any chat without a restart)
- `ALLOWED_CHATS=` (comma-separated allow-list additions, e.g. `-10012345,@mychannel`)

### 2. Install the dependencies

Use the Makefile helper (creates the virtual environment and installs every requirement):

```bash
make install
```

Manual alternative:

```bash
# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Start Node Exporter (Docker by default)

```bash
docker run -d \
  --name node-exporter \
  --restart unless-stopped \
  -p 9100:9100 \
  -v /:/host:ro,rslave \
  prom/node-exporter:latest \
  --path.rootfs=/host

# Optional: verify the metrics endpoint
curl http://127.0.0.1:9100/metrics | head
```

#### Prefer the Python exporter?
Set `NODE_EXPORTER_TYPE=python` in `.env` and launch the helper (see `tgbot/modules/exporters/` or `scripts/test_exporters.py`). The bot still scrapes `NODE_EXPORTER_URL`, so ensure the Python exporter process is running and serving that address.

Additional Python requirements:
```bash
pip install prometheus-client psutil flask
```

### 4. Run the bot

```bash
# Start the bot via Makefile (virtualenv is activated automatically)
make run

# Or run manually
source .venv/bin/activate
python -m tgbot.main
```

### 5. (Optional) Provision PostgreSQL

Fast path: use the provided Compose file.

```bash
# Start PostgreSQL with Docker Compose
docker compose -f docker-compose.postgres.yml up -d

# Update .env once the container is live
DATABASE_URL=postgresql://tgmonitor:your_password@localhost:5432/tgmonitoring
# Ensure `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` are present in `.env` and use strong, unique values.
```

Manual installation remains supported:

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt install postgresql postgresql-contrib

# Create the database and user
sudo -u postgres psql
CREATE DATABASE tgmonitoring;
CREATE USER tgmonitor WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE tgmonitoring TO tgmonitor;
\q

# Record the connection string
DATABASE_URL=postgresql://tgmonitor:your_password@localhost/tgmonitoring
# Also set `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` in `.env` to match what you created above.
```

On start-up the bot will:
- Automatically create the required tables
- Use PostgreSQL whenever available, otherwise fall back to JSON storage
- Migrate legacy JSON data into PostgreSQL when you enable it

## Data Storage

The bot supports two storage backends with automatic fallback:

### PostgreSQL (Recommended)
- Enhanced performance and reliability
- Proper relational data structure
- Per-chat RSS feed management
- Automatic schema migration
- Configure via `DATABASE_URL` environment variable

### JSON Files (Fallback)
- No external dependencies
- Automatic backup on writes
- Legacy compatibility mode
- Files stored in `data/` directory

## Modular Architecture

The bot uses a modular architecture under `tgbot/`:

- **Core**: Application framework and context management
- **Modules**: Feature modules (monitoring, RSS, help, exporters)
- **Services**: Business logic layer
- **Stores**: Data persistence
- **Clients**: External service clients

### Available Modules

Default modules: `monitoring,rss,help,stickers,qrcode`

Enable/disable via `MODULES` env variable (comma-separated):
```bash
MODULES=monitoring,rss,help
```

### Exporters Module

New flexible metrics collection system at `tgbot/modules/exporters/`:

- **Auto-detection**: Automatically selects Docker or Python based on availability
- **Docker wrapper**: Manages existing node-exporter container
- **Python implementation**: Pure Python metrics collector using psutil
- **100% Compatible**: Both provide identical metrics format
- **Async support**: Full async/await implementation

Configuration via `NODE_EXPORTER_TYPE`:
- `auto` - Auto-detect best option (default)
- `docker` - Force Docker exporter
- `python` - Force Python exporter

## Systemd Service

```bash
# Copy service file
sudo cp systemd/tg-monitor.service /etc/systemd/system/

# Or for user service
cp systemd/tg-monitor.service ~/.config/systemd/user/

# Reload and start
systemctl --user daemon-reload
systemctl --user enable --now tg-monitor.service
```

## Bot Commands

- `/status` - Get current system metrics
- `/help` - Show available commands with inline menu
- `/rss_add <url>` - Subscribe a new RSS feed (per chat)
- `/rss_rm <url>` - Remove an RSS feed
- `/rss_ls` - List current RSS feeds and pending items
- `/qrcode <text>` - Generate a QR code for text or replied message
- `/kang <optional_suffix>` - Clone the replied sticker into your pack
- `/version` - Show current tg-monitoring build info

## Technical Stack

- **Bot Framework**: aiogram 3.x
- **HTTP Client**: httpx
- **Metrics Parser**: prometheus-client
- **System Metrics**: psutil (for Python exporter)
- **Database**: PostgreSQL with asyncpg (optional, fallback to JSON)
- **Storage**: Hybrid PostgreSQL/JSON with automatic fallback
- **License**: GPL v3

## Development

### Database Migration Scripts

The `scripts/` directory contains utilities for PostgreSQL integration:

```bash
# Test RSS store functionality
python3 scripts/test_rss_store.py

# Test RSS add/remove operations
python3 scripts/test_rss_add_remove.py

# Migrate existing RSS data to PostgreSQL
python3 scripts/migrate_rss_to_postgres.py --dry-run  # Preview changes
python3 scripts/migrate_rss_to_postgres.py            # Perform migration

# Update database schema
python3 scripts/migrate_rss_schema.py
```

### Testing Exporters

```bash
# Run compatibility tests
python scripts/test_exporters.py
```

### Project Structure

```
tgbot/
├── core/           # Application core
├── modules/        # Feature modules
│   ├── exporters/  # Metrics collection
│   ├── monitoring/ # Alert monitoring
│   ├── rss/        # RSS feeds
│   ├── help/       # Help commands
│   └── qrcode/     # QR code generator
├── services/       # Business logic
├── stores/         # Data persistence
└── clients/        # External clients
```

## Notes

- The bot only sends alerts on state changes
- Use `/status` anytime for a current snapshot
- Node Exporter runs on port 9100 by default
- State persistence in `data/state.json`
- Legacy entrypoint `python -m monitor.main` redirects to `tgbot.main`
- Singleton guard via `LOCK_FILE` ensures only one bot instance can run at a time
- `ALLOW_ANY_CHAT=true` allows the bot to serve newly discovered chats without a restart

## Requirements

- Python 3.10+
- For Docker exporter: Docker installed and running
- For Python exporter: No Docker required

## License

This project is licensed under the GNU General Public License v3.0 or later.
See `LICENSE.md` and the license headers in source files for details.

## Contributors

- Author: Claude (Anthropic AI Assistant)
- Co-author: goodmeow (Harun Al Rasyid) <aarunalr@pm.me>

## Credits

- QR code generation uses the MIT-licensed [`QR-Code-generator`](https://github.com/nayuki/QR-Code-generator) by Project Nayuki.

## Changelog

### v20250923-postgresql (Latest)
- Added PostgreSQL hybrid storage with automatic JSON fallback
- Enhanced RSS service with per-chat feed management
- Improved error handling and user feedback for RSS operations
- Added database migration and testing scripts
- Fixed RSS feed uniqueness constraint to be per-chat
- Async/await pattern throughout RSS service for better performance

### v20250913-nebula
- Added flexible node exporters module with Docker/Python support
- Auto-detection of available exporter (Docker preferred)
- 100% compatible drop-in replacement
- Full async/await support with health checks
- Configurable via NODE_EXPORTER_TYPE environment variable
- Added GPL 3.0 license headers to all source files

### Previous versions
- Modular architecture implementation
- RSS feed monitoring
- Help command with inline buttons
- Basic monitoring and alerting
