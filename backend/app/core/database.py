from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event, text
from typing import AsyncGenerator
from urllib.parse import urlparse, quote, urlunparse

from .config import settings

def fix_database_url(url):
    """Fix the database URL by properly encoding the password"""
    # First replace the scheme
    url = url.replace("postgresql://", "postgresql+psycopg://")
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Extract and encode the password if needed
    if '@' in parsed.netloc:
        auth_part, host_part = parsed.netloc.split('@', 1)
        if ':' in auth_part:
            username, password = auth_part.split(':', 1)
            # URL encode the password to handle special characters
            encoded_password = quote(password, safe='')
            # Reconstruct the netloc
            new_netloc = f"{username}:{encoded_password}@{host_part}"
            # Create new URL with encoded password
            parsed = parsed._replace(netloc=new_netloc)
    
    return urlunparse(parsed)

# Use psycopg driver with properly encoded URL
DATABASE_URL = fix_database_url(settings.DATABASE_URL)

# For psycopg, we keep the SSL parameters in the URL
# Disable prepared statements to avoid conflicts
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Important for cloud databases
    pool_recycle=300,  # Recycle connections after 5 minutes
    connect_args={
        "prepare_threshold": None,  # Disable prepared statements
    }
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