from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _shorten(sha: str) -> str:
    return sha[:7] if len(sha) > 7 else sha


def _read_head_commit() -> str | None:
    git_dir = Path('.git')
    head_path = git_dir / 'HEAD'
    if not head_path.exists():
        return None
    try:
        head = head_path.read_text().strip()
    except OSError:
        return None

    if head.startswith('ref:'):
        ref = head.split(' ', 1)[1].strip()
        ref_path = git_dir / ref
        if ref_path.exists():
            try:
                ref_sha = ref_path.read_text().strip()
            except OSError:
                ref_sha = ''
            if ref_sha:
                return _shorten(ref_sha)
        packed_refs = git_dir / 'packed-refs'
        if packed_refs.exists():
            try:
                for line in packed_refs.read_text().splitlines():
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('^'):
                        continue
                    sha, name = line.split(' ', 1)
                    if name.strip() == ref:
                        return _shorten(sha)
            except OSError:
                return None
        return None
    return _shorten(head) if head else None


def get_version() -> str:
    env_override = os.environ.get('TG_MONITOR_VERSION')
    if env_override:
        return env_override
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--always', '--dirty'],
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
            ['git', 'rev-parse', '--short', 'HEAD'],
            check=True,
            capture_output=True,
            text=True,
        )
        sha = result.stdout.strip()
        if sha:
            return sha
    except Exception:
        pass
    head_sha = _read_head_commit()
    if head_sha:
        return head_sha
    return 'unknown'
