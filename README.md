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

### 1. Configuration

Create `.env` with at least:
- `bot_token=...` (your Telegram bot token)
- `chat_id=...` (your Telegram group/chat ID)

Optional tuning (defaults in code):
- `SAMPLE_INTERVAL_SEC=15`
- `ALERT_MIN_CONSECUTIVE=3`
- `NODE_EXPORTER_URL=http://127.0.0.1:9100/metrics`
- `NODE_EXPORTER_TYPE=auto` (auto/docker/python) **NEW**
- `DATABASE_URL=` (PostgreSQL connection string, optional) **NEW**
- `CPU_LOAD_PER_CORE_WARN=0.9`
- `MEM_AVAILABLE_PCT_WARN=0.10` (warn when free RAM ≤ 10%; dashboard shows used%)
- `DISK_USAGE_PCT_WARN=0.85`
- `ENABLE_INODES=false`
- `INODE_FREE_PCT_WARN=0.10`
- `STATE_FILE=data/state.json`
- `LOCK_FILE=data/tg-monitor.pid` (pidfile untuk mencegah instance ganda)
- `ALLOW_ANY_CHAT=false` (true = bot menerima perintah dari semua chat tanpa restart)
- `ALLOWED_CHATS=` (daftar tambahan, pisahkan koma, mis. `-10012345,@mychannel`)

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Node Exporter Setup

The bot now supports two methods for metrics collection:

#### Option A: Docker Node Exporter (Default)
```bash
docker run -d \
  --name node-exporter \
  --restart unless-stopped \
  -p 9100:9100 \
  -v /:/host:ro,rslave \
  prom/node-exporter:latest \
  --path.rootfs=/host
```

#### Option B: Python Node Exporter (No Docker Required)
Set `NODE_EXPORTER_TYPE=python` in `.env`. The bot will automatically start a Python-based exporter.

Requirements for Python exporter:
```bash
pip install prometheus-client psutil flask
```

### Optional: PostgreSQL Setup

The bot supports PostgreSQL for enhanced data persistence with automatic fallback to JSON files:

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE tgmonitoring;
CREATE USER tgmonitor WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE tgmonitoring TO tgmonitor;
\q

# Add to .env
DATABASE_URL=postgresql://tgmonitor:your_password@localhost/tgmonitoring
```

The bot will automatically:
- Create required tables on first run
- Use PostgreSQL when available, fallback to JSON otherwise
- Migrate existing JSON data when PostgreSQL is enabled

### 4. Run the Bot

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the bot (modular architecture)
python -m tgbot.main
```

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
- `/rss` - RSS feed management (if enabled)
- `/qrcode <text>` - Generate a QR code for text or replied message
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
python test_exporters.py
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
- Singleton guard via `LOCK_FILE` ensures hanya satu instance bot berjalan
- `ALLOW_ANY_CHAT=true` membuat bot otomatis melayani grup baru tanpa restart

## Requirements

- Python 3.10+
- For Docker exporter: Docker installed and running
- For Python exporter: No Docker required

## License

This project is licensed under the GNU General Public License v3.0 or later.
See the license headers in source files for details.

## Contributors

- Author: Claude (Anthropic AI Assistant)
- Co-author: goodmeow (Harun Al Rasyid) <aarunalr@pm.me>

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
