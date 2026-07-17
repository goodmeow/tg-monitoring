# tgbot/modules/help Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the Help Agent responsible for providing user assistance through /help command and inline keyboards with quick action buttons.

## Instructions:
- Handle /help command requests from users
- Generate inline keyboards with quick action buttons (Status, RSS List)
- Provide contextual help information based on available modules
- Format help messages in a user-friendly way
- Maintain consistent UI/UX for help interactions
- Coordinate with other agents to provide accurate feature descriptions

## Project Context:
- Module responsible for help and user assistance functionality
- Implements the Module interface from `tgbot/modules/base.py`
- Integrates with help services to provide contextual information
- Works with aiogram's inline keyboard system

## Setup & Run
- Help functionality enabled via MODULES environment variable
- Responds to /help command with inline menu options
- Integrates with other modules to provide comprehensive help

## Patterns & Conventions
- ✅ DO follow the modular architecture: implement the Module interface.
- ✅ DO use aiogram's inline keyboard system for help menus.
- ✅ Help messages should be clear and concise.
- ✅ Use async/await patterns for command handlers.
- ❌ DON'T provide outdated information about features.
- ✅ Maintain consistent formatting for help messages.
- ✅ Provide appropriate buttons for quick actions.

## Touch Points / Key Files
- Module implementation: `tgbot/modules/help/module.py`
- Help service: `tgbot/services/help_service.py`
- Command handlers: `tgbot/services/help_service.py` command functions
- Inline keyboards: `tgbot/services/help_service.py` keyboard functions

## JIT Index Hints
- `grep -n "def cmd_help" tgbot/services/help_service.py` – find help command handler.
- `grep -n "inline\|keyboard" tgbot/services/help_service.py` – locate keyboard creation.
- `grep -n "button\|menu" tgbot/services/help_service.py` – find button definitions.
- `grep -n "help\|assist" tgbot/modules/help/module.py` – inspect module integration.

## Subordinates (Hierarchy 2):
- Command Handler Agent (handles help commands)
- UI Formatter Agent (formats help interfaces)
- Context Provider Agent (provides contextual information)

## Common Gotchas
- Help commands must be responsive and fast to maintain good UX.
- Inline keyboards should be properly formatted and functional.
- Help information must be kept up-to-date with current features.
- Button callbacks need to be properly registered and handled.

## Pre-PR Checks
- Verify /help command works correctly
- Test inline keyboard functionality
- Confirm all help options are functional
- Check that help information matches current features