#!/usr/bin/env python3
"""
Test script to verify automatic tab navigation in UmaLecture
when students complete all questions in a tab.
"""

import asyncio
import json
from typing import Dict, List
import httpx

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEACHER_TOKEN = "your_teacher_token_here"  # Replace with actual token
STUDENT_TOKEN = "your_student_token_here"  # Replace with actual token

async def test_tab_navigation():
    """Test the automatic tab navigation feature"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {STUDENT_TOKEN}"}
        
        # 1. Get an existing assignment or create a test one
        print("Getting UmaLecture assignments...")
        response = await client.get(
            f"{API_BASE_URL}/student/assignments",
            headers=headers
        )
        assignments = response.json()
        
        # Find a UmaLecture assignment
        umalecture_assignment = None
        for assignment in assignments:
            if assignment.get("type") == "umalecture":
                umalecture_assignment = assignment
                break
        
        if not umalecture_assignment:
            print("No UmaLecture assignment found. Please create one first.")
            return
        
        assignment_id = umalecture_assignment["id"]
        print(f"Using assignment: {umalecture_assignment['title']}")
        
        # 2. Start the assignment
        print("\nStarting assignment...")
        response = await client.post(
            f"{API_BASE_URL}/student/umalecture/assignments/{assignment_id}/start",
            headers=headers
        )
        progress = response.json()
        lecture_id = progress["lecture_id"]
        
        # 3. Get lecture data
        print("\nGetting lecture data...")
        response = await client.get(
            f"{API_BASE_URL}/student/umalecture/lectures/{lecture_id}?assignment_id={assignment_id}",
            headers=headers
        )
        lecture_data = response.json()
        
        # 4. Get first topic
        topics = list(lecture_data["lecture_structure"]["topics"].keys())
        first_topic = topics[0] if topics else None
        
        if not first_topic:
            print("No topics found in lecture")
            return
        
        print(f"\nWorking with topic: {first_topic}")
        
        # 5. Get topic content
        response = await client.get(
            f"{API_BASE_URL}/student/umalecture/lectures/{lecture_id}/topics/{first_topic}/all-content?assignment_id={assignment_id}",
            headers=headers
        )
        topic_content = response.json()
        
        # 6. Answer questions for basic level
        basic_questions = topic_content["difficulty_levels"]["basic"]["questions"]
        print(f"\nFound {len(basic_questions)} questions in basic level")
        
        for i, question in enumerate(basic_questions):
            print(f"\nAnswering question {i+1}: {question['question'][:50]}...")
            
            # Evaluate answer
            response = await client.post(
                f"{API_BASE_URL}/student/umalecture/evaluate-response",
                headers=headers,
                json={
                    "assignment_id": assignment_id,
                    "topic_id": first_topic,
                    "difficulty": "basic",
                    "question_text": question["question"],
                    "student_answer": question.get("correct_answer", "A reasonable answer"),
                    "expected_answer": question.get("correct_answer"),
                    "includes_images": False,
                    "image_descriptions": []
                }
            )
            result = response.json()
            print(f"  Result: {'Correct' if result['is_correct'] else 'Incorrect'}")
            
            # Update progress
            await client.post(
                f"{API_BASE_URL}/student/umalecture/progress",
                headers=headers,
                json={
                    "assignment_id": assignment_id,
                    "topic_id": first_topic,
                    "tab": "basic",
                    "question_index": i,
                    "is_correct": result["is_correct"]
                }
            )
        
        print("\n✅ All basic questions completed!")
        print("The UI should now automatically switch to the intermediate tab.")
        print("\nTo test this in the browser:")
        print("1. Navigate to the UmaLecture assignment")
        print("2. Answer all questions in the basic tab")
        print("3. After the last question is answered correctly, wait 1.5 seconds")
        print("4. The intermediate tab should automatically activate")

if __name__ == "__main__":
    print("UmaLecture Tab Navigation Test")
    print("==============================")
    print("\nNote: This script simulates the API calls. To see the actual")
    print("tab navigation, you need to test in the browser.")
    print("\nMake sure to update the API tokens before running!")
    
    # Uncomment to run the test
    # asyncio.run(test_tab_navigation())