# tgbot/modules/qrcode Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the QR Code Agent responsible for generating QR codes from text or replied messages using the /qrcode command.

## Instructions:
- Handle /qrcode command requests from users
- Generate QR codes from provided text or replied messages
- Format QR codes as images for Telegram transmission
- Handle error cases when text is missing or invalid
- Coordinate with qrcode services for image generation
- Process replied messages when no direct text is provided

## Project Context:
- Module responsible for QR code generation functionality
- Implements the Module interface from `tgbot/modules/base.py`
- Uses Pillow library for image generation
- Integrates with qrcode services for core functionality

## Setup & Run
- QR code functionality enabled via MODULES environment variable
- Uses /qrcode command to generate QR codes from text
- Can process replied messages when no text is provided

## Patterns & Conventions
- ✅ DO follow the modular architecture: implement the Module interface.
- ✅ DO use Pillow library for image generation.
- ✅ QR codes should be properly sized for Telegram transmission.
- ✅ Use async/await patterns for command handlers.
- ❌ DON'T create oversized images that exceed Telegram limits.
- ✅ Handle replied messages gracefully when no direct text provided.
- ✅ Implement proper error handling for invalid input.

## Touch Points / Key Files
- Module implementation: `tgbot/modules/qrcode/module.py`
- QR code service: `tgbot/services/qrcode_service.py`
- Command handlers: `tgbot/services/qrcode_service.py` command functions
- Image generation: Pillow library integration in service

## JIT Index Hints
- `grep -n "def cmd_qrcode" tgbot/services/qrcode_service.py` – find qrcode command handler.
- `grep -n "Pillow\|Image" tgbot/services/qrcode_service.py` – locate image generation.
- `grep -n "qr\|qrcode" tgbot/services/qrcode_service.py` – find qrcode logic.
- `grep -n "reply\|message" tgbot/services/qrcode_service.py` – inspect message processing.

## Subordinates (Hierarchy 2):
- Command Handler Agent (handles qrcode commands)
- Image Generator Agent (generates QR code images)
- Message Processor Agent (processes replied messages)

## Common Gotchas
- QR code images must be within Telegram's size limits.
- Reply message processing requires proper message context.
- Image generation should be efficient to maintain responsiveness.
- Error handling is important for invalid input cases.

## Pre-PR Checks
- Verify /qrcode command generates proper QR codes
- Test with both direct text and replied messages
- Confirm image sizes are appropriate for Telegram
- Check error handling for invalid input