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
# Test RSS store functionality
python3 scripts/test_rss_store.py

# Test RSS add/remove operations
python3 scripts/test_rss_add_remove.py

# Test exporter compatibility (Docker vs Python)
python scripts/test_exporters.py

# Run smoke tests
python scripts/smoke_test.py

# Test QR code functionality
python scripts/test_qrcode.py

# Live health check
python scripts/live_check.py
```

### Database Operations
```bash
# Migrate existing RSS data to PostgreSQL
python3 scripts/migrate_rss_to_postgres.py --dry-run  # Preview changes
python3 scripts/migrate_rss_to_postgres.py            # Perform migration

# Update database schema
python3 scripts/migrate_rss_schema.py
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
- `DATABASE_URL`: PostgreSQL connection string (optional, falls back to JSON)
- `NODE_EXPORTER_TYPE`: `auto`/`docker`/`python` for metrics collection
- `MODULES`: Comma-separated list of enabled modules
- Threshold settings for CPU, memory, disk monitoring

### Data Storage
The application supports hybrid storage with automatic fallback:
- **PostgreSQL**: Primary storage with asyncpg for performance and reliability
- **JSON Files**: Fallback storage for backward compatibility and development
- **Migration**: Automatic schema creation and data migration support

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
- `asyncpg>=0.29`: PostgreSQL async driver

## Current Status

### Completed Features ✅
- **Modular Architecture**: Fully implemented with dynamic module loading
- **PostgreSQL Integration**: Hybrid storage with automatic JSON fallback
- **RSS Service Enhancement**: Per-chat feed management with async/await
- **Security**: All hardcoded credentials removed, environment variable configuration
- **Documentation**: Comprehensive README, security advisory, and migration guides
- **Testing**: Database migration scripts and functional tests

### Production Ready ✅
- **Memory Efficiency**: Optimized with repository pattern and LRU caching
- **Error Handling**: Comprehensive exception handling and user feedback
- **Database Migration**: Zero-downtime migration from JSON to PostgreSQL
- **Security**: Environment-based configuration with secure defaults
- **Monitoring**: Built-in health checks and performance monitoring

## Development Best Practices

### Security Guidelines
- **Never commit secrets**: Use environment variables for all credentials
- **Use .env.example**: Provide templates with placeholder values
- **Environment validation**: Validate configuration on startup
- **Secure defaults**: Use safe fallbacks in Docker Compose and configuration

### Code Quality
- **Type hints**: Use type annotations for better code clarity
- **Async/await**: Prefer async patterns for I/O operations
- **Error handling**: Implement comprehensive exception handling with user feedback
- **Testing**: Add tests for new features using the scripts/ directory pattern

### Database Operations
- **Hybrid storage**: Always maintain JSON fallback for development
- **Migration scripts**: Create migration utilities for schema changes
- **Connection pooling**: Use proper database connection management
- **Transactions**: Use appropriate transaction boundaries for data consistency

### Module Development
- **Base contract**: Implement the Module interface in `tgbot/modules/base.py`
- **Router patterns**: Use aiogram Router for command handling
- **Service layer**: Separate business logic into services
- **Configuration**: Use the centralized config system for settings