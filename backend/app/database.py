from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_connect_args = (
    {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
)
if _settings.production and "ssl=" not in _settings.database_url:
    _connect_args["ssl"] = "require"

engine = create_async_engine(
    _settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=not _settings.database_url.startswith("sqlite"),
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    from app import models  # noqa: F401  (register mappers)
    from app.v1 import models as v1_models  # noqa: F401

    if _settings.production:
        # Deployments run `alembic upgrade head` explicitly before serving traffic.
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if _settings.database_url.startswith("sqlite"):
            await conn.exec_driver_sql("PRAGMA table_info(bookings)")
            rows = (
                await conn.exec_driver_sql("PRAGMA table_info(bookings)")
            ).fetchall()
            cols = {row[1] for row in rows}
            if "origin" not in cols:
                await conn.exec_driver_sql(
                    "ALTER TABLE bookings ADD COLUMN origin VARCHAR(3)"
                )
            if "destination" not in cols:
                await conn.exec_driver_sql(
                    "ALTER TABLE bookings ADD COLUMN destination VARCHAR(3)"
                )
