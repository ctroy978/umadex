#!/usr/bin/env python3
import asyncio
import sys
from app.services.assignment_processor import AssignmentImageProcessor

async def main():
    if len(sys.argv) != 2:
        print("Usage: python test_process_images.py <assignment_id>")
        sys.exit(1)
    
    assignment_id = sys.argv[1]
    print(f"Processing images for assignment: {assignment_id}")
    
    processor = AssignmentImageProcessor()
    try:
        await processor.process_assignment_images(assignment_id)
        print("Image processing completed successfully")
    except Exception as e:
        print(f"Error processing images: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())