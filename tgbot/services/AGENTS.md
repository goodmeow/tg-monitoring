# tgbot/services Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the Business Services Agent responsible for implementing the core business logic for monitoring, RSS feeds, help commands, and other features. I act as the bridge between modules (command handlers) and data stores/clients.

## Instructions:
- Implement business logic for specific domains (monitoring, RSS, help, etc.)
- Handle command processing and business operations
- Format messages for Telegram using proper HTML parsing
- Manage state tracking for monitoring and alerting systems
- Handle async operations with proper error handling and timeouts
- Implement proper command registration via routers
- Ensure consistent message formatting across all services

## Project Context:
- Service layer containing business logic for monitoring, RSS feeds, help commands, and other features.
- Acts as the bridge between modules (command handlers) and data stores/clients.

## Setup & Run
- Services are initialized by modules during application startup.
- Background monitoring loop runs via `monitoring_service.py`.
- RSS service handles feed polling and notifications via `rss_service.py`.

## Patterns & Conventions
- ✅ DO implement command handlers using aiogram Router pattern as shown in service files.
- ✅ DO handle async operations properly with proper error handling and timeouts.
- ✅ Services should format messages for Telegram using HTML parsing where appropriate.
- ✅ Follow the pattern of returning routers from service methods for command registration.
- ❌ DON'T perform blocking operations in command handlers—use async alternatives.
- ✅ Implement proper state tracking for monitoring and alerting.
- ✅ Use consistent message formatting across all services.

## Touch Points / Key Files
- Server monitoring business logic: `tgbot/services/monitoring_service.py`
- RSS feed management logic: `tgbot/services/rss_service.py`
- Help command logic: `tgbot/services/help_service.py`
- QR code generation logic: `tgbot/services/qrcode_service.py`

## JIT Index Hints
- `grep -n "def build_router" tgbot/services/*.py` – find command registration methods.
- `grep -n "async def cmd_" tgbot/services/*.py` – inspect command handlers.
- `grep -n "run_loop" tgbot/services/monitoring_service.py` – locate monitoring loop.
- `grep -n "compose_" tgbot/services/monitoring_service.py` – find message formatting.

## Subordinates (Hierarchy 2):
- Monitoring Service Agent (handles server monitoring logic)
- RSS Service Agent (handles RSS feed management)
- Help Service Agent (handles help command logic)
- QR Code Service Agent (handles QR code generation)
- Sticker Service Agent (handles sticker operations)

## Common Gotchas
- The monitoring service tracks consecutive alert states—verify state transitions work correctly.
- RSS service handles per-chat feed management—ensure chat isolation works properly.
- Message formatting for HTML parsing requires proper escaping of special characters.
- Background tasks must handle exceptions gracefully to avoid stopping the bot.

## Pre-PR Checks
- Test all implemented commands to ensure they work correctly
- Verify message formatting renders properly in Telegram
- Check that background services handle errors gracefully