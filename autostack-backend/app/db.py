from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import settings


class Base(DeclarativeBase):
    pass


engine_kwargs: dict = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}

if settings.database_url.startswith("sqlite+"):
    engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": 30,  # Increase timeout to wait for locks
    }
    engine_kwargs["poolclass"] = NullPool

    # Enable WAL mode for better concurrency
    from sqlalchemy import event
    
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

engine = create_async_engine(settings.database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker[
    AsyncSession
](
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    # Place for running startup checks or ensuring connection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Lightweight, idempotent migration for Postgres to ensure new columns exist
        if settings.database_url.startswith("postgresql"):
            await conn.execute(
                text(
                    "ALTER TABLE projects "
                    "ADD COLUMN IF NOT EXISTS jenkins_job_name VARCHAR(255);"
                )
            )
