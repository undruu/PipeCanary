from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def task_session():
    """Create a fresh engine + session for use inside Celery tasks.

    Celery workers fork, so the module-level engine's asyncpg connections are
    bound to the parent's event loop.  asyncio.run() in each task creates a new
    loop, making the old connections unusable.  This helper creates an
    independent engine (and disposes it after use) so every task invocation gets
    connections on the current event loop.
    """
    task_engine = create_async_engine(settings.database_url, echo=settings.debug)
    factory = async_sessionmaker(task_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
    await task_engine.dispose()
