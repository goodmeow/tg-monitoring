from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional


class RssStore:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.data: Dict[str, Any] = {
            "chats": {},  # chat_id -> { feeds: [url], last_digest_ts: float, pending: {url: [items]} }
            "feeds_meta": {},  # url -> { etag, last_modified, seen_ids: [] }
        }
        self._ensure_dir()
        self.load()

    def _ensure_dir(self):
        d = os.path.dirname(self.path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except FileNotFoundError:
            pass
        except Exception:
            pass

    def save(self):
        tmp = self.path + ".tmp"
        with self.lock:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)

    # Chat subscriptions
    def add_feed(self, chat_id: int | str, url: str):
        cid = str(chat_id)
        with self.lock:
            chat = self.data.setdefault("chats", {}).setdefault(
                cid, {"feeds": [], "last_digest_ts": 0.0, "pending": {}}
            )
            if url not in chat["feeds"]:
                chat["feeds"].append(url)
            self.data.setdefault("feeds_meta", {}).setdefault(
                url, {"etag": None, "last_modified": None, "seen_ids": []}
            )

    def remove_feed(self, chat_id: int | str, url: str):
        cid = str(chat_id)
        with self.lock:
            chat = self.data.setdefault("chats", {}).setdefault(
                cid, {"feeds": [], "last_digest_ts": 0.0, "pending": {}}
            )
            if url in chat["feeds"]:
                chat["feeds"].remove(url)
            # also clear pending for this feed
            chat.get("pending", {}).pop(url, None)

    def list_feeds(self, chat_id: int | str) -> List[str]:
        cid = str(chat_id)
        with self.lock:
            chat = self.data.get("chats", {}).get(cid) or {}
            return list(chat.get("feeds") or [])

    def all_feeds(self) -> List[str]:
        urls: List[str] = []
        with self.lock:
            for chat in (self.data.get("chats") or {}).values():
                for u in chat.get("feeds") or []:
                    urls.append(u)
        # dedupe, preserve order
        seen = set()
        out: List[str] = []
        for u in urls:
            if u not in seen:
                out.append(u)
                seen.add(u)
        return out

    def subscribers(self, url: str) -> List[str]:
        subs: List[str] = []
        with self.lock:
            for cid, chat in (self.data.get("chats") or {}).items():
                if url in (chat.get("feeds") or []):
                    subs.append(cid)
        return subs

    # Pending items per chat
    def add_pending_item(self, chat_id: int | str, url: str, item: Dict[str, Any]):
        cid = str(chat_id)
        with self.lock:
            chat = self.data.setdefault("chats", {}).setdefault(
                cid, {"feeds": [], "last_digest_ts": 0.0, "pending": {}}
            )
            pend = chat.setdefault("pending", {}).setdefault(url, [])
            # avoid duplicates in pending by id
            iid = item.get("id")
            if iid and any(x.get("id") == iid for x in pend):
                return
            pend.append(item)

    def pop_pending_digest(self, chat_id: int | str) -> Dict[str, List[Dict[str, Any]]]:
        cid = str(chat_id)
        with self.lock:
            chat = self.data.setdefault("chats", {}).setdefault(
                cid, {"feeds": [], "last_digest_ts": 0.0, "pending": {}}
            )
            pending = chat.get("pending") or {}
            chat["pending"] = {}
            return pending

    def get_pending_counts(self, chat_id: int | str) -> Dict[str, int]:
        cid = str(chat_id)
        with self.lock:
            chat = self.data.get("chats", {}).get(cid) or {}
            pend = chat.get("pending") or {}
            return {u: len(items or []) for u, items in pend.items()}

    def get_chat(self, chat_id: int | str) -> Dict[str, Any]:
        cid = str(chat_id)
        with self.lock:
            return dict(self.data.get("chats", {}).get(cid) or {})

    def set_last_digest(self, chat_id: int | str, ts: float):
        cid = str(chat_id)
        with self.lock:
            chat = self.data.setdefault("chats", {}).setdefault(
                cid, {"feeds": [], "last_digest_ts": 0.0, "pending": {}}
            )
            chat["last_digest_ts"] = ts

    def get_last_digest(self, chat_id: int | str) -> float:
        cid = str(chat_id)
        with self.lock:
            chat = self.data.get("chats", {}).get(cid) or {}
            return float(chat.get("last_digest_ts") or 0.0)

    # Feed metadata
    def get_feed_meta(self, url: str) -> Dict[str, Any]:
        with self.lock:
            return dict(
                (
                    self.data.setdefault("feeds_meta", {}).setdefault(
                        url, {"etag": None, "last_modified": None, "seen_ids": []}
                    )
                )
            )

    def update_feed_meta(self, url: str, etag: Optional[str], last_modified: Optional[str]):
        with self.lock:
            meta = self.data.setdefault("feeds_meta", {}).setdefault(
                url, {"etag": None, "last_modified": None, "seen_ids": []}
            )
            if etag is not None:
                meta["etag"] = etag
            if last_modified is not None:
                meta["last_modified"] = last_modified

    def add_seen_id(self, url: str, iid: str, max_keep: int = 200):
        with self.lock:
            meta = self.data.setdefault("feeds_meta", {}).setdefault(
                url, {"etag": None, "last_modified": None, "seen_ids": []}
            )
            seen = meta.setdefault("seen_ids", [])
            if iid in seen:
                return
            seen.append(iid)
            if len(seen) > max_keep:
                # keep tail
                meta["seen_ids"] = seen[-max_keep:]

