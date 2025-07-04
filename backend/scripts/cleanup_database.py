#!/usr/bin/env python3
"""
Database cleanup script for UMADex
This script removes all data from the database while preserving the schema.
WARNING: This will DELETE ALL DATA in the database!
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of tables to clean in order (considering foreign key constraints)
TABLES_TO_CLEAN = [
    # Test and assessment related
    "test_security_incidents",
    "test_override_usage",
    "classroom_test_overrides",
    "classroom_test_schedules",
    "teacher_bypass_codes",
    "student_test_attempts",
    "test_results",
    "assignment_tests",
    
    # Vocabulary related
    "vocabulary_practice_progress",
    "vocabulary_word_reviews",
    "vocabulary_chain_members",
    "vocabulary_chains",
    "vocabulary_words",
    "vocabulary_lists",
    
    # Reading and content related
    "umaread_assignment_progress",
    "umaread_chunk_progress",
    "umaread_student_responses",
    "answer_evaluations",
    "question_cache",
    "assignment_images",
    "reading_chunks",
    "reading_assignments",
    
    # Writing related
    "student_writing_submissions",
    "writing_assignments",
    
    # Classroom and assignment related
    "student_events",
    "student_assignments",
    "classroom_assignments",
    "classroom_students",
    "classrooms",
    
    # User and auth related
    "refresh_tokens",
    "user_sessions",
    "otp_requests",
    "email_whitelists",
    "users",
]

async def cleanup_database():
    """Clean all data from the database"""
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    async with engine.begin() as conn:
        try:
            # Disable foreign key checks temporarily
            await conn.execute(text("SET session_replication_role = 'replica';"))
            
            # Clean each table
            for table in TABLES_TO_CLEAN:
                try:
                    result = await conn.execute(text(f"DELETE FROM {table};"))
                    logger.info(f"Cleaned table '{table}': {result.rowcount} rows deleted")
                except Exception as e:
                    logger.error(f"Error cleaning table '{table}': {e}")
            
            # Re-enable foreign key checks
            await conn.execute(text("SET session_replication_role = 'origin';"))
            
            # Reset sequences if needed (for any serial/identity columns)
            await conn.execute(text("SELECT setval(pg_get_serial_sequence(table_name, column_name), 1, false) FROM information_schema.columns WHERE column_default LIKE 'nextval%';"))
            
            logger.info("Database cleanup completed successfully!")
            
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            raise
    
    await engine.dispose()

async def confirm_cleanup():
    """Ask for confirmation before cleaning the database"""
    print("\n" + "="*60)
    print("WARNING: This will DELETE ALL DATA in the database!")
    print("This action cannot be undone.")
    print("="*60 + "\n")
    
    confirmation = input("Type 'DELETE ALL DATA' to confirm: ")
    
    if confirmation != "DELETE ALL DATA":
        print("Cleanup cancelled.")
        return False
    
    return True

async def main():
    """Main function"""
    if not await confirm_cleanup():
        sys.exit(0)
    
    print("\nStarting database cleanup...")
    await cleanup_database()
    print("\nDatabase cleanup completed!")

if __name__ == "__main__":
    asyncio.run(main())