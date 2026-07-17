# tgbot Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the Application Framework Agent responsible for coordinating the main tg-monitoring application using aiogram 3.x, with modular architecture for monitoring, RSS, exporters and other features.

## Instructions:
- Initialize the main application framework and context
- Load and coordinate all modules based on configuration
- Handle application lifecycle (startup/shutdown)
- Manage the main event loop and task coordination
- Coordinate between services, stores, and clients
- Handle configuration loading and validation
- Manage singleton protection and process coordination

## Project Context:
- Main tg-monitoring application using aiogram 3.x, with modular architecture for monitoring, RSS, exporters and other features.
- Python 3.10+ application with PostgreSQL optional support and JSON fallback.
- Lives under the main package; consumed via `python -m tgbot.main` entry point.

## Setup & Run
- `make install` – install dependencies and setup virtual environment.
- `make run` – start the bot in background mode with logging.
- `python -m tgbot.main` – run the bot directly in foreground.
- `make stop` – stop any running instances and clean up PID files.
- `make restart` – restart the systemd service.

## Patterns & Conventions
- ✅ DO follow the modular architecture: modules in `tgbot/modules/`, business logic in `tgbot/services/`, persistence in `tgbot/stores/`.
- ✅ DO use the configuration system from `tgbot/domain/config.py` for all settings.
- ✅ DO implement the Module interface from `tgbot/modules/base.py` when adding new features.
- ✅ Services should implement business logic and interact with stores and clients.
- ❌ DON'T hardcode credentials or settings—use environment variables via the config system.
- ✅ Use async/await patterns throughout for I/O operations.
- ✅ Follow the repository pattern for data access with PostgreSQL/JSON fallback.

## Touch Points / Key Files
- Application entry: `tgbot/main.py`
- Core framework: `tgbot/core/app.py`
- Configuration system: `tgbot/domain/config.py`
- Module interface: `tgbot/modules/base.py`
- Main services: `tgbot/services/*`
- Data stores: `tgbot/stores/*`
- External clients: `tgbot/clients/*`

## JIT Index Hints
- `grep -r "class.*Module" tgbot/modules/` – find all module implementations.
- `grep -r "async def" tgbot/services/` – inspect async service methods.
- `grep -r "Router()" tgbot/services/` – find command handlers.
- `find tgbot -name "*.py" -exec grep -l "store\|database" {} \;` – locate data persistence logic.

## Subordinates (Hierarchy 2):
- Module Manager Agent (handles module loading)
- Configuration Agent (handles app configuration)
- Lifecycle Manager Agent (handles startup/shutdown)
- Task Coordinator Agent (handles background tasks)
- Singleton Guard Agent (handles process coordination)

## Common Gotchas
- The singleton guard in `tgbot/core/singleton.py` prevents duplicate instances—check for stale PID files.
- PostgreSQL connection pools are managed in `tgbot/core/database.py`—monitor for connection leaks.
- Always check the lock file (`data/tg-monitor.pid`) before starting multiple instances.
- Environment variables override .env file settings—verify your configuration chain.

## Pre-PR Checks
- `make run` and verify bot starts correctly
- Test basic commands like `/status`
- Ensure PostgreSQL fallback works if configured