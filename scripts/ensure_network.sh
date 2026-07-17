#!/usr/bin/env bash
set -euo pipefail

NETWORK_NAME="${1:-tg-monitoring_net}"

if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
  echo "Creating docker network: $NETWORK_NAME"
  docker network create "$NETWORK_NAME" >/dev/null
else
  echo "Docker network already exists: $NETWORK_NAME"
fi
