from __future__ import annotations

import os
import subprocess


def get_version() -> str:
    env_override = os.environ.get("TG_MONITOR_VERSION")
    if env_override:
        return env_override
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            check=True,
            capture_output=True,
            text=True,
        )
        version = result.stdout.strip()
        if version:
            return version
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        sha = result.stdout.strip()
        if sha:
            return sha
    except Exception:
        pass
    return "unknown"

