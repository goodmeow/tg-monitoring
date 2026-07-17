# tgbot/modules/exporters Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the Exporters Agent responsible for flexible metrics collection using Docker or Python-based exporters with auto-detection capabilities.

## Instructions:
- Auto-detect the best available exporter (Docker preferred)
- Manage Docker-based node-exporter container
- Implement Python-based metrics collection using psutil
- Ensure 100% compatibility between both exporter types
- Provide identical Prometheus metrics format regardless of exporter type
- Perform health checks on the metrics collection system
- Handle configuration based on NODE_EXPORTER_TYPE setting
- Maintain system metrics collection reliability

## Project Context:
- Module responsible for flexible metrics collection
- Implements the Module interface from `tgbot/modules/base.py`
- Supports auto-detection (auto/docker/python) via NODE_EXPORTER_TYPE
- Provides identical metrics format regardless of implementation

## Setup & Run
- Exporter type selected via NODE_EXPORTER_TYPE environment variable (auto/docker/python)
- Docker exporter requires Docker to be installed and running
- Python exporter requires psutil library for system metrics
- Auto-detection prioritizes Docker when available

## Patterns & Conventions
- ✅ DO maintain identical Prometheus metrics format across implementations.
- ✅ DO implement the exporter factory pattern for auto-detection.
- ✅ Exporters should provide health checks to verify availability.
- ✅ Follow async patterns for all exporter operations.
- ❌ DON'T break metrics compatibility between different exporter types.
- ✅ Implement proper cleanup in exporter shutdown procedures.
- ✅ Use the base exporter interface for consistency.

## Touch Points / Key Files
- Exporter factory and selection: `tgbot/modules/exporters/factory.py`
- Base exporter interface: `tgbot/modules/exporters/base.py`
- Docker exporter implementation: `tgbot/modules/exporters/docker/`
- Python exporter implementation: `tgbot/modules/exporters/python/`
- Exporter module integration: `tgbot/modules/exporters/module.py`

## JIT Index Hints
- `grep -n "class.*Exporter" tgbot/modules/exporters/*.py` – find exporter implementations.
- `grep -n "def create_exporter" tgbot/modules/exporters/factory.py` – locate factory logic.
- `grep -n "fetch_stats" tgbot/modules/exporters/*/*.py` – inspect metrics collection.
- `grep -n "docker\|python\|psutil" tgbot/modules/exporters/*/*.py` – find implementation specifics.

## Subordinates (Hierarchy 2):
- Docker Exporter Agent (handles Docker-based metrics)
- Python Exporter Agent (handles Python-based metrics)
- Health Check Agent (performs health validation)
- Auto-Detection Agent (determines best exporter)

## Common Gotchas
- Auto-detection logic prioritizes Docker exporter when available.
- Python exporter requires psutil library – verify dependencies are available.
- Metrics format must be identical between implementations – test compatibility carefully.
- Docker exporter needs proper permissions to manage containers – verify Docker setup.

## Pre-PR Checks
- Test auto-detection works correctly in different environments
- Verify metrics format is identical between exporter types
- Ensure both exporters provide the same functionality
- Check that exporter selection respects the NODE_EXPORTER_TYPE setting