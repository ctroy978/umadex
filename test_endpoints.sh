#!/bin/bash

# Test script to verify the test endpoints are working
echo "Testing test endpoints..."

# Check if the backend is running
echo "1. Checking backend health..."
curl -s http://localhost:8000/health | jq .

# Check the API routes
echo -e "\n2. Checking student tests routes..."
curl -s http://localhost:8000/openapi.json | jq '.paths | keys[] | select(contains("/student/tests"))'

echo -e "\nEndpoints should now be working. Try the UMARead test completion flow again."
echo "The database has been updated with:"
echo "- Added missing columns to test_question_evaluations table"
echo "- Updated student_test_attempts constraints"
echo "- Created migration file 013_fix_test_question_evaluations_columns.sql"
echo "- Updated the consolidated schema for persistence"