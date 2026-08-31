"""
Pytest configuration and test database fixtures for Videogen-Lucy test suite.
"""
import pytest
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.app.models.database import Base, get_db, init_db, engine
from backend.app.main import app
from backend.app.config import settings

# Test SQLite file
TEST_DB_FILE = settings.STORAGE_DIR / "test_videogen.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    future=True
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def override_get_db():
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture(autouse=True)
async def setup_test_environment():
    """Create test tables and set dependency overrides."""
    settings.init_directories()
    app.dependency_overrides[get_db] = override_get_db
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Also initialize default app DB
    await init_db()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Yield an isolated async database session for testing."""
    async with TestAsyncSessionLocal() as session:
        yield session
