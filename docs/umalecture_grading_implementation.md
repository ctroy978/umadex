# UMALecture Grading Implementation

## Overview
This document describes the implementation of the grading system for UMALecture modules. The system uses a simple, progression-based scoring where students earn grades based on the highest difficulty level they complete.

## Grading Scale
- **Basic Level Completed**: 70%
- **Intermediate Level Completed**: 80%
- **Advanced Level Completed**: 90%
- **Expert Level Completed**: 100%

## Key Implementation Details

### 1. Grade Calculation Logic
- Students must answer all questions correctly to advance to the next difficulty level
- For Basic, Intermediate, and Advanced levels: completing the level (answering all questions correctly) automatically grants the associated grade
- For Expert level: since there's no level beyond it, the system checks if all expert questions were answered correctly
- The grade is based on the highest completed difficulty level across all topics in the lecture

### 2. Automatic Grade Updates
- Grades are automatically calculated and updated when a student completes a difficulty level
- The system triggers grade calculation in the `update_student_progress` method when all questions in a tab are answered correctly
- Gradebook entries are created or updated automatically (keeping the highest score if multiple attempts)

### 3. Database Changes
- Added 'umalecture' to the `gradebook_entries.assignment_type` constraint
- Migration file: `018_add_umalecture_to_gradebook.py`

### 4. API Endpoints
- **POST** `/api/v1/student/umalecture/assignments/{assignment_id}/calculate-grade`
  - Manually calculates and updates a student's grade for a lecture
  - Returns the calculated score and success status

### 5. Gradebook Integration
- UMALecture grades now appear in the teacher's gradebook alongside other module types
- Teachers can view, filter, and export UMALecture grades
- Grades are displayed as percentages with the same color coding as other modules

## Code Changes

### Files Modified:
1. **`/backend/app/services/umalecture.py`**
   - Added `calculate_lecture_grade()` method
   - Added `create_or_update_gradebook_entry()` method
   - Updated `update_student_progress()` to trigger automatic grading

2. **`/backend/app/api/v1/umalecture.py`**
   - Added `/calculate-grade` endpoint
   - Added necessary imports

3. **`/backend/app/api/v1/teacher_reports.py`**
   - Updated gradebook query to include UMALecture
   - Added UMALecture to assignment type filters

4. **`/backend/alembic/versions/018_add_umalecture_to_gradebook.py`**
   - New migration to update gradebook constraint

### Testing
A test script is provided at `/backend/scripts/test_umalecture_grading.py` to verify the grading implementation.

## Usage
1. Students work through UMALecture content at their own pace
2. As they complete each difficulty level, their grade is automatically updated
3. Teachers can view student progress and grades in the gradebook
4. Grades reflect the highest difficulty level completed, providing a clear measure of student achievement