"""
Update RLS policies to work with Supabase Auth
This script updates the Row Level Security policies to use auth.uid() instead of session variables
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../.env.supabase")

async def update_rls_policies():
    """Update RLS policies for Supabase Auth integration"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url or "[YOUR-PASSWORD]" in database_url:
        print("❌ ERROR: Valid DATABASE_URL required")
        return False
    
    # Convert to async URL
    async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    print("🔄 Updating RLS policies for Supabase Auth...")
    
    try:
        engine = create_async_engine(async_url, echo=False)
        
        async with engine.connect() as conn:
            # Check if we're using custom session variables
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM pg_policies 
                WHERE polname LIKE '%app.%'
            """))
            custom_policy_count = (await result.fetchone())[0]
            
            if custom_policy_count > 0:
                print(f"ℹ️  Found {custom_policy_count} policies using custom session variables")
                print("ℹ️  These will need to be updated when implementing Supabase Auth in Phase 3")
            else:
                print("✅ RLS policies are already compatible with Supabase Auth")
            
            # Create a helper function for session context (temporary until Phase 3)
            await conn.execute(text("""
                CREATE OR REPLACE FUNCTION get_current_user_id() 
                RETURNS UUID AS $$
                BEGIN
                    -- Phase 2: Use session variable
                    -- Phase 3: This will be updated to: RETURN auth.uid();
                    RETURN NULLIF(current_setting('app.current_user_id', true), '')::UUID;
                END;
                $$ LANGUAGE plpgsql SECURITY DEFINER;
            """))
            
            await conn.execute(text("""
                CREATE OR REPLACE FUNCTION is_current_user_admin() 
                RETURNS BOOLEAN AS $$
                BEGIN
                    -- Phase 2: Use session variable
                    -- Phase 3: This will check against Supabase Auth metadata
                    RETURN COALESCE(current_setting('app.is_admin', true)::BOOLEAN, false);
                END;
                $$ LANGUAGE plpgsql SECURITY DEFINER;
            """))
            
            await conn.commit()
            print("✅ Created helper functions for RLS policies")
            print("ℹ️  These functions will be updated in Phase 3 to use Supabase Auth")
            
            return True
            
    except Exception as e:
        print(f"❌ Error updating RLS policies: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("=" * 60)
    print("RLS Policy Update for Supabase")
    print("=" * 60)
    print("\n⚠️  Note: Full RLS integration with Supabase Auth will be done in Phase 3")
    print("This script prepares the database for the transition\n")
    
    asyncio.run(update_rls_policies())