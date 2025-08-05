#!/usr/bin/env python3
"""
Test script to verify UMALecture question generation is working correctly
"""
import asyncio
import sys
import os
sys.path.append('/app')

from app.services.umalecture_ai import UMALectureAIService

async def test_question_generation():
    """Test the structured question generation"""
    service = UMALectureAIService()
    
    # Test content
    test_topic = "Photosynthesis"
    test_content = """
    Photosynthesis is the process by which plants convert light energy into chemical energy. 
    This process takes place in the chloroplasts, which contain chlorophyll - the green pigment 
    that captures light energy. During photosynthesis, plants take in carbon dioxide from the air 
    and water from the soil. Using sunlight, they convert these raw materials into glucose (sugar) 
    and oxygen. The glucose provides energy for the plant, while oxygen is released into the 
    atmosphere as a byproduct. This process is essential for life on Earth, as it produces the 
    oxygen we breathe and forms the base of most food chains.
    """
    
    difficulties = ["basic", "intermediate", "advanced", "expert"]
    
    for difficulty in difficulties:
        print(f"\n{'='*60}")
        print(f"Testing {difficulty} level questions for: {test_topic}")
        print(f"{'='*60}")
        
        try:
            questions = await service._generate_questions_structured(
                test_topic,
                test_content,
                difficulty,
                with_images=False
            )
            
            print(f"\nGenerated {len(questions)} questions:")
            for i, q in enumerate(questions, 1):
                print(f"\nQuestion {i}:")
                print(f"  Text: {q['question']}")
                print(f"  Answer: {q['correct_answer']}")
                print(f"  Type: {q['question_type']}")
                print(f"  Uses Images: {q['uses_images']}")
                
        except Exception as e:
            print(f"Error generating questions: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n\nTest completed!")

if __name__ == "__main__":
    asyncio.run(test_question_generation())