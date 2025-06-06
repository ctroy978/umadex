#!/usr/bin/env python3
"""
Clear all data from the database for testing purposes.
This script removes all data but preserves table structures.
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def clear_database():
    """Clear all data from the database."""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment variables")
        return
    
    # Create async engine
    engine = create_async_engine(database_url)
    
    try:
        async with engine.begin() as conn:
            print("🗑️  Starting database cleanup...")
            
            # Disable foreign key checks
            await conn.execute(text("SET session_replication_role = 'replica'"))
            
            # Define tables in order (considering dependencies)
            tables_to_clear = [
                # Test-related tables
                "test_security_incidents",
                "teacher_bypass_codes", 
                "student_test_attempts",
                "test_results",
                "assignment_tests",
                
                # UmaRead tables
                "umaread_test_override_usage",
                "umaread_test_questions",
                "umaread_test_results",
                "umaread_student_events",
                "umaread_assignment_progress",
                "umaread_simple_questions",
                "umaread_simple_sessions",
                "student_assignments",
                "umaread_assignments",
                
                # Vocabulary tables
                "classroom_vocabulary_assignments",
                "student_vocabulary_progress",
                "vocabulary_assignments",
                
                # Classroom tables
                "classroom_test_schedules",
                "classroom_assignments",
                "classroom_students",
                "classrooms",
                
                # Reading/assignment tables
                "ai_image_analysis",
                "assignment_images",
                "reading_chunks",
                "reading_assignments",
                
                # User-related tables
                "refresh_tokens",
                "whitelist_entries",
                "users"
            ]
            
            # Clear each table
            for table in tables_to_clear:
                try:
                    await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                    print(f"✓ Cleared table: {table}")
                except Exception as e:
                    print(f"⚠️  Warning clearing {table}: {str(e)}")
            
            # Re-enable foreign key checks
            await conn.execute(text("SET session_replication_role = 'origin'"))
            
            # Get counts to verify
            print("\n📊 Verification - Row counts after cleanup:")
            verification_tables = [
                "users",
                "reading_assignments", 
                "assignment_tests",
                "classrooms",
                "umaread_assignments"
            ]
            
            for table in verification_tables:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"   {table}: {count} rows")
            
            print("\n✅ Database cleanup complete!")
            
    except Exception as e:
        print(f"\n❌ Error during cleanup: {str(e)}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("⚠️  WARNING: This will delete ALL data from your database!")
    print("⚠️  The database structure will be preserved, but all users, tests, assignments, etc. will be removed.")
    
    confirmation = input("\nType 'DELETE ALL DATA' to confirm: ")
    
    if confirmation == "DELETE ALL DATA":
        asyncio.run(clear_database())
    else:
        print("❌ Cancelled. No data was deleted.")