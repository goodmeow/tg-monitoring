# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Installation
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Alternative: use Makefile
make install
```

### Running the Application
```bash
# Run the bot directly
python -m tgbot.main

# Alternative: use Makefile
make run
```

### Testing and Validation
```bash
# Test exporter compatibility (Docker vs Python)
python scripts/test_exporters.py

# Run smoke tests
python scripts/smoke_test.py

# Test QR code functionality
python scripts/test_qrcode.py

# Live health check
python scripts/live_check.py
```

### Service Management (systemd)
```bash
# Install and enable as user service
make enable

# Check service status
make status

# View logs
make logs

# Restart service
make restart

# Stop and disable service
make stop
```

## Architecture Overview

### Modular Design
The bot uses a modular architecture centered around `tgbot/core/app.py`:

- **Core**: Application framework (`App`, `AppContext`) handles module lifecycle
- **Modules**: Self-contained features under `tgbot/modules/`
  - `monitoring/`: System metrics and alerting
  - `rss/`: RSS feed management and digests
  - `help/`: Help commands with inline keyboards
  - `qrcode/`: QR code generation
  - `exporters/`: Flexible metrics collection (Docker/Python)
- **Services**: Business logic layer in `tgbot/services/`
- **Stores**: Data persistence (`StateStore`, `RssStore`)
- **Clients**: External service interfaces (`NodeExporterClient`, `FeedClient`)

### Module System
Modules are loaded dynamically via the `MODULES` environment variable (default: `monitoring,rss,help,stickers,qrcode`). Each module implements the base contract in `tgbot/modules/base.py` and provides:
- Router registration for handlers
- Background tasks via async coroutines
- Startup/shutdown hooks

### Configuration
Configuration is managed through `tgbot/domain/config.py` with `.env` file support. Key settings:
- `bot_token`, `chat_id`: Required Telegram credentials
- `NODE_EXPORTER_TYPE`: `auto`/`docker`/`python` for metrics collection
- `MODULES`: Comma-separated list of enabled modules
- Threshold settings for CPU, memory, disk monitoring

### Metrics Collection
The exporters module provides flexible metrics collection:
- **Auto-detection**: Chooses Docker or Python exporter based on availability
- **Docker**: Manages existing node-exporter container
- **Python**: Pure Python implementation using psutil
- Both provide identical Prometheus metrics format

### Entry Points
- Primary: `python -m tgbot.main`
- Legacy redirect: `python -m monitor.main` → `tgbot.main`
- Singleton protection via pidfile (`data/tg-monitor.pid`)

## Development Guidelines

### Adding New Modules
1. Create `tgbot/modules/yourmodule/module.py` with `Module` class
2. Implement base contract: `routers()`, `tasks()`, optional hooks
3. Add to `MODULES` env variable or use full module path

### Testing
Use the scripts in `scripts/` directory for component testing:
- `test_exporters.py`: Validates exporter compatibility
- `smoke_test.py`: Basic functionality validation

### Dependencies
Core dependencies are minimal and focused:
- `aiogram>=3.4`: Telegram bot framework
- `httpx>=0.27`: Async HTTP client
- `prometheus-client>=0.20`: Metrics parsing
- `psutil>=5.9`: System metrics (Python exporter)
- `feedparser>=6.0`: RSS parsing
- `Pillow>=10.0`: QR code image generation

## Planned Development

### PostgreSQL Migration Roadmap

#### Phase 1: PostgreSQL Rollout
- Finalize the decision to adopt PostgreSQL as the primary state backend (no SQLite intermediate step)
- Pre-flight checklist for getting comfortable with Postgres:
  - Install Postgres locally or run a Docker container; set up a GUI tool (pgAdmin, TablePlus)
  - Work through basic SQL: CREATE TABLE, INSERT, SELECT, UPDATE, DELETE
  - Confirm connectivity using the planned `DATABASE_URL` via GUI or `psql`
  - Write and run a minimal Python script with `asyncpg` that executes `SELECT 1`
  - Create draft tables manually (chats, feeds, state) to internalize the schema
  - Document the steps and findings for future reference

#### Phase 2: Database Implementation
- Define the PostgreSQL schema covering chats, monitoring state, RSS feeds/pending items, and key-value settings
- Build a connection/repository layer using an async Postgres client (asyncpg or SQLAlchemy 2)
- Introduce configuration options (`DATABASE_URL`, pool sizes) and initialize the DB connection during app startup
- Replace the JSON-based stores with Postgres-backed repositories for monitoring state and RSS data

#### Phase 3: Migration & Operations
- Develop a migration script that imports `data/state.json` and `data/rss.json` into PostgreSQL
- Document database backup and operations procedures (pg_dump usage, retention, schema migrations)

#### Phase 4: Follow-up Features
- Expand admin commands to manage per-chat settings and module toggles once the database layer is in place