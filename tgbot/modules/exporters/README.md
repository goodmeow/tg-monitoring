# Node Exporters Module

Provides flexible node metrics collection via Docker or Native Python implementation.

## Features

- ✅ **Auto-detection** - Automatically selects Docker or Python based on availability
- ✅ **100% Compatible** - Drop-in replacement, no existing code changes required
- ✅ **Async Support** - Full async/await implementation
- ✅ **Same Port (9100)** - Compatible with existing setup

## Configuration

Set environment variable in `.env`:

```bash
# Auto-detect (default, prefers Docker if available)
NODE_EXPORTER_TYPE=auto

# Force Docker exporter
NODE_EXPORTER_TYPE=docker  

# Force Python exporter
NODE_EXPORTER_TYPE=python
```

## Usage

### Basic Usage

```python
from tgbot.modules.exporters import create_exporter, ExporterType

# Auto-select best available
exporter = create_exporter()

# Or specify type
exporter = create_exporter(ExporterType.DOCKER)
exporter = create_exporter(ExporterType.PYTHON)

# Start exporter
await exporter.start()

# Check status
status = exporter.status()
print(f"Running: {status['running']}")
print(f"Type: {status['type']}")
print(f"URL: {status['metrics_url']}")

# Health check
if await exporter.health_check():
    print("Exporter is healthy")

# Stop when done
await exporter.stop()
```

### Check Available Exporters

```python
from tgbot.modules.exporters import get_available_exporters

available = get_available_exporters()
print(f"Docker available: {available['docker']}")
print(f"Python available: {available['python']}")
```

### Switch Between Exporters

```python
from tgbot.modules.exporters import switch_exporter, ExporterType

# Switch to Python exporter
await switch_exporter(ExporterType.PYTHON)

# Switch to Docker exporter
await switch_exporter(ExporterType.DOCKER)
```

## Structure

```
exporters/
├── __init__.py         # Module exports
├── base.py            # Base class and types
├── factory.py         # Factory pattern implementation
├── docker/
│   ├── __init__.py
│   └── exporter.py    # Docker wrapper
└── python/
    ├── __init__.py
    ├── exporter.py    # Python implementation
    ├── standalone_script.py  # Script template
    └── metrics_collector.py  # Metrics utilities
```

## Docker Exporter

- Uses existing `node-exporter` container
- Manages container lifecycle (start/stop)
- Compatible with existing Docker setup

## Python Exporter  

- Pure Python implementation using `psutil`
- Runs as subprocess
- No Docker dependency required
- Requires: `prometheus-client`, `psutil`, `flask`

## Testing

Run test script from project root:

```bash
source .venv/bin/activate
python test_exporters.py
```

## Integration with Bot

Currently the bot expects node exporter to be running on port 9100.

To manually ensure exporter is running:

```bash
# For Docker
docker start node-exporter

# For Python (if Docker not available)
export NODE_EXPORTER_TYPE=python
# Then restart bot
```

## Requirements

### For Docker Exporter
- Docker installed and running
- Permission to manage Docker containers

### For Python Exporter
```
prometheus-client>=0.20.0
psutil>=5.9.0
flask>=3.0.0
```

## Notes

- Both exporters provide identical metrics format
- Metrics available at `http://127.0.0.1:9100/metrics`
- Compatible with Prometheus scraping
- No changes needed in existing bot code
