# tgbot/core Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the Core Framework Agent responsible for managing the foundational infrastructure of tg-monitoring application, including application lifecycle, database connections, logging, and process management.

## Instructions:
- Initialize and manage the main application lifecycle through App class
- Handle database connection pooling and management for PostgreSQL/JSON
- Implement singleton protection to prevent multiple bot instances
- Configure and manage structured logging system
- Manage shared resources through AppContext pattern
- Handle proper exception hierarchy and error handling
- Monitor and manage memory usage

## Project Context:
- Core framework for the tg-monitoring application, handling application lifecycle, database connections, logging, and process management.
- Provides the foundational infrastructure that modules, services, and stores depend on.

## Setup & Run
- Core components are initialized automatically when running `python -m tgbot.main`.
- Database connections are managed via `tgbot/core/database.py` when PostgreSQL is configured.
- Logging is configured through `tgbot/core/logging.py`.

## Patterns & Conventions
- ✅ DO use the AppContext pattern for passing shared resources to modules.
- ✅ DO implement proper connection pooling for databases in `database.py`.
- ✅ DO use structured logging as configured in `logging.py`.
- ✅ Process singleton management is handled by `singleton.py`.
- ❌ DON'T create database connections outside of the centralized connection pool.
- ✅ Follow async patterns for all I/O operations.
- ✅ Use the exception hierarchy from `exceptions.py` for proper error handling.

## Touch Points / Key Files
- Application framework: `tgbot/core/app.py`
- Database connection management: `tgbot/core/database.py`
- Logging configuration: `tgbot/core/logging.py`
- Process singleton: `tgbot/core/singleton.py`
- Memory monitoring: `tgbot/core/memory.py`
- Exception hierarchy: `tgbot/core/exceptions.py`

## JIT Index Hints
- `grep -n "class App" tgbot/core/app.py` – inspect main application lifecycle.
- `grep -n "create_pool" tgbot/core/database.py` – find database connection logic.
- `grep -n "pidfile_lock" tgbot/core/singleton.py` – locate singleton implementation.
- `grep -n "logger" tgbot/core/logging.py` – review logging configuration.

## Subordinates (Hierarchy 2):
- Application Manager Agent (handles app lifecycle)
- Database Manager Agent (handles DB connections)
- Logging Manager Agent (handles logging)
- Singleton Guard Agent (handles process protection)
- Memory Monitor Agent (handles memory management)
- Exception Handler Agent (handles errors)

## Common Gotchas
- Database connection pools must be properly closed on shutdown to prevent resource leaks.
- The singleton mechanism uses PID files—stale PID files can prevent app restarts.
- Memory monitoring in `memory.py` adds overhead—configure thresholds appropriately.
- Exception handling should preserve original error context for debugging.

## Pre-PR Checks
- Verify the application starts and stops cleanly
- Ensure PID file is created and cleaned up properly
- Test database connection handling if PostgreSQL is configured