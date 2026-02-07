import logging
import ssl
from typing import Optional
import asyncpg
from config.settings import settings

logger = logging.getLogger("scamshield.database")

db_pool: Optional[asyncpg.Pool] = None


async def init_postgres() -> asyncpg.Pool:
    global db_pool
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        db_pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=settings.DB_POOL_MIN_SIZE,
            max_size=settings.DB_POOL_MAX_SIZE,
            command_timeout=60,
            ssl=ssl_context
        )
        logger.info("PostgreSQL connection pool created")
        return db_pool
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        raise


async def close_postgres():
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None
        logger.info("PostgreSQL pool closed")


async def get_db() -> asyncpg.Connection:
    if db_pool is None:
        raise RuntimeError("Database pool not initialized")
    return db_pool.acquire()


async def execute_query(query: str, *args) -> str:
    async with db_pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch_one(query: str, *args) -> Optional[asyncpg.Record]:
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetch_all(query: str, *args) -> list:
    async with db_pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetch_value(query: str, *args):
    async with db_pool.acquire() as conn:
        return await conn.fetchval(query, *args)
