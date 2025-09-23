#!/usr/bin/env python3
"""
Simple test script to verify RSS store functionality
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tgbot.domain.config import load_config
from tgbot.core.database import DatabaseManager
from tgbot.stores.rss_store_v2 import HybridRssStore

async def test_rss_store():
    """Test basic RSS store operations."""
    print("Testing RSS store functionality...")

    # Load config and initialize database
    config = load_config()
    db_manager = DatabaseManager(config)
    await db_manager.initialize()

    # Initialize RSS store
    rss_store = HybridRssStore(db_manager, config.rss_store_file)

    # Test chat ID from migration
    test_chat_id = "-1001293932187"

    try:
        # Test get_feeds
        print(f"Testing get_feeds for chat {test_chat_id}...")
        feeds = await rss_store.get_feeds(test_chat_id)
        print(f"Found {len(feeds)} feeds: {feeds}")

        # Test get_pending_counts
        print(f"Testing get_pending_counts for chat {test_chat_id}...")
        counts = await rss_store.get_pending_counts(test_chat_id)
        print(f"Pending counts: {counts}")

        # Test get_last_digest
        print(f"Testing get_last_digest for chat {test_chat_id}...")
        last_digest = await rss_store.get_last_digest(test_chat_id)
        print(f"Last digest timestamp: {last_digest}")

        print("✅ All RSS store tests passed!")

    except Exception as e:
        print(f"❌ RSS store test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(test_rss_store())