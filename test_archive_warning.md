# Test Instructions for Archive Warning Dialog

## Summary
Added a user-friendly warning dialog when attempting to archive a UmaWrite assignment that's attached to classrooms.

## Changes Made:
1. Added Dialog component imports from `/components/ui/dialog`
2. Added `errorDialog` state to manage dialog visibility
3. Updated `handleArchive` function to show dialog instead of browser alert
4. Added Dialog component to display the warning message

## How to Test:
1. Go to http://localhost/teacher/uma-write
2. Find an assignment that shows "1 classroom" or more in the assignment card
3. Click the archive button (box with down arrow icon)
4. You should see a proper dialog with:
   - Title: "Cannot Archive Assignment"
   - Warning icon
   - Detailed message explaining why it can't be archived
   - Instructions to remove from classrooms first
   - "Got it" button to close the dialog

## Expected Behavior:
- For assignments with 0 classrooms: Should show confirmation prompt then archive
- For assignments with 1+ classrooms: Should show the new warning dialog
- If backend returns an error: Should show the error message in the dialog

## Previous Behavior:
- Used basic browser `alert()` which was easy to miss
- No clear explanation of what to do next