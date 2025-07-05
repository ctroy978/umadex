#!/usr/bin/env python3
"""Test script to verify UMALecture assignment saving works correctly"""

import asyncio
import httpx
from uuid import UUID
import json

# Test data - Replace these with actual IDs from your system
CLASSROOM_ID = "YOUR_CLASSROOM_ID"
UMALECTURE_ID = "YOUR_UMALECTURE_ID"

# This would normally come from authentication
# For testing, you'd need to get a valid token
AUTH_HEADERS = {
    "Authorization": "Bearer YOUR_TOKEN_HERE"
}

API_BASE = "http://localhost:8000/api/v1"

async def test_umalecture_assignment_save():
    """Test saving a UMALecture assignment to a classroom"""
    
    async with httpx.AsyncClient() as client:
        # Prepare the assignment data
        assignment_data = {
            "assignments": [
                {
                    "assignment_id": UMALECTURE_ID,
                    "assignment_type": "UMALecture",  # This should now work correctly!
                    "start_date": None,
                    "end_date": None
                }
            ]
        }
        
        print(f"Sending request to save UMALecture assignment...")
        print(f"Data: {json.dumps(assignment_data, indent=2)}")
        
        # Make the request
        url = f"{API_BASE}/teacher/classrooms/{CLASSROOM_ID}/assignments/all"
        response = await client.put(
            url,
            json=assignment_data,
            headers=AUTH_HEADERS
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ UMALecture assignment saved successfully!")
        else:
            print("❌ Failed to save UMALecture assignment")
        
        return response

async def check_classroom_assignments():
    """Check what assignments are currently in the classroom"""
    
    async with httpx.AsyncClient() as client:
        # Check via the teacher detail endpoint
        url = f"{API_BASE}/teacher/classrooms/{CLASSROOM_ID}/assignments/all"
        response = await client.get(url, headers=AUTH_HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nClassroom has {len(data)} assignments:")
            for assignment in data:
                print(f"  - {assignment['title']} (type: {assignment['assignment_type']})")
                if assignment['assignment_type'] == 'UMALecture':
                    print("    ✅ UMALecture assignment found!")
        
        return response

async def get_available_umalectures():
    """Get list of available UMALecture assignments"""
    
    async with httpx.AsyncClient() as client:
        url = f"{API_BASE}/teacher/classrooms/{CLASSROOM_ID}/assignments/available/all"
        params = {
            "assignment_type": "UMALecture",
            "page": 1,
            "per_page": 10
        }
        
        response = await client.get(url, headers=AUTH_HEADERS, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nFound {data['total_count']} UMALecture assignments:")
            for assignment in data['assignments']:
                print(f"  - ID: {assignment['id']}")
                print(f"    Title: {assignment['assignment_title']}")
                print(f"    Type: {assignment['assignment_type']}")
                print(f"    Is Assigned: {assignment['is_assigned']}")
                print()
        
        return response

if __name__ == "__main__":
    print("Testing UMALecture assignment functionality...")
    print(f"Classroom ID: {CLASSROOM_ID}")
    print(f"UMALecture ID: {UMALECTURE_ID}")
    
    print("\n⚠️  Note: You need to update the following before running:")
    print("1. CLASSROOM_ID - Replace with an actual classroom ID")
    print("2. UMALECTURE_ID - Replace with an actual UMALecture assignment ID")
    print("3. AUTH_HEADERS - Add a valid authentication token")
    
    # Uncomment these lines after adding the required IDs and token:
    # asyncio.run(get_available_umalectures())
    # asyncio.run(test_umalecture_assignment_save())
    # asyncio.run(check_classroom_assignments())