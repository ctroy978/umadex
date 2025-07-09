#!/usr/bin/env python
"""Run database operations - create tables or run custom SQL"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.core.database import Base
from app.models import tests  # Import to register models

async def create_tables():
    """Create all tables defined in the models"""
    # Convert sync URL to async URL
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully!")
    
    await engine.dispose()

async def run_sql(sql_commands):
    """Run custom SQL commands"""
    # Convert sync URL to async URL
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    
    async with engine.begin() as conn:
        for sql in sql_commands.split(';'):
            sql = sql.strip()
            if sql:
                print(f"Running: {sql}")
                await conn.execute(text(sql))
        print("SQL executed successfully!")
    
    await engine.dispose()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sql":
        # Run custom SQL passed as second argument
        if len(sys.argv) > 2:
            asyncio.run(run_sql(sys.argv[2]))
        else:
            print("Usage: python create_tables.py sql \"SQL commands\"")
    else:
        # Default: create tables
        asyncio.run(create_tables())