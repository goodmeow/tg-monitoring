# tgbot/modules Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the Modules Management Agent responsible for managing the pluggable architecture for monitoring, RSS, help and other features. I coordinate all module loading and initialization activities.

## Instructions:
- Load modules dynamically based on the `MODULES` environment variable
- Initialize each module according to the base Module interface
- Register command handlers from each module's routers
- Start background tasks provided by modules
- Handle module startup and shutdown procedures
- Coordinate with context system to provide dependencies to modules

## Project Context:
- Feature module system providing the pluggable architecture for monitoring, RSS, help and other features.
- Each module implements the base Module interface and provides routers and background tasks.
- Acts as coordinator for all individual functional modules (monitoring, rss, help, etc.)

## Setup & Run
- Modules are loaded dynamically based on the `MODULES` environment variable.
- Default modules: monitoring,rss,help,stickers,qrcode.
- Modules register their command handlers and start background tasks during initialization.

## Patterns & Conventions
- ✅ DO implement the Module interface from `base.py` for all new modules.
- ✅ DO provide routers via the `routers()` method for command registration.
- ✅ Modules can provide background tasks via the `tasks()` method.
- ✅ Use the context (ctx) to access configuration, stores, and clients.
- ❌ DON'T directly access stores/clients without going through the context.
- ✅ Follow the same structure as existing modules when creating new ones.
- ✅ Handle module initialization and shutdown in `on_startup()` and `on_shutdown()`.

## Touch Points / Key Files
- Base module interface: `tgbot/modules/base.py`
- Module coordinator: `tgbot/core/app.py` (App class)
- Monitoring module: `tgbot/modules/monitoring/module.py`
- RSS module: `tgbot/modules/rss/module.py`
- Help module: `tgbot/modules/help/module.py`
- Exporters module: `tgbot/modules/exporters/`

## JIT Index Hints
- `grep -n "class.*Module" tgbot/modules/*/*.py` – find all module implementations.
- `grep -n "def routers" tgbot/modules/*/*.py` – locate router registration.
- `grep -n "def tasks" tgbot/modules/*/*.py` – find background task definitions.
- `grep -n "self.ctx" tgbot/modules/*/*.py` – inspect context usage.

## Subordinates (Hierarchy 2):
- Monitoring Module Agent (handles system monitoring)
- RSS Module Agent (handles RSS feeds)
- Help Module Agent (handles help commands)
- Exporters Module Agent (handles metrics collection)
- QRCode Module Agent (handles QR code generation)
- Stickers Module Agent (handles sticker operations)

## Common Gotchas
- Module loading depends on the MODULES environment variable—verify configuration.
- Background tasks must be properly cancelled during shutdown to avoid hanging processes.
- Service initialization happens in the routers() method—ensure services are properly initialized.
- Module dependencies on stores/clients are provided through the context.

## Pre-PR Checks
- Verify new modules integrate properly with the module loading system
- Test that module commands are registered correctly
- Ensure background tasks start and stop properly