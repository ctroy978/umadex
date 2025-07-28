#!/usr/bin/env python3
import os
from urllib.parse import urlparse, quote, urlunparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_database_url(url):
    """Fix the database URL by properly encoding the password"""
    parsed = urlparse(url)
    
    # Extract username and password
    if '@' in parsed.netloc:
        auth_part, host_part = parsed.netloc.split('@', 1)
        if ':' in auth_part:
            username, password = auth_part.split(':', 1)
            # Properly URL encode the password
            encoded_password = quote(password, safe='')
            # Reconstruct the netloc
            new_netloc = f"{username}:{encoded_password}@{host_part}"
            # Create new URL with encoded password
            new_parsed = parsed._replace(netloc=new_netloc)
            return urlunparse(new_parsed)
    
    return url

# Test with the current DATABASE_URL
original_url = os.getenv('DATABASE_URL')
print("Original URL (password hidden):")
print(original_url.split('@')[0].rsplit(':', 1)[0] + ':****@' + original_url.split('@')[1])

fixed_url = fix_database_url(original_url)
print("\nFixed URL (password hidden):")
print(fixed_url.split('@')[0].rsplit(':', 1)[0] + ':****@' + fixed_url.split('@')[1])

# Test connection
import asyncio
import psycopg

async def test_connection():
    try:
        # Test with psycopg
        conn_str = fixed_url.replace('postgresql://', '')
        async with await psycopg.AsyncConnection.connect(conn_str) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                result = await cur.fetchone()
                print(f"\nConnection successful! Test query result: {result}")
    except Exception as e:
        print(f"\nConnection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())