# tgbot/clients Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the External Clients Agent responsible for communicating with external services like Node Exporter and RSS feeds. I manage HTTP client interfaces for metrics collection and feed retrieval.

## Instructions:
- Handle HTTP requests to external services (Node Exporter, RSS feeds, etc.)
- Implement proper timeout handling for all HTTP requests
- Parse Prometheus metrics format following standard format specifications
- Fetch and parse RSS feeds from remote URLs in various formats
- Return domain objects rather than raw HTTP responses
- Handle network errors gracefully with appropriate logging
- Validate response formats before processing

## Project Context:
- External service client layer responsible for communicating with Node Exporter and RSS feeds.
- Provides HTTP client interfaces for metrics collection and feed retrieval.

## Setup & Run
- Node Exporter client fetches metrics from the configured endpoint.
- Feed client retrieves and parses RSS feeds from remote URLs.
- Both clients use httpx for async HTTP operations.

## Patterns & Conventions
- ✅ DO implement proper timeout handling for all HTTP requests.
- ✅ DO parse Prometheus metrics format in node_exporter.py following standard format.
- ✅ Clients should return domain objects rather than raw HTTP responses.
- ✅ Follow async/await patterns for all network operations.
- ❌ DON'T make blocking HTTP calls—always use async clients.
- ✅ Handle network errors gracefully with appropriate logging.
- ✅ Validate response formats before processing.

## Touch Points / Key Files
- Node Exporter metrics client: `tgbot/clients/node_exporter.py`
- RSS feed retrieval client: `tgbot/clients/feed_client.py`

## JIT Index Hints
- `grep -n "httpx" tgbot/clients/*.py` – find HTTP client usage.
- `grep -n "fetch" tgbot/clients/*.py` – locate data fetching methods.
- `grep -n "parse" tgbot/clients/node_exporter.py` – inspect metrics parsing.
- `grep -n "timeout" tgbot/clients/*.py` – review timeout configurations.

## Subordinates (Hierarchy 2):
- Node Exporter Client Agent (handles metrics retrieval)
- RSS Feed Client Agent (handles feed retrieval)
- HTTP Client Agent (handles generic HTTP operations)
- Response Parser Agent (handles response parsing)

## Common Gotchas
- Node Exporter client must parse Prometheus text format correctly—verify parsing logic.
- RSS feed client handles different feed formats (RSS, Atom)—test with various feed types.
- HTTP timeouts must be configured appropriately to avoid hanging requests.
- Network errors should be handled gracefully with fallback behaviors where appropriate.

## Pre-PR Checks
- Verify HTTP requests complete within timeout limits
- Test metrics parsing with various Prometheus formats
- Ensure RSS feed parsing works with different feed types