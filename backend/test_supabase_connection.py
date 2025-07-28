"""
Test script to verify Supabase database connection
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../.env.supabase")

async def test_connection():
    """Test basic database connection to Supabase"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        print("   Please check your .env.supabase file")
        return False
    
    # Check if password placeholder is still in URL
    if "[YOUR-PASSWORD]" in database_url:
        print("❌ ERROR: Database password not set")
        print("   Please update DATABASE_URL in .env.supabase with your actual password")
        print("   Get it from: https://supabase.com/dashboard/project/wssmxlqloncdhonzssbj/settings/database")
        return False
    
    # Convert to async URL
    async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    print(f"🔄 Testing connection to Supabase...")
    print(f"   Project: wssmxlqloncdhonzssbj")
    
    try:
        # Create engine with connection settings
        engine = create_async_engine(
            async_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=300,
            connect_args={
                "server_settings": {"jit": "off"},
                "timeout": 60,
                "command_timeout": 60,
            }
        )
        
        # Test connection
        async with engine.connect() as conn:
            # Simple query to test connection
            result = await conn.execute(text("SELECT 1"))
            await conn.commit()
            
            print("✅ Basic connection successful!")
            
            # Test database version
            result = await conn.execute(text("SELECT version()"))
            version = (await result.fetchone())[0]
            print(f"✅ PostgreSQL version: {version}")
            
            # Test table access
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = (await result.fetchone())[0]
            print(f"✅ Found {table_count} tables in public schema")
            
            # Test specific tables from migration
            tables_to_check = ['users', 'classrooms', 'reading_assignments', 'vocabulary_lists']
            for table in tables_to_check:
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table}'
                    )
                """))
                exists = (await result.fetchone())[0]
                if exists:
                    print(f"✅ Table '{table}' exists")
                else:
                    print(f"❌ Table '{table}' not found")
            
            print("\n🎉 Supabase connection test completed successfully!")
            return True
            
    except Exception as e:
        print(f"\n❌ Connection failed: {type(e).__name__}: {e}")
        print("\n📋 Troubleshooting steps:")
        print("1. Check your database password in .env.supabase")
        print("2. Ensure your IP is not blocked by Supabase")
        print("3. Verify the database URL format is correct")
        print("4. Check if the Supabase project is active")
        return False
    finally:
        await engine.dispose()

async def test_supabase_config():
    """Test Supabase API configuration"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    
    print("\n🔍 Checking Supabase API configuration...")
    
    if supabase_url:
        print(f"✅ SUPABASE_URL: {supabase_url}")
    else:
        print("❌ SUPABASE_URL not found")
    
    if supabase_anon_key:
        print(f"✅ SUPABASE_ANON_KEY: {supabase_anon_key[:20]}...")
    else:
        print("❌ SUPABASE_ANON_KEY not found")
    
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if service_role_key and service_role_key != "your-service-role-key-here":
        print(f"✅ SUPABASE_SERVICE_ROLE_KEY: {service_role_key[:20]}...")
    else:
        print("⚠️  SUPABASE_SERVICE_ROLE_KEY not set (optional for now)")

if __name__ == "__main__":
    print("=" * 60)
    print("Supabase Connection Test")
    print("=" * 60)
    
    # Run tests
    asyncio.run(test_connection())
    asyncio.run(test_supabase_config())
    
    print("\n📝 Next steps:")
    print("1. If connection failed, update DATABASE_URL in .env.supabase")
    print("2. Copy .env.supabase to .env to use Supabase settings")
    print("3. Run 'docker-compose up' to test the full stack")
    print("4. Test API endpoints that use the database")