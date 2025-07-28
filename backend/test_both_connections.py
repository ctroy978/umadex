import os
import asyncio
import psycopg
from dotenv import load_dotenv

load_dotenv()

async def test_connections():
    # Get the pooler URL from env
    pooler_url = os.getenv('DATABASE_URL')
    password = pooler_url.split('@')[0].split(':')[-1].split('?')[0]
    
    # Build direct connection URL
    direct_url = f"postgresql://postgres:{password}@db.wssmxlqloncdhonzssbj.supabase.co:5432/postgres"
    
    print("Testing Supabase connections...")
    print(f"Password: {'*' * len(password)}")
    print()
    
    # Test pooler connection
    print("1. Testing POOLER connection (port 6543)...")
    try:
        conn = await psycopg.AsyncConnection.connect(pooler_url)
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT version()')
                result = await cur.fetchone()
                print(f"   ✓ SUCCESS! Pooler connection works")
                print(f"   Version: {result[0][:50]}...")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
    
    print()
    
    # Test direct connection
    print("2. Testing DIRECT connection (port 5432)...")
    try:
        conn = await psycopg.AsyncConnection.connect(direct_url)
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT version()')
                result = await cur.fetchone()
                print(f"   ✓ SUCCESS! Direct connection works")
                print(f"   Version: {result[0][:50]}...")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
    
    print("\nNote: If direct connection works but pooler doesn't, wait 5-10 minutes for password to propagate to the pooler.")

if __name__ == "__main__":
    asyncio.run(test_connections())