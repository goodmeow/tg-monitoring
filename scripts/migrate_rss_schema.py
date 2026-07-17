#!/usr/bin/env python3
"""
Database schema migration script for RSS feeds table
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tgbot.domain.config import load_config
from tgbot.core.database import DatabaseManager

async def migrate_rss_feeds_schema():
    """Migrate RSS feeds table to support multiple chats per feed."""
    print("Starting RSS feeds schema migration...")

    # Load config and initialize database
    config = load_config()
    db_manager = DatabaseManager(config)
    await db_manager.initialize()

    try:
        async with db_manager.connection() as conn:
            # Check current schema
            print("Checking current schema...")

            # Drop old unique constraint on url if it exists
            print("Removing old UNIQUE constraint on url...")
            try:
                await conn.execute("""
                    ALTER TABLE rss_feeds DROP CONSTRAINT IF EXISTS rss_feeds_url_key;
                """)
                print("✅ Dropped old unique constraint")
            except Exception as e:
                print(f"Note: {e}")

            # Add new unique constraint on (url, chat_id) if not exists
            print("Adding new UNIQUE constraint on (url, chat_id)...")
            try:
                await conn.execute("""
                    ALTER TABLE rss_feeds
                    ADD CONSTRAINT rss_feeds_url_chat_id_key
                    UNIQUE (url, chat_id);
                """)
                print("✅ Added new unique constraint")
            except Exception as e:
                print(f"Note: Constraint may already exist: {e}")

            # Verify the change
            print("Verifying schema changes...")
            constraints = await conn.fetch("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'rss_feeds' AND constraint_type = 'UNIQUE';
            """)

            print("Current unique constraints:")
            for constraint in constraints:
                print(f"  - {constraint['constraint_name']}: {constraint['constraint_type']}")

        print("✅ Schema migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return 1
    finally:
        await db_manager.close()

    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(migrate_rss_feeds_schema()))