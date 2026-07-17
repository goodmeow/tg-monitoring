# tgbot/modules/monitoring Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the System Monitoring Agent responsible for collecting and analyzing system metrics from Node Exporter, including CPU, memory, disk usage, and other system resources.

## Instructions:
- Scrape metrics from http://127.0.0.1:9100/metrics (Node Exporter)
- Evaluate CPU, memory, and disk thresholds
- Monitor system load and performance metrics
- Report system status to the base agent (0-AGENTS.md)
- Detect anomalies or threshold breaches
- Track state changes for alerting purposes
- Collect metrics at configured intervals

## Project Context:
- Module responsible for system monitoring functionality
- Implements the Module interface from `tgbot/modules/base.py`
- Uses configuration from `tgbot/domain/config.py`
- Integrates with monitoring services and state stores

## Setup & Run
- Monitored via the `SAMPLE_INTERVAL_SEC` environment variable (default: 15 seconds)
- Thresholds configured via `CPU_LOAD_PER_CORE_WARN`, `MEM_AVAILABLE_PCT_WARN`, `DISK_USAGE_PCT_WARN`
- State changes trigger ALERT/RECOVERED notifications to Telegram

## Patterns & Conventions
- ✅ DO follow the modular architecture: implement the Module interface.
- ✅ DO respect the configured sample interval for metrics collection.
- ✅ Monitor only sends alerts on state changes (ALERT/RECOVERED pattern).
- ✅ Use async/await patterns for metrics collection.
- ❌ DON'T send duplicate alerts for the same issue.
- ✅ Follow threshold configuration from environment variables.
- ✅ Maintain state tracking between checks to detect changes.

## Touch Points / Key Files
- Module implementation: `tgbot/modules/monitoring/module.py`
- Monitoring service: `tgbot/services/monitoring_service.py`
- Configuration: `tgbot/domain/config.py`
- State stores: `tgbot/stores/` for persistence
- Node Exporter client: `tgbot/clients/node_exporter_client.py` (if exists)

## JIT Index Hints
- `grep -n "cpu\|memory\|disk" tgbot/modules/monitoring/module.py` – find resource monitoring.
- `grep -n "ALERT\|RECOVERED" tgbot/services/monitoring_service.py` – locate alert logic.
- `grep -n "threshold\|warn" tgbot/domain/config.py` – inspect threshold settings.
- `grep -n "state\|change" tgbot/stores/` – find state tracking mechanisms.

## Subordinates (Hierarchy 2):
- CPU Monitoring Agent (handles CPU metrics)
- Memory Monitoring Agent (handles memory metrics) 
- Disk Monitoring Agent (handles disk metrics)
- Network Monitoring Agent (handles network metrics)

## Common Gotchas
- The bot only sends alerts on state changes, not continuously.
- Thresholds are configurable via environment variables.
- State persistence helps track changes between checks.
- Must respect the ALERT_MIN_CONSECUTIVE setting for alert filtering.

## Pre-PR Checks
- Verify alert thresholds work correctly
- Test both ALERT and RECOVERED states
- Confirm proper state tracking between metrics checks