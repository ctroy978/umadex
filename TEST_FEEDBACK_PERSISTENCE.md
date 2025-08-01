# Testing Feedback Persistence for Wrong Answers

## Changes Made:
1. Modified `handleSubmitAnswer` to NOT clear previous feedback when submitting a new answer
2. Modified `handleRetryAnswer` to clear feedback only when the "Try Again" button is clicked

## Expected Behavior:
1. When a student gets an answer wrong, yellow feedback appears
2. The feedback persists on screen (no fading)
3. The "Try Again" button appears alongside the feedback
4. Clicking "Try Again" clears the feedback and resets the answer field
5. The student can then enter a new answer

## Test Steps:
1. Navigate to a UMA Lecture assignment as a student
2. Answer a question incorrectly
3. Verify that yellow feedback appears and stays visible
4. Verify that a "Try Again" button is shown
5. Click "Try Again" and verify the feedback disappears
6. Enter a new answer and submit

## Code Changes Location:
- File: `/frontend/src/components/student/lecture/QuestionPanel.tsx`
- Lines modified: 80-89 (handleSubmitAnswer) and 143-156 (handleRetryAnswer)