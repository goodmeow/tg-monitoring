# This file is part of tg-monitoring.
#
# tg-monitoring is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tg-monitoring is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tg-monitoring. If not, see <https://www.gnu.org/licenses/>.
#
# Author: Claude (Anthropic AI Assistant)
# Co-author: goodmeow (Harun Al Rasyid) <aarunalr@pm.me>

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

import asyncpg

from tgbot.domain.config import Config
from tgbot.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, config: Config):
        self.config = config
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        if not self.config.database_url:
            logger.info("No DATABASE_URL configured, PostgreSQL disabled")
            return

        try:
            logger.info("Initializing PostgreSQL connection pool...")
            self._pool = await asyncpg.create_pool(
                self.config.database_url,
                min_size=1,
                max_size=self.config.db_pool_size,
                command_timeout=self.config.db_timeout_sec,
                server_settings={
                    'application_name': 'tg-monitoring',
                    'timezone': 'UTC',
                }
            )
            logger.info(f"PostgreSQL pool initialized with {self.config.db_pool_size} connections")

            # Test connection and run schema
            await self.ensure_schema()

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            raise DatabaseError("Database initialization failed", context={"error": str(e)})

    async def close(self) -> None:
        """Close the database connection pool."""
        if self._pool:
            logger.info("Closing PostgreSQL connection pool...")
            await self._pool.close()
            self._pool = None

    @property
    def is_available(self) -> bool:
        """Check if database is available."""
        return self._pool is not None and not self._pool._closed

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a database connection from the pool."""
        if not self.is_available:
            raise DatabaseError("Database not available")

        try:
            async with self._pool.acquire() as conn:
                yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise DatabaseError("Database connection failed", context={"error": str(e)})

    async def ensure_schema(self) -> None:
        """Ensure database schema is created."""
        if not self.is_available:
            return

        try:
            async with self.connection() as conn:
                # Read schema file
                schema_sql = self._get_schema_sql()
                await conn.execute(schema_sql)
                logger.info("Database schema ensured")
        except Exception as e:
            logger.error(f"Failed to ensure schema: {e}")
            raise DatabaseError("Schema creation failed", context={"error": str(e)})

    def _get_schema_sql(self) -> str:
        """Get the schema SQL content."""
        import os
        schema_path = os.path.join(os.path.dirname(__file__), '../../schema.sql')
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            # Embedded schema as fallback
            return """
-- Basic schema for tg-monitoring
CREATE TABLE IF NOT EXISTS chats (
    id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS monitoring_state (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    chat_id BIGINT REFERENCES chats(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rss_feeds (
    id SERIAL PRIMARY KEY,
    url VARCHAR(2048) NOT NULL,
    title VARCHAR(512),
    description TEXT,
    chat_id BIGINT REFERENCES chats(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT true,
    last_polled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(url, chat_id)
);

CREATE TABLE IF NOT EXISTS rss_items (
    id SERIAL PRIMARY KEY,
    feed_id INTEGER REFERENCES rss_feeds(id) ON DELETE CASCADE,
    guid VARCHAR(512) NOT NULL,
    title VARCHAR(512),
    link VARCHAR(2048),
    description TEXT,
    pub_date TIMESTAMP WITH TIME ZONE,
    is_sent BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(feed_id, guid)
);

CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_monitoring_state_chat_id ON monitoring_state(chat_id);
CREATE INDEX IF NOT EXISTS idx_rss_feeds_chat_id ON rss_feeds(chat_id);
CREATE INDEX IF NOT EXISTS idx_rss_items_feed_id ON rss_items(feed_id);
"""