'use client';

import { useState, useEffect } from 'react';
import { UserIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline';
import { api } from '@/lib/api';

interface Student {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
}

interface StudentAnalyticsData {
  student: Student;
  umaread?: any;
  umavocab?: any;
  umadebate?: any;
  umawrite?: any;
  umatest?: any;
  insufficient_data?: boolean;
  message?: string;
}

export default function StudentAnalysis() {
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<string>('');
  const [analyticsData, setAnalyticsData] = useState<StudentAnalyticsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Fetch all students
  useEffect(() => {
    const fetchStudents = async () => {
      try {
        const response = await api.get('/v1/teacher/students');
        setStudents(response.data);
      } catch (error) {
        console.error('Error fetching students:', error);
      }
    };

    fetchStudents();
  }, []);

  // Fetch analytics data for selected student
  const fetchAnalytics = async () => {
    if (!selectedStudent) return;
    
    setLoading(true);
    try {
      const response = await api.get(`/v1/teacher/student-analytics/${selectedStudent}`);
      setAnalyticsData(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  // Export data with AI prompt
  const exportData = () => {
    if (!analyticsData || analyticsData.insufficient_data) return;
    
    setExporting(true);
    
    const aiPrompt = `# Student Performance Analysis Request

You are analyzing educational performance data for a student. Please provide insights on their learning patterns, strengths, weaknesses, and specific recommendations for improvement.

## Data Overview
- Student: ${analyticsData.student.first_name} ${analyticsData.student.last_name}
- Modules: UMARead (reading comprehension), UMAVocab (vocabulary), UMADebate (argumentation), UMAWrite (writing), UMATest (assessments)
- Time Period: Various dates included in the data

## Analysis Tasks
1. Identify the student's primary areas of struggle across all modules
2. Highlight areas where the student excels or shows consistent improvement
3. Analyze learning patterns and progression over time
4. Identify specific misconceptions or repeated errors
5. Recommend targeted interventions and learning strategies
6. Suggest which skills should be prioritized for remediation
7. Note any concerning patterns that may indicate learning difficulties

## Important Note for Teachers
**Privacy Warning:** Remove or redact any sensitive information before sharing. This data contains student performance metrics and should be handled according to your institution's privacy policies.

---

## STUDENT PERFORMANCE DATA

`;

    const dataString = aiPrompt + JSON.stringify(analyticsData, null, 2);
    
    // Create blob and download
    const blob = new Blob([dataString], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `student_analysis_${analyticsData.student.last_name}_${analyticsData.student.first_name}_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    setExporting(false);
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Student Analysis</h2>
      
      {/* Student Selection */}
      <div className="mb-8">
        <label htmlFor="student-select" className="block text-sm font-medium text-gray-700 mb-2">
          Select a Student
        </label>
        <div className="flex gap-4">
          <select
            id="student-select"
            value={selectedStudent}
            onChange={(e) => setSelectedStudent(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">Choose a student...</option>
            {students.map((student) => (
              <option key={student.id} value={student.id}>
                {student.last_name}, {student.first_name} - {student.email}
              </option>
            ))}
          </select>
          <button
            onClick={fetchAnalytics}
            disabled={!selectedStudent || loading}
            className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Loading...' : 'Load Analytics'}
          </button>
        </div>
      </div>

      {/* Analytics Display */}
      {analyticsData && (
        <div className="space-y-6">
          {/* Check for insufficient data */}
          {analyticsData.insufficient_data ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
              <div className="flex items-center">
                <UserIcon className="h-12 w-12 text-yellow-600 mr-4" />
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {analyticsData.student.first_name} {analyticsData.student.last_name}
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">{analyticsData.message}</p>
                </div>
              </div>
            </div>
          ) : (
            <>
          {/* Student Info */}
          <div className="bg-gray-50 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <UserIcon className="h-12 w-12 text-gray-400 mr-4" />
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {analyticsData.student.first_name} {analyticsData.student.last_name}
                  </h3>
                  <p className="text-sm text-gray-600">{analyticsData.student.email}</p>
                </div>
              </div>
              <button
                onClick={exportData}
                disabled={exporting}
                className="flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
                {exporting ? 'Exporting...' : 'Export for AI Analysis'}
              </button>
            </div>
          </div>

          {/* Module Summaries */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* UMARead Summary */}
            {analyticsData.umaread && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h4 className="font-semibold text-gray-900 mb-3">UMARead Performance</h4>
                <div className="space-y-2 text-sm">
                  <p>Assignments Completed: {analyticsData.umaread.assignmentsCompleted}</p>
                  <p>Average Comprehension: {analyticsData.umaread.averageComprehension}%</p>
                  <p>Total Time Spent: {analyticsData.umaread.totalTimeSpent} minutes</p>
                  <p>Difficulty Progression: Level {analyticsData.umaread.currentDifficulty}</p>
                </div>
              </div>
            )}

            {/* UMAVocab Summary */}
            {analyticsData.umavocab && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h4 className="font-semibold text-gray-900 mb-3">UMAVocab Performance</h4>
                <div className="space-y-2 text-sm">
                  <p>Lists Completed: {analyticsData.umavocab.listsCompleted}</p>
                  <p>Average Test Score: {analyticsData.umavocab.averageTestScore}%</p>
                  <p>Practice Activities Done: {analyticsData.umavocab.practiceActivitiesCompleted}</p>
                  <p>Words Mastered: {analyticsData.umavocab.wordsMastered}</p>
                </div>
              </div>
            )}

            {/* UMADebate Summary */}
            {analyticsData.umadebate && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h4 className="font-semibold text-gray-900 mb-3">UMADebate Performance</h4>
                <div className="space-y-2 text-sm">
                  <p>Debates Completed: {analyticsData.umadebate.debatesCompleted}</p>
                  <p>Average Score: {analyticsData.umadebate.averageScore}%</p>
                  <p>Techniques Used: {analyticsData.umadebate.techniquesUsed}</p>
                  <p>Fallacies Identified: {analyticsData.umadebate.fallaciesIdentified}</p>
                </div>
              </div>
            )}

            {/* UMAWrite Summary */}
            {analyticsData.umawrite && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h4 className="font-semibold text-gray-900 mb-3">UMAWrite Performance</h4>
                <div className="space-y-2 text-sm">
                  <p>Assignments Completed: {analyticsData.umawrite.assignmentsCompleted}</p>
                  <p>Average Score: {analyticsData.umawrite.averageScore}/10</p>
                  <p>Average Word Count: {analyticsData.umawrite.averageWordCount}</p>
                  <p>Improvement Rate: {analyticsData.umawrite.improvementRate}%</p>
                </div>
              </div>
            )}

            {/* UMATest Summary */}
            {analyticsData.umatest && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h4 className="font-semibold text-gray-900 mb-3">UMATest Performance</h4>
                <div className="space-y-2 text-sm">
                  <p>Tests Completed: {analyticsData.umatest.testsCompleted}</p>
                  <p>Average Score: {analyticsData.umatest.averageScore}%</p>
                  <p>Pass Rate: {analyticsData.umatest.passRate}%</p>
                  <p>Avg Time per Question: {analyticsData.umatest.avgTimePerQuestion}s</p>
                </div>
              </div>
            )}
          </div>

          {/* Export Instructions */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>Export Instructions:</strong> Click the "Export for AI Analysis" button to download
              a formatted text file containing all performance data. The file includes an AI prompt that
              explains the data structure and suggests analysis questions. Simply paste the entire contents
              into your preferred AI assistant for detailed insights.
            </p>
          </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}