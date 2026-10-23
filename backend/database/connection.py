"""
DSFMP Fraud Detection — Async MySQL Database Connection

Provides the SQLAlchemy async engine, session factory, and Base class
for ORM models. All database access goes through the `get_db` dependency.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config.settings import settings


# ── Async Engine ──────────────────────────────────
# Creates a connection pool to MySQL via aiomysql.
# pool_pre_ping=True ensures dead connections are discarded before use.
engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,     # Log SQL statements when DB_ECHO=true (independent of DEBUG)
    pool_pre_ping=False,       # Disabled to fix compatibility issue between SQLAlchemy 2.0 and aiomysql's ping() method
    pool_size=10,              # Max persistent connections
    max_overflow=20,           # Additional connections under load
    pool_recycle=3600,         # Recycle connections every hour
)


# ── Session Factory ───────────────────────────────
# Each request gets its own AsyncSession via the get_db dependency.
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,    # Prevent lazy-load issues after commit
)


# ── Base Class for ORM Models ─────────────────────
class Base(DeclarativeBase):
    """
    All ORM models inherit from this Base.

    Usage:
        from database.connection import Base

        class User(Base):
            __tablename__ = "users"
            ...
    """
    pass


# ── Dependency: get_db ────────────────────────────
async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields an async database session.
    The session is automatically closed after the request completes.

    Usage in a route:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
