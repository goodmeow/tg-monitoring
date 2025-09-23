#!/usr/bin/env python3
"""
Test script for RSS add/remove functionality
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

async def test_rss_add_remove():
    """Test RSS add/remove functionality with duplicate detection."""
    print("Testing RSS add/remove functionality...")

    # Load config and initialize database
    config = load_config()
    db_manager = DatabaseManager(config)
    await db_manager.initialize()

    # Initialize RSS store
    rss_store = HybridRssStore(db_manager, config.rss_store_file)

    # Test chat ID
    test_chat_id = "-1001293932187"
    test_url = "https://example.com/test-feed.xml"

    try:
        print(f"Testing with chat {test_chat_id} and URL {test_url}")

        # Test 1: Get initial feeds
        print("\n1. Getting initial feeds...")
        initial_feeds = await rss_store.get_feeds(test_chat_id)
        print(f"   Initial feeds count: {len(initial_feeds)}")

        # Test 2: Add new feed
        print(f"\n2. Adding new feed: {test_url}")
        await rss_store.add_feed(test_chat_id, test_url)

        after_add_feeds = await rss_store.get_feeds(test_chat_id)
        print(f"   Feeds after add: {len(after_add_feeds)}")
        print(f"   Feed added: {test_url in after_add_feeds}")

        # Test 3: Try adding duplicate (should not increase count)
        print(f"\n3. Adding duplicate feed: {test_url}")
        await rss_store.add_feed(test_chat_id, test_url)

        after_duplicate_feeds = await rss_store.get_feeds(test_chat_id)
        print(f"   Feeds after duplicate: {len(after_duplicate_feeds)}")
        print(f"   Count unchanged: {len(after_add_feeds) == len(after_duplicate_feeds)}")

        # Test 4: Remove feed
        print(f"\n4. Removing feed: {test_url}")
        success = await rss_store.remove_feed(test_chat_id, test_url)

        after_remove_feeds = await rss_store.get_feeds(test_chat_id)
        print(f"   Remove success: {success}")
        print(f"   Feeds after remove: {len(after_remove_feeds)}")
        print(f"   Feed removed: {test_url not in after_remove_feeds}")

        # Test 5: Try removing non-existent feed
        print(f"\n5. Removing non-existent feed: {test_url}")
        success = await rss_store.remove_feed(test_chat_id, test_url)

        print(f"   Remove non-existent success: {success}")

        print("\n✅ All RSS add/remove tests passed!")

    except Exception as e:
        print(f"❌ RSS test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await db_manager.close()

    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(test_rss_add_remove()))