# tgbot/modules/rss Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the RSS Management Agent responsible for managing RSS feed subscriptions, parsing feeds, and distributing content to subscribed chats.

## Instructions:
- Handle RSS feed subscription requests (/rss_add)
- Manage RSS feed removals (/rss_rm)
- List current RSS feeds and pending items (/rss_ls)
- Parse RSS feeds and extract content
- Manage per-chat feed subscriptions
- Store and retrieve RSS feed data
- Schedule periodic feed checks
- Handle feed parsing errors gracefully

## Project Context:
- Module responsible for RSS feed management functionality
- Implements the Module interface from `tgbot/modules/base.py`
- Uses PostgreSQL with JSON fallback for data persistence
- Integrates with RSS services and feed clients

## Setup & Run
- RSS functionality enabled via MODULES environment variable
- Database connection uses DATABASE_URL with fallback to JSON storage
- Per-chat feed management ensures proper isolation

## Patterns & Conventions
- ✅ DO follow the modular architecture: implement the Module interface.
- ✅ DO handle feeds on a per-chat basis (not globally).
- ✅ RSS items should not be duplicated across chats.
- ✅ Use async/await patterns for feed parsing and database operations.
- ❌ DON'T store feeds globally when per-chat management is needed.
- ✅ Implement proper error handling for feed parsing.
- ✅ Respect feed update intervals to avoid excessive requests.

## Touch Points / Key Files
- Module implementation: `tgbot/modules/rss/module.py`
- RSS service: `tgbot/services/rss_service.py`
- RSS stores: `tgbot/stores/rss_store_v2.py` and related files
- Feed client: `tgbot/clients/feed_client.py` (if exists)
- Migration scripts: `scripts/migrate_rss_to_postgres.py`

## JIT Index Hints
- `grep -n "rss_add\|rss_rm\|rss_ls" tgbot/modules/rss/module.py` – find RSS commands.
- `grep -n "per-chat\|subscription" tgbot/services/rss_service.py` – locate per-chat logic.
- `grep -n "PostgreSQL\|JSON" tgbot/stores/rss_store_v2.py` – inspect storage backends.
- `grep -n "parse\|feed" tgbot/clients/feed_client.py` – find feed parsing logic.

## Subordinates (Hierarchy 2):
- Feed Parser Agent (handles feed parsing)
- Subscription Manager Agent (handles subscriptions)
- Content Distributor Agent (handles content distribution)

## Common Gotchas
- RSS feed uniqueness constraint must be per-chat instead of global.
- Database migrations must be handled carefully to prevent data loss.
- Feed parsing errors should be handled gracefully without stopping the bot.
- Connection pooling is important for database performance.

## Pre-PR Checks
- Verify per-chat feed management works correctly
- Test RSS add/remove operations
- Confirm database migration functionality
- Check error handling for invalid feeds