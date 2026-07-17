#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to the project directory
cd "$PROJECT_DIR"
mkdir -p logs

# Log the restart attempt
echo "$(date): Initiating daily restart of tg-monitoring" >> logs/daily-restart.log

# Perform the restart using the Makefile target
make daily-restart

# Log completion
echo "$(date): Completed daily restart attempt" >> logs/daily-restart.log
