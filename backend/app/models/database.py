"""
Database engine and session management with Automatic Schema Migration.
Supports async SQLite for zero-config local runs and async PostgreSQL for cloud deployment.
Automatically upgrades existing database tables with new columns (e.g. users.phone_number) on startup.
"""
import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from backend.app.config import settings

logger = logging.getLogger("videogen.db")

# Configure SQLite or PostgreSQL async engine
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def _migrate_sqlite_schema(conn):
    """
    Checks existing SQLite database tables and automatically adds any missing columns.
    Prevents 'no such column' errors when models are updated.
    """
    # 1. Users table migration
    try:
        res = await conn.execute(text("PRAGMA table_info(users)"))
        cols = {row[1] for row in res.fetchall()}
        if cols:
            if "phone_number" not in cols:
                logger.info("Migrating schema: Adding phone_number to users table")
                await conn.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(30)"))
            if "hashed_password" not in cols:
                logger.info("Migrating schema: Adding hashed_password to users table")
                await conn.execute(text("ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255)"))
            if "is_verified" not in cols:
                logger.info("Migrating schema: Adding is_verified to users table")
                await conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0"))
            if "updated_at" not in cols:
                logger.info("Migrating schema: Adding updated_at to users table")
                await conn.execute(text("ALTER TABLE users ADD COLUMN updated_at DATETIME"))
    except Exception as e:
        logger.debug(f"Users table migration check: {e}")

    # 2. Projects table migration
    try:
        res = await conn.execute(text("PRAGMA table_info(projects)"))
        cols = {row[1] for row in res.fetchall()}
        if cols:
            if "user_id" not in cols:
                logger.info("Migrating schema: Adding user_id to projects table")
                await conn.execute(text("ALTER TABLE projects ADD COLUMN user_id VARCHAR(36)"))
            if "aspect_ratio" not in cols:
                logger.info("Migrating schema: Adding aspect_ratio to projects table")
                await conn.execute(text("ALTER TABLE projects ADD COLUMN aspect_ratio VARCHAR(20) DEFAULT '16:9'"))
            if "music_mood" not in cols:
                logger.info("Migrating schema: Adding music_mood to projects table")
                await conn.execute(text("ALTER TABLE projects ADD COLUMN music_mood VARCHAR(50) DEFAULT 'Cinematic'"))
    except Exception as e:
        logger.debug(f"Projects table migration check: {e}")


async def init_db():
    """Create all tables in the database if they do not exist and apply migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.DATABASE_URL.startswith("sqlite"):
            await _migrate_sqlite_schema(conn)
