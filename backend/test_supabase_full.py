#!/usr/bin/env python3
"""Test Supabase connection and authentication"""
import os
import sys
from dotenv import load_dotenv
import asyncio
from urllib.parse import urlparse, quote

# Load environment variables
load_dotenv()

print("=" * 60)
print("SUPABASE CONNECTION TEST")
print("=" * 60)

# 1. Test Supabase client connection
print("\n1. Testing Supabase Client Connection:")
try:
    from supabase import create_client
    
    url = os.getenv('SUPABASE_URL')
    anon_key = os.getenv('SUPABASE_ANON_KEY')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    print(f"   Supabase URL: {url}")
    print(f"   Anon Key: {anon_key[:20]}...{anon_key[-10:]}")
    print(f"   Service Key: {service_key[:20]}...{service_key[-10:]}")
    
    # Test anon client
    anon_client = create_client(url, anon_key)
    print("   ✅ Anon client created successfully")
    
    # Test service client
    service_client = create_client(url, service_key)
    print("   ✅ Service client created successfully")
    
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# 2. Test database connection
print("\n2. Testing Database Connection:")
database_url = os.getenv('DATABASE_URL')
print(f"   Database URL: {database_url[:50]}...{database_url[-30:]}")

async def test_db():
    try:
        # Test with asyncpg (used by SQLAlchemy)
        import asyncpg
        
        # Parse the URL
        parsed = urlparse(database_url)
        
        conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:],
            ssl='require'
        )
        
        # Test query
        row = await conn.fetchrow('SELECT version()')
        print(f"   ✅ Database connected: {row[0][:50]}...")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False

# Run database test
print("\n" + "=" * 60)
print("RUNNING DATABASE CONNECTION TEST...")
print("=" * 60)

db_success = asyncio.run(test_db())

print("\n" + "=" * 60)
print("SUMMARY:")
print("=" * 60)
print(f"✅ Supabase clients initialized")
print(f"{'✅' if db_success else '❌'} Database connection")

if not db_success:
    print("\n⚠️  DATABASE CONNECTION ISSUE:")
    print("   1. Check if the database password in Supabase dashboard matches your .env file")
    print("   2. Try resetting the database password in Supabase dashboard")
    print("   3. Ensure your IP is not blocked by Supabase")
    print("   4. Check Supabase dashboard for any service issues")