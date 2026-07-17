#!/usr/bin/env python3
"""
RSS Data Migration Script: JSON to PostgreSQL

This script migrates existing RSS data from the legacy JSON format
to the new PostgreSQL database structure.

Usage:
    python scripts/migrate_rss_to_postgres.py [--dry-run] [--json-path data/rss.json]
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from typing import Any, Dict, List
import logging

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tgbot.core.database import DatabaseManager
from tgbot.stores.rss_store_v2 import PostgreSQLRssStore
from tgbot.domain.config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RSSDataMigrator:
    """Handles migration of RSS data from JSON to PostgreSQL."""

    def __init__(self, db_manager: DatabaseManager, dry_run: bool = False):
        self.db_manager = db_manager
        self.pg_store = PostgreSQLRssStore(db_manager)
        self.dry_run = dry_run

    async def migrate(self, json_data: Dict[str, Any]) -> None:
        """Main migration method."""
        logger.info(f"Starting RSS migration (dry_run={self.dry_run})")

        if not self.db_manager.is_available:
            raise RuntimeError("Database is not available")

        # Extract data sections
        chats_data = json_data.get("chats", {})
        feeds_meta = json_data.get("feeds_meta", {})

        logger.info(f"Found {len(chats_data)} chats with RSS data")
        logger.info(f"Found {len(feeds_meta)} feed metadata entries")

        if self.dry_run:
            await self._dry_run_analysis(chats_data, feeds_meta)
            return

        # Start actual migration
        await self._migrate_chats_and_feeds(chats_data)
        await self._migrate_feed_metadata(feeds_meta)
        await self._migrate_pending_items(chats_data)
        await self._migrate_digest_timestamps(chats_data)

        logger.info("Migration completed successfully!")

    async def _dry_run_analysis(self, chats_data: Dict, feeds_meta: Dict) -> None:
        """Analyze data without making changes."""
        logger.info("=== DRY RUN ANALYSIS ===")

        total_feeds = set()
        total_pending_items = 0

        for chat_id, chat_data in chats_data.items():
            feeds = chat_data.get("feeds", [])
            pending = chat_data.get("pending", {})
            last_digest = chat_data.get("last_digest_ts", 0)

            logger.info(f"Chat {chat_id}:")
            logger.info(f"  - {len(feeds)} feeds")
            logger.info(f"  - {sum(len(items) for items in pending.values())} pending items")
            logger.info(f"  - Last digest: {last_digest}")

            total_feeds.update(feeds)
            total_pending_items += sum(len(items) for items in pending.values())

        logger.info(f"\nSummary:")
        logger.info(f"  - {len(total_feeds)} unique feeds")
        logger.info(f"  - {total_pending_items} total pending items")
        logger.info(f"  - {len(feeds_meta)} feed metadata entries")

        # Show sample data
        if chats_data:
            sample_chat = list(chats_data.keys())[0]
            sample_data = chats_data[sample_chat]
            logger.info(f"\nSample chat data ({sample_chat}):")
            logger.info(f"  Feeds: {sample_data.get('feeds', [])[:2]}...")
            if sample_data.get('pending'):
                sample_url = list(sample_data['pending'].keys())[0]
                sample_items = sample_data['pending'][sample_url][:1]
                logger.info(f"  Sample pending item: {sample_items}")

    async def _migrate_chats_and_feeds(self, chats_data: Dict) -> None:
        """Migrate chat feeds data."""
        logger.info("Migrating chat feeds...")

        for chat_id, chat_data in chats_data.items():
            feeds = chat_data.get("feeds", [])
            logger.info(f"Migrating {len(feeds)} feeds for chat {chat_id}")

            for feed_url in feeds:
                try:
                    await self.pg_store.add_feed(chat_id, feed_url)
                    logger.debug(f"Added feed {feed_url} for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to add feed {feed_url} for chat {chat_id}: {e}")

    async def _migrate_feed_metadata(self, feeds_meta: Dict) -> None:
        """Migrate feed metadata (etag, last_modified, seen_ids)."""
        logger.info("Migrating feed metadata...")

        for feed_url, meta in feeds_meta.items():
            etag = meta.get("etag")
            last_modified = meta.get("last_modified")
            seen_ids = meta.get("seen_ids", [])

            logger.info(f"Migrating metadata for {feed_url}: {len(seen_ids)} seen IDs")

            try:
                # Update feed metadata with available fields
                await self.pg_store.update_feed_metadata(feed_url, title=f"Migrated feed", description="")

                # Handle seen IDs - log for now since PostgreSQL store doesn't support etag/seen_ids yet
                if etag:
                    logger.info(f"Feed {feed_url} etag: {etag}")
                if last_modified:
                    logger.info(f"Feed {feed_url} last_modified: {last_modified}")
                if seen_ids:
                    logger.info(f"Feed {feed_url} has {len(seen_ids)} seen IDs (stored in legacy format)")

            except Exception as e:
                logger.error(f"Failed to migrate metadata for {feed_url}: {e}")

    async def _migrate_pending_items(self, chats_data: Dict) -> None:
        """Migrate pending RSS items."""
        logger.info("Migrating pending items...")

        for chat_id, chat_data in chats_data.items():
            pending = chat_data.get("pending", {})

            for feed_url, items in pending.items():
                logger.info(f"Migrating {len(items)} pending items for {feed_url} in chat {chat_id}")

                for item in items:
                    try:
                        # Extract item data
                        item_id = item.get("id", "")
                        title = item.get("title", "")
                        link = item.get("link", "")
                        author = item.get("author", "")
                        published_ts = item.get("published_ts", 0)

                        # Convert timestamp to datetime if needed
                        pub_date = None
                        if published_ts:
                            from datetime import datetime
                            pub_date = datetime.fromtimestamp(published_ts)

                        # Add to PostgreSQL
                        await self.pg_store.add_item(
                            feed_url=feed_url,
                            guid=item_id,
                            title=title,
                            link=link,
                            description="",  # Not available in old format
                            pub_date=pub_date
                        )
                        logger.debug(f"Added pending item: {title}")

                    except Exception as e:
                        logger.error(f"Failed to migrate pending item {item.get('id', 'unknown')}: {e}")

    async def _migrate_digest_timestamps(self, chats_data: Dict) -> None:
        """Migrate last digest timestamps."""
        logger.info("Migrating digest timestamps...")

        for chat_id, chat_data in chats_data.items():
            last_digest = chat_data.get("last_digest_ts", 0)

            if last_digest:
                try:
                    await self.pg_store.set_last_digest_time(chat_id, last_digest)
                    logger.info(f"Set last digest time for chat {chat_id}: {last_digest}")
                except Exception as e:
                    logger.error(f"Failed to set digest time for chat {chat_id}: {e}")


async def main():
    """Main migration entry point."""
    parser = argparse.ArgumentParser(description="Migrate RSS data from JSON to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Analyze data without making changes")
    parser.add_argument("--json-path", default="data/rss.json", help="Path to RSS JSON file")

    args = parser.parse_args()

    # Load JSON data
    json_path = Path(args.json_path)
    if not json_path.exists():
        logger.error(f"RSS JSON file not found: {json_path}")
        return 1

    logger.info(f"Loading RSS data from {json_path}")
    with open(json_path, 'r') as f:
        json_data = json.load(f)

    # Initialize database connection
    try:
        config = load_config()
        if not config.database_url:
            logger.error("DATABASE_URL not configured in environment or .env file")
            return 1
        logger.info(f"Using database: {config.database_url.split('@')[1] if '@' in config.database_url else 'localhost'}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1

    db_manager = DatabaseManager(config)

    try:
        # Initialize database
        logger.info("Initializing database connection...")
        await db_manager.initialize()

        # Run migration
        migrator = RSSDataMigrator(db_manager, dry_run=args.dry_run)
        await migrator.migrate(json_data)

        return 0

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1
    finally:
        await db_manager.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))