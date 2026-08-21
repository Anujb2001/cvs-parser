import clickhouse_connect
import asyncpg
from app.core.config import settings

# Synchronous/Pooled ClickHouse Client
def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        username=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
        database=settings.CLICKHOUSE_DB
    )

# Async PostgreSQL Connection Pool
postgres_pool = None

async def init_postgres_pool():
    global postgres_pool
    postgres_pool = await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB,
        min_size=2,
        max_size=10
    )

async def get_postgres_conn():
    async with postgres_pool.acquire() as connection:
        yield connection