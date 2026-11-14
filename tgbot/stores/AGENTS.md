# tgbot/stores Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the Data Storage Agent responsible for managing data persistence using PostgreSQL with automatic fallback to JSON storage.

## Instructions:
- Manage PostgreSQL connections and operations
- Handle automatic fallback to JSON storage when PostgreSQL is unavailable
- Store and retrieve monitoring state data
- Manage RSS feed data persistence
- Perform database schema creation and migrations
- Handle data backup and recovery operations
- Maintain data consistency across storage backends

## Project Context:
- Component responsible for data persistence functionality
- Implements hybrid storage system with PostgreSQL primary and JSON fallback
- Uses asyncpg for PostgreSQL operations
- Keeps one store module per domain: `state_store_v2.py` (monitoring checks) and `rss_store_v2.py` (feeds, items, digests)

## Setup & Run
- PostgreSQL connection via DATABASE_URL environment variable
- Automatic fallback to JSON storage when PostgreSQL unavailable
- Schema automatically created on startup if needed
- Migration scripts available for schema updates

## Patterns & Conventions
- ✅ DO maintain backward compatibility with JSON storage.
- ✅ DO implement proper connection pooling for PostgreSQL.
- ✅ Data operations should be async for performance.
- ✅ Use repository pattern for data access operations.
- ❌ DON'T lose data during storage transition operations.
- ✅ Implement proper error handling for database failures.
- ✅ Maintain consistency between PostgreSQL and JSON storage.

## Touch Points / Key Files
- State stores: `tgbot/stores/state_store_v2.py` (`PostgreSQLStateStore`, `AsyncStateStore`, `HybridStateStore`)
- RSS stores: `tgbot/stores/rss_store_v2.py` (`PostgreSQLRssStore`, `AsyncRssStore`, `HybridRssStore`)
- Database manager: `tgbot/core/database.py`
- Repository patterns: `tgbot/core/repository.py` and related files

## JIT Index Hints
- `grep -n "PostgreSQL\|asyncpg" tgbot/stores/*.py` – find PostgreSQL operations.
- `grep -n "fallback\|JSON" tgbot/stores/*.py` – locate fallback logic.
- `grep -n "migrate\|schema" tgbot/core/database.py` – inspect schema management.
- `grep -n "connection\|pool" tgbot/core/database.py` – find connection pooling.

## Subordinates (Hierarchy 2):
- PostgreSQL Management Agent (handles PostgreSQL operations)
- JSON Storage Agent (handles JSON file operations)
- Migration Agent (handles database migrations)
- Backup Agent (handles data backup operations)

## Common Gotchas
- Fallback system must be transparent to the application.
- Connection pooling needs proper configuration to avoid resource exhaustion.
- Schema migrations should be tested carefully to prevent data loss.
- JSON storage must maintain the same interface as PostgreSQL.
- `JsonRepository` buffers writes: call `HybridStateStore.save()` after state changes or nothing reaches `data/state.json`.
- Digest delivery is peek-then-ack: `get_pending_digest()`, send, then `remove_pending_items()` only for delivered ids.
- PostgreSQL stores feed ETag/Last-Modified in `settings` (key hashed with SHA-1) and prunes sent `rss_items` each poll cycle.
- `/rss_ls` pending counts come from a grouped `rss_items` query on PostgreSQL; keep that path working.

## Pre-PR Checks
- Verify PostgreSQL connection works properly
- Test fallback to JSON storage when PostgreSQL unavailable
- Confirm a failed digest send leaves items pending and a successful send acks only included items
- Confirm state survives a save/reload cycle on the JSON backend
- Confirm migration scripts work correctly
- Check data consistency between storage backends