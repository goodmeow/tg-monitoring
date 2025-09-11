from __future__ import annotations

import json
import time
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class TelegramClient:
    def __init__(self, bot_token: str, timeout_sec: int = 8):
        self.bot_token = bot_token
        self.base = f"https://api.telegram.org/bot{bot_token}"
        self.timeout_sec = timeout_sec

    def _post(self, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        body = urllib.parse.urlencode(data).encode()
        req = Request(
            f"{self.base}/{method}",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "tg-monitor/1.0",
            },
        )
        with urlopen(req, timeout=self.timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except Exception:
            return {"ok": False, "error": "invalid_json", "raw": raw}

    def _get(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        qs = urllib.parse.urlencode(params)
        url = f"{self.base}/{method}?{qs}"
        req = Request(url, headers={"User-Agent": "tg-monitor/1.0"})
        with urlopen(req, timeout=self.timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except Exception:
            return {"ok": False, "error": "invalid_json", "raw": raw}

    def send_message(self, chat_id: str | int, text: str, disable_web_page_preview: bool = True) -> bool:
        try:
            res = self._post(
                "sendMessage",
                {
                    "chat_id": str(chat_id),
                    "text": text,
                    "disable_web_page_preview": "true" if disable_web_page_preview else "false",
                },
            )
            return bool(res.get("ok"))
        except (HTTPError, URLError):
            return False

    def get_updates(self, offset: Optional[int], timeout: int = 50, allowed_updates: Optional[List[str]] = None) -> Dict[str, Any]:
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        if allowed_updates:
            params["allowed_updates"] = json.dumps(allowed_updates)
        try:
            return self._get("getUpdates", params)
        except (HTTPError, URLError) as e:
            return {"ok": False, "error": str(e)}

