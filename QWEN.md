# tg-monitoring - QWEN Context

## Project Overview

**tg-monitoring** is a lightweight Telegram notifier for server monitoring that scrapes Node Exporter metrics. It provides real-time alerts for CPU, memory, and disk usage thresholds, and responds to Telegram commands with status information.

### Key Features
- Scrapes metrics from Node Exporter (default: `http://127.0.0.1:9100/metrics`)
- Evaluates CPU, memory, and disk thresholds with configurable alerts
- Sends Telegram alerts on state changes (ALERT/RECOVERED)
- Responds to `/status` commands with current system summary
- Provides `/help` with inline buttons for quick actions
- PostgreSQL hybrid storage with automatic fallback to JSON
- Enhanced RSS service with per-chat feed management
- Flexible metrics collection via Docker or Native Python exporters
- Modular architecture with support for additional features

### Architecture

The application follows a modular architecture:

- **Core**: Application framework in `tgbot/core/` (`App`, `AppContext`) handles module lifecycle
- **Modules**: Self-contained features under `tgbot/modules/`
  - `monitoring/`: System metrics and alerting
  - `rss/`: RSS feed management and digests
  - `help/`: Help commands with inline keyboards
  - `qrcode/`: QR code generation
  - `exporters/`: Flexible metrics collection (Docker/Python)
  - `stickers/`: Sticker cloning functionality
- **Services**: Business logic layer in `tgbot/services/`
- **Stores**: Data persistence (`StateStore`, `RssStore`) with hybrid PostgreSQL/JSON support
- **Clients**: External service interfaces (`NodeExporterClient`, `FeedClient`)
- **Domain**: Configuration and domain models in `tgbot/domain/`

## Technical Stack

- **Language**: Python 3.10+
- **Bot Framework**: aiogram 3.x
- **HTTP Client**: httpx
- **Metrics Parser**: prometheus-client
- **System Metrics**: psutil (for Python exporter)
- **Database**: PostgreSQL with asyncpg (optional, fallback to JSON)
- **Storage**: Hybrid PostgreSQL/JSON with automatic fallback
- **License**: GPL v3

## Configuration

Configuration is managed through environment variables in `.env` file:

### Required Variables
- `bot_token`: Telegram bot token
- `chat_id`: Telegram group or channel ID for alerts

### Optional Variables
- `NODE_EXPORTER_URL`: Metrics endpoint (default: `http://127.0.0.1:9100/metrics`)
- `NODE_EXPORTER_TYPE`: `auto`/`docker`/`python` for metrics collection (default: `auto`)
- `DATABASE_URL`: PostgreSQL connection string (optional)
- `SAMPLE_INTERVAL_SEC`: Sampling interval (default: 15)
- `ALERT_MIN_CONSECUTIVE`: Consecutive samples required for alert (default: 3)
- `CPU_LOAD_PER_CORE_WARN`: CPU threshold (default: 0.9)
- `MEM_AVAILABLE_PCT_WARN`: Memory threshold (default: 0.10)
- `DISK_USAGE_PCT_WARN`: Disk threshold (default: 0.85)
- `ENABLE_INODES`: Enable inodes monitoring (default: false)
- `INODE_FREE_PCT_WARN`: Inodes threshold (default: 0.10)
- `STATE_FILE`: State file location (default: `data/state.json`)
- `LOCK_FILE`: PID file location (default: `data/tg-monitor.pid`)
- `MODULES`: Comma-separated list of enabled modules (default: `monitoring,rss,help,stickers,qrcode`)

## Building and Running

### Prerequisites
- Python 3.10+
- For Docker exporter: Docker installed and running
- For Python exporter: No Docker required

### Installation

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your bot token and chat ID

3. Install dependencies:
   ```bash
   # Create a virtual environment (recommended)
   python3 -m venv .venv
   source .venv/bin/activate

   # Install requirements
   pip install -r requirements.txt
   ```

### Running the Application

1. Start Node Exporter (Docker example):
   ```bash
   docker run -d \
     --name node-exporter \
     --restart unless-stopped \
     -p 9100:9100 \
     -v /:/host:ro,rslave \
     prom/node-exporter:latest \
     --path.rootfs=/host
   ```

2. Run the bot:
   ```bash
   # Direct run
   python -m tgbot.main

   # Or with activated virtual environment
   source .venv/bin/activate
   python -m tgbot.main
   ```

### Docker Deployment

The project includes a Dockerfile and Docker Compose configuration:

```bash
# Build and run with Docker
docker build -t tg-monitoring .
docker run -d --env-file .env tg-monitoring

# Or with Docker Compose (with PostgreSQL)
docker-compose -f docker-compose.postgres.yml up -d
```

### Systemd Service

The project includes systemd service files for running as a system service:

```bash
# Install as user service
cp systemd/tg-monitor.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now tg-monitor.service
```

## Database Schema

The application supports hybrid storage with PostgreSQL as the primary and JSON as the fallback:

### PostgreSQL Tables
- `chats`: Telegram chat information
- `monitoring_state`: Monitoring state storage
- `rss_feeds`: RSS feed subscriptions per chat
- `rss_items`: RSS feed items with delivery status
- `settings`: General key-value settings

## Development

### Module Development
1. Create `tgbot/modules/yourmodule/module.py` with `Module` class
2. Implement base contract: `routers()`, `tasks()`, optional hooks
3. Add to `MODULES` environment variable

### Testing
Use the scripts in `scripts/` directory for component testing:
- `test_exporters.py`: Validates exporter compatibility
- `smoke_test.py`: Basic functionality validation
- `migrate_rss_to_postgres.py`: Database migration testing
- `test_rss_store.py`: RSS store functionality testing

## Important Notes
- The bot only sends alerts on state changes
- State persistence is in `data/state.json` (or PostgreSQL if configured)
- Singleton guard via `LOCK_FILE` ensures only one bot instance runs
- `ALLOW_ANY_CHAT=true` allows the bot to serve newly discovered chats
- The modular architecture allows for extending functionality

## Security
- Credentials must be configured via environment variables
- No hardcoded credentials (as of commit f0eaf62)
- Use strong, randomly generated database passwords
- `.env` files should never be committed with real credentials