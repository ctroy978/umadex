#!/usr/bin/env python3
"""
Test script to generate vocabulary questions
"""
import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, '/app')

from app.services.vocabulary_game_generator import VocabularyGameGenerator
from app.core.database import get_async_db_session
from uuid import UUID

async def test_generation():
    """Test question generation for vocabulary list"""
    
    # Use the vocabulary list ID from the error
    vocabulary_list_id = UUID('3cb6f1f4-ae08-4869-ab32-b02545877406')
    
    async with get_async_db_session() as db:
        generator = VocabularyGameGenerator(db)
        
        print(f"Generating questions for vocabulary list: {vocabulary_list_id}")
        
        try:
            questions = await generator.generate_game_questions(vocabulary_list_id, regenerate=True)
            
            print(f"Generated {len(questions)} questions:")
            for i, question in enumerate(questions):
                print(f"\n{i+1}. Question: {question['question_text']}")
                print(f"   Answer: {question['correct_answer']}")
                print(f"   Type: {question['question_type']}")
                print(f"   Order: {question['question_order']}")
                
        except Exception as e:
            print(f"Error generating questions: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_generation())