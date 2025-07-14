#!/usr/bin/env python3
"""
Debug script to check UMATest evaluation issues
"""
import asyncio
import sys
from uuid import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from app.models.tests import StudentTestAttempt, TestQuestionEvaluation
from app.core.config import settings

async def check_test_evaluations(test_attempt_id: str):
    """Check evaluations for a specific test attempt"""
    
    # Create engine
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if test attempt exists
        result = await session.execute(
            select(StudentTestAttempt).where(StudentTestAttempt.id == UUID(test_attempt_id))
        )
        test_attempt = result.scalar_one_or_none()
        
        if not test_attempt:
            print(f"Test attempt {test_attempt_id} not found")
            return
            
        print(f"\nTest Attempt Details:")
        print(f"ID: {test_attempt.id}")
        print(f"Status: {test_attempt.status}")
        print(f"Score: {test_attempt.score}")
        print(f"Submitted at: {test_attempt.submitted_at}")
        print(f"Evaluated at: {test_attempt.evaluated_at}")
        print(f"Answers data keys: {list(test_attempt.answers_data.keys()) if test_attempt.answers_data else 'None'}")
        print(f"Number of answers: {len(test_attempt.answers_data) if test_attempt.answers_data else 0}")
        
        # Check evaluations
        result = await session.execute(
            select(TestQuestionEvaluation)
            .where(TestQuestionEvaluation.test_attempt_id == UUID(test_attempt_id))
            .order_by(TestQuestionEvaluation.question_index)
        )
        evaluations = result.scalars().all()
        
        print(f"\nFound {len(evaluations)} evaluations:")
        for eval in evaluations:
            print(f"\nQuestion {eval.question_index}:")
            print(f"  Score: {eval.rubric_score}")
            print(f"  Points: {eval.points_earned}/{eval.max_points}")
            print(f"  Rationale: {eval.scoring_rationale[:100]}...")
            
        # Check table schema
        result = await session.execute(
            text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'test_question_evaluations'
                ORDER BY ordinal_position
            """)
        )
        columns = result.fetchall()
        
        print(f"\nTable schema for test_question_evaluations:")
        for col_name, col_type in columns:
            print(f"  {col_name}: {col_type}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_umatest_evaluation.py <test_attempt_id>")
        print("\nYou can find the test_attempt_id from the console output when submitting a test")
        return
        
    test_attempt_id = sys.argv[1]
    await check_test_evaluations(test_attempt_id)

if __name__ == "__main__":
    asyncio.run(main())