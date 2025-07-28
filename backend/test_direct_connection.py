import os
from dotenv import load_dotenv
import psycopg
import asyncio
from urllib.parse import urlparse

load_dotenv()

async def test_direct_connection():
    database_url = os.getenv('DATABASE_URL')
    print("Testing direct connection to Supabase...")
    
    # Parse the URL
    parsed = urlparse(database_url)
    
    # Extract components
    username = parsed.username
    password = parsed.password
    hostname = parsed.hostname
    port = parsed.port
    database = parsed.path.lstrip('/')
    
    print(f"Connection details:")
    print(f"  Username: {username}")
    print(f"  Password: {'*' * len(password) if password else 'None'}")
    print(f"  Host: {hostname}")
    print(f"  Port: {port}")
    print(f"  Database: {database}")
    
    try:
        # Build connection string
        conn_str = f"host={hostname} port={port} dbname={database} user={username} password={password}"
        
        async with await psycopg.AsyncConnection.connect(conn_str) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT version()")
                version = await cur.fetchone()
                print(f"\nSUCCESS! Connected to: {version[0]}")
                
                # Test if we can access tables
                await cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' LIMIT 5")
                tables = await cur.fetchall()
                print("\nSample tables in public schema:")
                for table in tables:
                    print(f"  - {table[0]}")
                    
    except Exception as e:
        print(f"\nFAILED: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_direct_connection())