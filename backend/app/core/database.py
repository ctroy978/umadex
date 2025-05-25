from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event, text
from typing import AsyncGenerator

from .config import settings

# Convert DATABASE_URL to async version
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def set_rls_context(session: AsyncSession, user_id: str = None, user_email: str = None, is_admin: bool = False):
    """Set RLS context for the current session"""
    if user_id:
        await session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
    if user_email:
        await session.execute(text(f"SET LOCAL app.current_user_email = '{user_email}'"))
    await session.execute(text(f"SET LOCAL app.is_admin = '{str(is_admin).lower()}'"))