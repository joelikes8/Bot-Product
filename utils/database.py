import os
import asyncio
import logging
import asyncpg
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Tuple

# Setup logging
logger = logging.getLogger('discord_bot.database')

# Get database connection info from environment variables
DB_NAME = os.getenv('PGDATABASE')
DB_USER = os.getenv('PGUSER')
DB_PASSWORD = os.getenv('PGPASSWORD')
DB_HOST = os.getenv('PGHOST')
DB_PORT = os.getenv('PGPORT')
DB_URL = os.getenv('DATABASE_URL')

# Use the DATABASE_URL if available, otherwise construct from individual vars
if DB_URL:
    dsn = DB_URL
else:
    dsn = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Pool for database connections
_pool = None

async def get_pool() -> asyncpg.Pool:
    """Get or create the database connection pool"""
    global _pool
    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Error creating database pool: {e}")
            raise
    return _pool

async def execute_query(query: str, *args) -> str:
    """Execute a database query with parameters"""
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)
    except Exception as e:
        logger.error(f"Database query error: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Args: {args}")
        raise

async def fetch_query(query: str, *args) -> List[Dict[str, Any]]:
    """Fetch data from the database with parameters"""
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Database fetch error: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Args: {args}")
        raise

async def create_tables():
    """Create all required database tables if they don't exist"""
    # Define all table creation queries
    tables = [
        # Store verified users
        """
        CREATE TABLE IF NOT EXISTS verified_users (
            id SERIAL PRIMARY KEY,
            discord_id BIGINT NOT NULL UNIQUE,
            discord_username TEXT NOT NULL,
            roblox_id BIGINT NOT NULL,
            roblox_username TEXT NOT NULL,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Store guild-specific settings
        """
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id BIGINT PRIMARY KEY,
            verified_role_id BIGINT,
            ticket_category_id BIGINT,
            log_channel_id BIGINT,
            welcome_channel_id BIGINT,
            welcome_message TEXT,
            prefix TEXT DEFAULT '!',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Store ticket support roles
        """
        CREATE TABLE IF NOT EXISTS ticket_support_roles (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            role_id BIGINT NOT NULL,
            UNIQUE(guild_id, role_id)
        )
        """,
        
        # Store tickets
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            channel_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            closed_at TIMESTAMP,
            status TEXT NOT NULL,
            ticket_type TEXT DEFAULT 'general',
            UNIQUE(guild_id, channel_id)
        )
        """,
        
        # Store moderation actions
        """
        CREATE TABLE IF NOT EXISTS mod_actions (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            target_id BIGINT NOT NULL,
            action_type TEXT NOT NULL,
            reason TEXT,
            timestamp TIMESTAMP NOT NULL,
            duration INT
        )
        """
    ]
    
    # Create each table
    try:
        for table_query in tables:
            await execute_query(table_query)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
