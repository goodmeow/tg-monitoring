"""Regression tests for the audit fixes; run with python -m unittest discover -s tests."""

import json
import os
import tempfile
import unittest

from tgbot.domain.config import Config
from tgbot.services.monitoring_service import _compose_changes_message_html
from tgbot.services.rss_service import RssService, _compose_rss_digest_html
from tgbot.stores.state_store_v2 import HybridStateStore


def _cfg(**overrides) -> Config:
    return Config(bot_token="test", chat_id="1", **overrides)


class FakeRssStore:
    def __init__(self, pending):
        self.pending = pending
        self.acked = None
        self.last_digest = None
        self.saves = 0

    async def get_pending_digest(self, chat_id):
        return self.pending

    async def remove_pending_items(self, chat_id, delivered):
        self.acked = delivered

    async def set_last_digest(self, chat_id, ts):
        self.last_digest = ts

    async def save(self):
        self.saves += 1


class RecordingBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append(text)


class FailingBot:
    async def send_message(self, chat_id, text, **kwargs):
        raise RuntimeError("telegram is down")


def _items(count):
    return [
        {
            "id": f"id{i}",
            "title": f"title {i}",
            "link": f"https://example.com/{i}",
            "published_ts": 1000 - i,
            "description": "",
        }
        for i in range(count)
    ]


class DigestDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_send_keeps_items_pending(self):
        pending = {"https://example.com/feed": _items(1)}
        store = FakeRssStore(pending)
        service = RssService(cfg=_cfg(), rss=store, client=None)

        with self.assertRaises(RuntimeError):
            await service.send_digest(FailingBot(), 1, "host", 12345.0)

        self.assertIsNone(store.acked)
        self.assertIsNone(store.last_digest)

    async def test_success_acks_only_sent_items(self):
        pending = {"https://example.com/feed": _items(3)}
        store = FakeRssStore(pending)
        service = RssService(cfg=_cfg(), rss=store, client=None)
        bot = RecordingBot()

        await service.send_digest(bot, 1, "host", 12345.0)

        self.assertEqual(store.acked, {"https://example.com/feed": ["id0", "id1", "id2"]})
        self.assertEqual(store.last_digest, 12345.0)
        self.assertEqual(store.saves, 1)
        self.assertEqual(len(bot.messages), 1)

    async def test_cap_overflow_is_deferred(self):
        cfg = _cfg(rss_digest_max_total=2, rss_digest_items_per_feed=5)
        pending = {"https://example.com/feed": _items(5)}

        message, delivered = _compose_rss_digest_html("host", pending, cfg)

        self.assertEqual(delivered, {"https://example.com/feed": ["id0", "id1"]})
        self.assertIn("3 items deferred to the next digest", message)


class StatePersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_json_state_is_flushed_by_save(self):
        class StubDatabase:
            is_available = False

        path = tempfile.mktemp(suffix=".json")
        try:
            store = HybridStateStore(StubDatabase(), path)
            await store.set_check("disk:/", {"status": "alert"})
            await store.save()

            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["checks:disk:/"], {"status": "alert"})
        finally:
            if os.path.exists(path):
                os.unlink(path)


class DiskAlertTests(unittest.TestCase):
    def test_alert_uses_measured_disk_fraction(self):
        entry = {
            "type": "disk",
            "status": "alert",
            "value": 1.0,
            "meta": {"by_mount": [{"mount": "/", "value": 0.86, "device": "/dev/sda1"}]},
            "message": "/ used 86%",
        }

        message = _compose_changes_message_html([("ALERT", entry)], "host")

        self.assertIn("/: 86%", message)
        self.assertNotIn("100%", message)


if __name__ == "__main__":
    unittest.main()
