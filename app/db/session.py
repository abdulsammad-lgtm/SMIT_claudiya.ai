"""
Database session management.
Supports PostgreSQL (primary) with SQLite fallback for development.
"""
import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import get_settings

settings = get_settings()


def _build_engine(db_url: str | None = None):
    url = db_url or settings.database_url
    use_sqlite = url.startswith("sqlite") or url.startswith("sqlite+aiosqlite")
    if use_sqlite:
        url = url.replace("postgresql+asyncpg://", "sqlite+aiosqlite://")
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fraud_demo.db"
        )
        url = f"sqlite+aiosqlite:///{db_path}"

    connect_args = {"check_same_thread": False} if use_sqlite else {}
    return create_async_engine(url, echo=settings.database_echo, connect_args=connect_args)


engine = _build_engine()
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
