#!/usr/bin/env python3
"""Test script to verify assignment saving works correctly"""

import asyncio
import httpx
from uuid import UUID

# Test data
CLASSROOM_ID = "d121da45-d905-4758-b63d-91a33a010d45"
VOCABULARY_LIST_ID = "3ae4ddad-9faf-4d92-94ac-51d7bbf1331d"

# This would normally come from authentication
# For testing, you'd need to get a valid token
AUTH_HEADERS = {
    "Authorization": "Bearer YOUR_TOKEN_HERE"
}

API_BASE = "http://localhost:8000/api/v1"

async def test_assignment_save():
    """Test saving a vocabulary assignment to a classroom"""
    
    async with httpx.AsyncClient() as client:
        # Prepare the assignment data
        assignment_data = {
            "assignments": [
                {
                    "assignment_id": VOCABULARY_LIST_ID,
                    "assignment_type": "vocabulary",  # This should now work!
                    "start_date": None,
                    "end_date": None
                }
            ]
        }
        
        print(f"Sending request to save vocabulary assignment...")
        print(f"Data: {assignment_data}")
        
        # Make the request
        url = f"{API_BASE}/teacher/classrooms/{CLASSROOM_ID}/assignments/all"
        response = await client.put(
            url,
            json=assignment_data,
            headers=AUTH_HEADERS
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Assignment saved successfully!")
        else:
            print("❌ Failed to save assignment")
        
        return response

async def check_classroom_assignments():
    """Check what assignments are currently in the classroom"""
    
    async with httpx.AsyncClient() as client:
        url = f"{API_BASE}/teacher/classrooms/{CLASSROOM_ID}"
        response = await client.get(url, headers=AUTH_HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nClassroom has {len(data.get('assignments', []))} assignments:")
            for assignment in data.get('assignments', []):
                print(f"  - {assignment['title']} (type: {assignment['assignment_type']})")
        
        return response

if __name__ == "__main__":
    print("Testing assignment save functionality...")
    print(f"Classroom ID: {CLASSROOM_ID}")
    print(f"Vocabulary List ID: {VOCABULARY_LIST_ID}")
    
    # Note: You'll need to add proper authentication to test this
    print("\n⚠️  Note: You need to update AUTH_HEADERS with a valid token to test this")
    
    # asyncio.run(test_assignment_save())
    # asyncio.run(check_classroom_assignments())