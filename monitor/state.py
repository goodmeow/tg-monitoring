from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, Optional


class StateStore:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.data: Dict[str, Any] = {
            "last_update_id": None,
            "checks": {},  # key -> {status, consecutive, last_value, last_ts}
        }
        self._loaded = False
        self._ensure_dir()
        self.load()

    def _ensure_dir(self):
        d = os.path.dirname(self.path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def load(self):
        with self.lock:
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                    self._loaded = True
            except FileNotFoundError:
                self._loaded = True
            except Exception:
                # keep defaults on error
                self._loaded = True

    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)

    def get_check(self, key: str) -> Dict[str, Any]:
        with self.lock:
            checks = self.data.setdefault("checks", {})
            return dict(checks.get(key) or {})

    def set_check(self, key: str, value: Dict[str, Any]):
        with self.lock:
            checks = self.data.setdefault("checks", {})
            checks[key] = value

    def iter_checks(self):
        with self.lock:
            for k, v in (self.data.get("checks") or {}).items():
                yield k, dict(v)

    def set_last_update_id(self, update_id: Optional[int]):
        with self.lock:
            self.data["last_update_id"] = update_id

    def get_last_update_id(self) -> Optional[int]:
        with self.lock:
            return self.data.get("last_update_id")

