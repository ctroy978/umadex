#!/usr/bin/env python3
"""
Script to manually trigger evaluation for submitted but unevaluated tests
"""
import asyncio
import sys
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.database import AsyncSessionLocal
from app.models.tests import StudentTestAttempt
from app.models.umatest import TestAssignment
from app.services.umatest_evaluation import UMATestEvaluationService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def evaluate_submitted_tests():
    async with AsyncSessionLocal() as db:
        # Find submitted but unevaluated tests
        result = await db.execute(
            select(StudentTestAttempt, TestAssignment)
            .join(TestAssignment, StudentTestAttempt.test_id == TestAssignment.id)
            .where(
                and_(
                    StudentTestAttempt.status == 'submitted',
                    StudentTestAttempt.score.is_(None),
                    TestAssignment.test_type == 'hand_built'
                )
            )
        )
        
        unevaluated_tests = result.all()
        
        if not unevaluated_tests:
            logger.info("No unevaluated hand-built tests found")
            return
        
        logger.info(f"Found {len(unevaluated_tests)} unevaluated hand-built tests")
        
        for test_attempt, test_assignment in unevaluated_tests:
            logger.info(f"Evaluating test: {test_assignment.test_title} (Attempt ID: {test_attempt.id})")
            
            try:
                evaluation_service = UMATestEvaluationService(db)
                result = await evaluation_service.evaluate_test_submission(
                    test_attempt_id=test_attempt.id,
                    trigger_source="manual_evaluation"
                )
                logger.info(f"Successfully evaluated test {test_attempt.id}. Score: {result.get('score', 'N/A')}")
                
            except Exception as e:
                logger.error(f"Failed to evaluate test {test_attempt.id}: {str(e)}", exc_info=True)
                continue
        
        logger.info("Evaluation process completed")

if __name__ == "__main__":
    asyncio.run(evaluate_submitted_tests())