# tgbot/modules/stickers Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the Stickers Agent responsible for handling sticker operations, particularly the /kang command for cloning stickers to user's sticker packs.

## Instructions:
- Handle /kang command requests for sticker cloning
- Interface with Telegram's sticker APIs to clone stickers
- Manage sticker pack creation and management
- Handle different sticker formats and types
- Coordinate with sticker services for core functionality
- Process replied sticker messages for cloning

## Project Context:
- Module responsible for sticker operations and cloning functionality
- Implements the Module interface from `tgbot/modules/base.py`
- Integrates with sticker services for core functionality
- Works with Telegram's sticker APIs

## Setup & Run
- Sticker functionality enabled via MODULES environment variable
- Uses /kang command to clone stickers to user's packs
- Processes replied sticker messages for cloning

## Patterns & Conventions
- ✅ DO follow the modular architecture: implement the Module interface.
- ✅ DO use Telegram's sticker APIs properly for cloning operations.
- ✅ Sticker operations should handle different formats appropriately.
- ✅ Use async/await patterns for API operations.
- ❌ DON'T violate Telegram's sticker policies or rate limits.
- ✅ Handle replied sticker messages gracefully.
- ✅ Implement proper error handling for API failures.

## Touch Points / Key Files
- Module implementation: `tgbot/modules/stickers/module.py`
- Sticker service: `tgbot/services/sticker_kang_service.py`
- Command handlers: `tgbot/services/sticker_kang_service.py` command functions
- API integration: Telegram sticker API calls in service

## JIT Index Hints
- `grep -n "def cmd_kang" tgbot/services/sticker_kang_service.py` – find kang command handler.
- `grep -n "sticker\|pack" tgbot/services/sticker_kang_service.py` – locate sticker operations.
- `grep -n "clone\|add" tgbot/services/sticker_kang_service.py` – find cloning logic.
- `grep -n "reply\|sticker" tgbot/services/sticker_kang_service.py` – inspect message processing.

## Subordinates (Hierarchy 2):
- Command Handler Agent (handles kang commands)
- Sticker Processor Agent (processes sticker operations)
- API Manager Agent (manages Telegram API calls)

## Common Gotchas
- Sticker cloning must comply with Telegram's terms and policies.
- Rate limits apply to sticker operations—implement appropriate delays.
- Different sticker formats (static, animated) may require different handling.
- Error handling is important for API failures and policy violations.

## Pre-PR Checks
- Verify /kang command works correctly for sticker cloning
- Test with different sticker formats
- Confirm compliance with Telegram's policies
- Check error handling for API limitations