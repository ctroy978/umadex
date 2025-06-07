'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { CheckCircleIcon, XCircleIcon, ClockIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';

interface QuestionResult {
  student_answer: string;
  ai_score: number;
  ai_justification: string;
  what_was_good: string;
  what_was_missing: string;
}

interface TestResult {
  id: string;
  test_id: string;
  overall_score: number;
  responses: Record<string, QuestionResult>;
  started_at: string;
  completed_at: string;
  time_spent_minutes: number;
}

export default function TestResultsPage({ params }: { params: { resultId: string } }) {
  const router = useRouter();
  const { token } = useAuth();
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (token) {
      fetchTestResults();
    }
  }, [token]);

  const fetchTestResults = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/tests/results/${params.resultId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Test results not found');
        }
        throw new Error('Failed to load test results');
      }

      const data = await response.json();
      setTestResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load test results');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 80) return 'text-blue-600';
    if (score >= 70) return 'text-yellow-600';
    if (score >= 60) return 'text-orange-600';
    return 'text-red-600';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 90) return 'bg-green-50 border-green-200';
    if (score >= 80) return 'bg-blue-50 border-blue-200';
    if (score >= 70) return 'bg-yellow-50 border-yellow-200';
    if (score >= 60) return 'bg-orange-50 border-orange-200';
    return 'bg-red-50 border-red-200';
  };

  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  if (loading) {
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-lg text-gray-600">Loading your results...</p>
          </div>
        </div>
    );
  }

  if (error || !testResult) {
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full mx-4">
            <div className="text-center">
              <XCircleIcon className="h-12 w-12 text-red-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Unable to Load Results</h2>
              <p className="text-gray-600 mb-6">{error || 'An unexpected error occurred'}</p>
              <button
                onClick={() => router.push('/student/dashboard')}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Return to Dashboard
              </button>
            </div>
          </div>
        </div>
    );
  }

  const questionResults = Object.entries(testResult.responses).map(([key, result]) => ({
    questionNumber: parseInt(key.replace('question_', '')),
    ...result
  })).sort((a, b) => a.questionNumber - b.questionNumber);

  return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow-sm border-b">
          <div className="max-w-4xl mx-auto px-4 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Test Results</h1>
                <p className="text-gray-600 mt-1">
                  Completed on {new Date(testResult.completed_at).toLocaleDateString()} at{' '}
                  {new Date(testResult.completed_at).toLocaleTimeString()}
                </p>
              </div>
              
              <button
                onClick={() => router.push('/student/dashboard')}
                className="flex items-center px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                <ArrowLeftIcon className="h-4 w-4 mr-2" />
                Back to Dashboard
              </button>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 py-8">
          {/* Overall Score Card */}
          <div className={`rounded-lg border-2 p-6 mb-8 ${getScoreBgColor(testResult.overall_score)}`}>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-2">Overall Score</h2>
                <div className="flex items-center space-x-6">
                  <div className="flex items-center">
                    <ClockIcon className="h-5 w-5 text-gray-500 mr-2" />
                    <span className="text-gray-700">
                      Time spent: {formatTime(testResult.time_spent_minutes)}
                    </span>
                  </div>
                  <div className="flex items-center">
                    <CheckCircleIcon className="h-5 w-5 text-gray-500 mr-2" />
                    <span className="text-gray-700">
                      {questionResults.length} questions answered
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="text-right">
                <div className={`text-4xl font-bold ${getScoreColor(testResult.overall_score)}`}>
                  {testResult.overall_score.toFixed(1)}%
                </div>
                <div className="text-gray-600 text-sm mt-1">
                  {testResult.overall_score >= 90 ? 'Excellent!' :
                   testResult.overall_score >= 80 ? 'Great job!' :
                   testResult.overall_score >= 70 ? 'Good work!' :
                   testResult.overall_score >= 60 ? 'Keep improving!' :
                   'Study more!'}
                </div>
              </div>
            </div>
          </div>

          {/* Question Results */}
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-gray-900">Question-by-Question Results</h3>
            
            {questionResults.map((result, index) => (
              <div key={result.questionNumber} className="bg-white rounded-lg shadow border">
                <div className="p-6">
                  {/* Question Header */}
                  <div className="flex items-start justify-between mb-4">
                    <h4 className="text-lg font-medium text-gray-900">
                      Question {result.questionNumber}
                    </h4>
                    <div className={`px-3 py-1 rounded-full text-sm font-medium ${getScoreBgColor(result.ai_score)}`}>
                      <span className={getScoreColor(result.ai_score)}>
                        {result.ai_score}/100
                      </span>
                    </div>
                  </div>

                  {/* Student Answer */}
                  <div className="mb-4">
                    <h5 className="font-medium text-gray-700 mb-2">Your Answer:</h5>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-gray-800 whitespace-pre-wrap">
                        {result.student_answer || <em className="text-gray-500">No answer provided</em>}
                      </p>
                    </div>
                  </div>

                  {/* AI Feedback */}
                  <div className="space-y-3">
                    <div>
                      <h5 className="font-medium text-gray-700 mb-2">Feedback:</h5>
                      <p className="text-gray-800">{result.ai_justification}</p>
                    </div>

                    {result.what_was_good && (
                      <div>
                        <h5 className="font-medium text-green-700 mb-2">✓ What you did well:</h5>
                        <p className="text-green-800 bg-green-50 rounded-lg p-3">
                          {result.what_was_good}
                        </p>
                      </div>
                    )}

                    {result.what_was_missing && (
                      <div>
                        <h5 className="font-medium text-amber-700 mb-2">→ Areas for improvement:</h5>
                        <p className="text-amber-800 bg-amber-50 rounded-lg p-3">
                          {result.what_was_missing}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="mt-8 bg-white rounded-lg shadow border p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Test Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {questionResults.length}
                </div>
                <div className="text-gray-600">Questions</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {questionResults.filter(r => r.ai_score >= 70).length}
                </div>
                <div className="text-gray-600">Above 70%</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-purple-600">
                  {formatTime(testResult.time_spent_minutes)}
                </div>
                <div className="text-gray-600">Time Spent</div>
              </div>
            </div>
          </div>
        </div>
      </div>
  );
}