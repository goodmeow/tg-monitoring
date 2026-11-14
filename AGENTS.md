# tg-monitoring Hierarchical Agent System

## Hierarchy: 0 (Base Agent)

## Role:
I am the Base Agent, the root of the hierarchical agent system for tg-monitoring. I coordinate all activities within the tg-monitoring system and delegate tasks to lower hierarchy agents when needed.

## Instructions:
- Monitor the overall state of the tg-monitoring system
- Coordinate with sub-agents (hierarchy 1) for specific tasks
- Delegate monitoring tasks to specialized agents when thresholds are reached
- Generate reports on system status
- Handle high-level decision making
- Provide overall system coordination and communication

## Project Context:
- Simple single-app repo: Python Telegram bot for server monitoring with modular architecture under `tgbot/`, data stores, external clients, and configuration systems.
- Python 3.10+ with aiogram 3.31 and aiohttp 3.14 (pinned in `requirements.txt`); PostgreSQL optional with JSON fallback.
- Runtime image is `python:3.11-alpine`; deployed with Docker Compose via the `tg-monitor.service` systemd unit.
- Regression tests use stdlib `unittest` under `tests/`.
- Each major directory ships its own `AGENTS.md`; hierarchy follows 0-AGENTS.md (base), 1-*.md (sub-agents), 2-*.md (sub-sub-agents), etc.

## Root Setup Commands
- `make build` – build the bot image with Docker Compose, baking the `git describe` version.
- `make up` – enable and start the systemd unit (Compose stack).
- `make status` – show the systemd unit status.
- `make logs` – follow the bot container logs.
- `make restart` – restart the systemd unit.
- `make down` – stop the Compose stack.
- `make full-stop` – stop the stack and disable the watchdog.
- `python -m tgbot.main` – run the bot directly in foreground.
- `python3 -m unittest discover -s tests` – run the regression tests.

## Universal Conventions
- Python + aiogram framework with async/await patterns, 4-space indent, imports ordered standard library → third-party → local.
- Configuration via environment variables and .env files; use the config system from `tgbot/domain/config.py`.
- Keep modules organized in the modular architecture pattern; new features as separate modules.
- Commits should be descriptive and include references to related functionality; include testing steps for new features.

## Security & Secrets
- Never commit API keys or tokens; reference `.env.example` and keep secrets in `.env` or environment variables.
- Bot credentials surface via `bot_token` and `chat_id` environment variables; treat them as secrets.
- Database credentials should be in environment variables when using PostgreSQL; never hardcode them.
- `.dockerignore` keeps `.env*`, `data/`, `logs/`, `.git`, and caches out of the image; never remove those entries.
- Scan a built image with `docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image tg-monitoring-tg-monitoring:latest`.
- SonarCloud analysis runs in CI via `.github/workflows/sonar.yml` and needs the `SONAR_TOKEN` repository secret; project settings live in `sonar-project.properties`.

### SonarCloud Notes
- The free tier applies only while this repository stays public; private repos need a paid plan and consume GitHub Actions minutes.
- CI prerequisites: add the `SONAR_TOKEN` repository secret, then turn off **Automatic Analysis** (project → Administration → Analysis Method). CI and local scans are rejected while it is on.
- Local scanning uses `sonar-scanner` with the repository `sonar-project.properties`; pass the token through `SONAR_TOKEN`, never through the file or a commit.
- Pull requests from forks do not receive repository secrets, so the scan workflow does not run for them.

## Subordinates (Hierarchy 1):
- System Monitoring Agent (handles node_exporter metrics)
- Notification Agent (handles Telegram alerts)
- Data Storage Agent (handles PostgreSQL/JSON storage)
- RSS Management Agent (handles RSS feeds)
- Exporters Agent (handles metrics collection)

## JIT Index (what to open, not what to paste)

### Directory Map
- Main application: `tgbot/` → [see tgbot/AGENTS.md](tgbot/AGENTS.md)
- Core framework: `tgbot/core/` → [see tgbot/core/AGENTS.md](tgbot/core/AGENTS.md)
- Domain logic: `tgbot/domain/` → [see tgbot/domain/AGENTS.md](tgbot/domain/AGENTS.md)
- Feature modules: `tgbot/modules/` → [see tgbot/modules/AGENTS.md](tgbot/modules/AGENTS.md)
- Business services: `tgbot/services/` → [see tgbot/services/AGENTS.md](tgbot/services/AGENTS.md)
- Data stores: `tgbot/stores/` → [see tgbot/stores/AGENTS.md](tgbot/stores/AGENTS.md)
- External clients: `tgbot/clients/` → [see tgbot/clients/AGENTS.md](tgbot/clients/AGENTS.md)
- Exporters module: `tgbot/modules/exporters/` → [see tgbot/modules/exporters/AGENTS.md](tgbot/modules/exporters/AGENTS.md)

### Quick Find Commands
- `grep -r "class.*Module" tgbot/modules` – enumerate module implementations.
- `grep -r "async def cmd" tgbot/services` – inspect command handlers.
- `grep -r "Router()" tgbot/services` – find route registrations.
- `grep -r "fetch_stats" tgbot/clients` – review metrics fetching.
- `grep -r "DATABASE_URL" tgbot` – locate database configuration usage.

## Definition of Done
- `make up` or `python -m tgbot.main` starts without errors; address any startup errors.
- Basic commands like `/status` work correctly in testing.
- `python3 -m unittest discover -s tests` passes.
- Rebuild (`make build`) after Dockerfile or dependency changes; Trivy reports no fixable CVEs.
- Update relevant `AGENTS.md` entries when adding patterns or commands.
- Verify both PostgreSQL and JSON storage backends work if relevant.