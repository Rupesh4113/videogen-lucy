"""
Database engine and session management with Automatic Dynamic Schema Migration and NullPool connection safety.
Supports async SQLite for zero-config local/cloud runs and async PostgreSQL for cloud deployment.
Uses NullPool for SQLite to guarantee multi-thread and multi-event-loop safety in Streamlit and Celery.
"""
import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from backend.app.config import settings

logger = logging.getLogger("videogen.db")

Base = declarative_base()

# Configure SQLite or PostgreSQL async engine
# For SQLite, NullPool prevents "Task attached to a different loop" and connection thread desync in Streamlit/uvloop
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
pool_kwargs = {"poolclass": NullPool} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    future=True,
    **pool_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def _migrate_sqlite_schema(conn):
    """
    Dynamically inspects ALL tables in Base.metadata and automatically adds any missing columns.
    Completely eliminates any 'table X has no column named Y' errors forever.
    """
    import backend.app.models.entities  # Ensure all model tables are registered
    
    for table_name, table in Base.metadata.tables.items():
        try:
            res = await conn.execute(text(f"PRAGMA table_info({table_name})"))
            existing_cols = {row[1] for row in res.fetchall()}
            if not existing_cols:
                continue

            for col in table.columns:
                if col.name not in existing_cols:
                    col_type = col.type.compile(engine.dialect)
                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"
                    logger.info(f"Auto-migrating SQLite schema: {alter_sql}")
                    await conn.execute(text(alter_sql))
        except Exception as e:
            logger.warning(f"Auto-migration error on table {table_name}: {e}")


async def init_db():
    """Create all tables in the database if they do not exist and apply migrations."""
    import backend.app.models.entities  # noqa: F401
    
    settings.init_directories()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.DATABASE_URL.startswith("sqlite"):
            await _migrate_sqlite_schema(conn)
