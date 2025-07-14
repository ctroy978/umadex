#!/usr/bin/env python3
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_
from app.core.config import settings
from app.models.tests import StudentTestAttempt, TestQuestionEvaluation
from app.models.user import User

async def check_user_tests(username: str):
    """Check test attempts for a specific user"""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get user
        result = await session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User {username} not found")
            return
            
        print(f"Found user: {user.username} (ID: {user.id})")
        
        # Get latest test attempts
        result = await session.execute(
            select(StudentTestAttempt)
            .where(StudentTestAttempt.student_id == user.id)
            .order_by(StudentTestAttempt.created_at.desc())
            .limit(3)
        )
        attempts = result.scalars().all()
        
        print(f"\nFound {len(attempts)} recent test attempts")
        
        for attempt in attempts:
            print(f"\n{'='*60}")
            print(f"Attempt ID: {attempt.id}")
            print(f"Status: {attempt.status}")
            print(f"Score: {attempt.score}")
            print(f"Submitted: {attempt.submitted_at}")
            print(f"Number of answers: {len(attempt.answers_data) if attempt.answers_data else 0}")
            
            if attempt.answers_data:
                print(f"\nAnswers provided for questions:")
                for q_idx, answer in attempt.answers_data.items():
                    if answer.strip():
                        print(f"  Question {q_idx}: '{answer[:50]}...' (length: {len(answer)})")
                    else:
                        print(f"  Question {q_idx}: [empty answer]")
            
            # Check evaluations
            result = await session.execute(
                select(TestQuestionEvaluation)
                .where(TestQuestionEvaluation.test_attempt_id == attempt.id)
                .order_by(TestQuestionEvaluation.question_index)
            )
            evaluations = result.scalars().all()
            
            print(f"\nEvaluations found: {len(evaluations)}")
            if evaluations:
                print("Evaluation scores:")
                for eval in evaluations:
                    print(f"  Question {eval.question_index}: Score={eval.rubric_score}, Points={eval.points_earned}/{eval.max_points}")

if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "icoop-csd8info"
    asyncio.run(check_user_tests(username))