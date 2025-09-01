'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthSupabase } from '@/hooks/useAuthSupabase';
import { supabase } from '@/lib/supabase';
import { 
  CheckCircleIcon, 
  XCircleIcon, 
  ClockIcon, 
  ArrowLeftIcon,
  ExclamationTriangleIcon,
  AcademicCapIcon,
  ChatBubbleLeftEllipsisIcon
} from '@heroicons/react/24/outline';

interface QuestionEvaluation {
  question_number: number;
  question_text: string;
  student_answer: string;
  rubric_score: number;
  points_earned: number;
  scoring_rationale: string;
  feedback: string | null;
  key_concepts: string[];
  misconceptions: string[];
  confidence: number;
}

interface TestResultDetail {
  attempt_id: string;
  assignment_id: string;
  assignment_title: string;
  student_name: string;
  overall_score: number;
  total_points: number;
  passed: boolean;
  status: string;
  submitted_at: string;
  evaluated_at: string;
  question_evaluations: QuestionEvaluation[];
  feedback_summary: string | null;
  needs_review: boolean;
}

export default function TestResultsPage({ params }: { params: { resultId: string } }) {
  const router = useRouter();
  const { user } = useAuthSupabase();
  const [testResult, setTestResult] = useState<TestResultDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedQuestions, setExpandedQuestions] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (user) {
      fetchTestResults();
    }
  }, [user]);

  const fetchTestResults = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/student/tests/results/${params.resultId}`, {
        headers: { 'Authorization': `Bearer ${session?.access_token}` }
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

  const toggleQuestionExpanded = (questionNumber: number) => {
    const newExpanded = new Set(expandedQuestions);
    if (newExpanded.has(questionNumber)) {
      newExpanded.delete(questionNumber);
    } else {
      newExpanded.add(questionNumber);
    }
    setExpandedQuestions(newExpanded);
  };

  const getRubricLabel = (score: number): string => {
    switch (score) {
      case 4: return 'Excellent';
      case 3: return 'Good';
      case 2: return 'Fair';
      case 1: return 'Poor';
      case 0: return 'No Credit';
      default: return 'Unknown';
    }
  };

  const getRubricColor = (score: number): string => {
    switch (score) {
      case 4: return 'text-green-600 bg-green-50 border-green-200';
      case 3: return 'text-blue-600 bg-blue-50 border-blue-200';
      case 2: return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 1: return 'text-orange-600 bg-orange-50 border-orange-200';
      case 0: return 'text-red-600 bg-red-50 border-red-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getOverallScoreColor = (score: number): string => {
    if (score >= 90) return 'text-green-600';
    if (score >= 80) return 'text-blue-600';
    if (score >= 70) return 'text-yellow-600';
    if (score >= 60) return 'text-orange-600';
    return 'text-red-600';
  };

  const getOverallScoreBg = (score: number): string => {
    if (score >= 90) return 'bg-green-50 border-green-200';
    if (score >= 80) return 'bg-blue-50 border-blue-200';
    if (score >= 70) return 'bg-yellow-50 border-yellow-200';
    if (score >= 60) return 'bg-orange-50 border-orange-200';
    return 'bg-red-50 border-red-200';
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return {
      date: date.toLocaleDateString(),
      time: date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
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

  const { date: submittedDate, time: submittedTime } = formatDateTime(testResult.submitted_at);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Test Results</h1>
              <p className="text-gray-600 mt-1">
                {testResult.assignment_title}
              </p>
              <p className="text-sm text-gray-500">
                Submitted on {submittedDate} at {submittedTime}
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
        {/* Review Notice */}
        {testResult.needs_review && (
          <div className="mb-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="h-5 w-5 text-amber-600 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-amber-800">Results Under Review</h3>
                <p className="text-sm text-amber-700 mt-1">
                  Your test results are being reviewed by your teacher for accuracy. Final scores may be adjusted.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Overall Score Card */}
        <div className={`rounded-lg border-2 p-6 mb-8 ${getOverallScoreBg(testResult.overall_score)}`}>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Overall Score</h2>
              <div className="flex items-center space-x-6">
                <div className="flex items-center">
                  <AcademicCapIcon className="h-5 w-5 text-gray-500 mr-2" />
                  <span className="text-gray-700">
                    {testResult.question_evaluations.length} questions
                  </span>
                </div>
                <div className="flex items-center">
                  <CheckCircleIcon className="h-5 w-5 text-gray-500 mr-2" />
                  <span className="text-gray-700">
                    {testResult.passed ? 'Passed' : 'Not Passed'}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="text-right">
              <div className={`text-4xl font-bold ${getOverallScoreColor(testResult.overall_score)}`}>
                {testResult.overall_score}/100
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

        {/* Feedback Summary */}
        {testResult.feedback_summary && (
          <div className="mb-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
            <div className="flex items-start">
              <ChatBubbleLeftEllipsisIcon className="h-5 w-5 text-blue-600 mr-3 mt-0.5" />
              <div>
                <h3 className="text-lg font-medium text-blue-900 mb-2">Summary</h3>
                <p className="text-blue-800">{testResult.feedback_summary}</p>
              </div>
            </div>
          </div>
        )}

        {/* Question Results Overview */}
        <div className="mb-8 bg-white rounded-lg shadow border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Score Breakdown</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
            {[4, 3, 2, 1, 0].map(score => {
              const count = testResult.question_evaluations.filter(q => q.rubric_score === score).length;
              return (
                <div key={score} className={`p-3 rounded-lg border ${getRubricColor(score)}`}>
                  <div className="text-xl font-bold">{count}</div>
                  <div className="text-sm">{getRubricLabel(score)}</div>
                  <div className="text-xs">({score}/4)</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Question Results */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Question-by-Question Results</h3>
          
          {testResult.question_evaluations.map((evaluation) => {
            const isExpanded = expandedQuestions.has(evaluation.question_number);
            const hasImprovement = evaluation.feedback && evaluation.rubric_score < 4;
            
            return (
              <div key={evaluation.question_number} className="bg-white rounded-lg shadow border">
                {/* Question Header - Always Visible */}
                <div 
                  className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => toggleQuestionExpanded(evaluation.question_number)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <h4 className="text-lg font-medium text-gray-900">
                        Question {evaluation.question_number}
                      </h4>
                      {hasImprovement && (
                        <div className="flex items-center text-amber-600">
                          <ChatBubbleLeftEllipsisIcon className="h-4 w-4 mr-1" />
                          <span className="text-xs font-medium">Feedback Available</span>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      <div className={`px-3 py-1 rounded-full border text-sm font-medium ${getRubricColor(evaluation.rubric_score)}`}>
                        {evaluation.points_earned}/10 pts
                      </div>
                      <div className={`px-2 py-1 rounded text-xs font-medium ${getRubricColor(evaluation.rubric_score)}`}>
                        {getRubricLabel(evaluation.rubric_score)}
                      </div>
                      <button className="text-gray-400 hover:text-gray-600">
                        {isExpanded ? '↑' : '↓'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded Content */}
                {isExpanded && (
                  <div className="px-4 pb-4 border-t bg-gray-50">
                    {/* Question Text */}
                    <div className="mb-4 pt-4">
                      <h5 className="font-medium text-gray-700 mb-2">Question:</h5>
                      <div className="bg-white rounded p-3 text-gray-800">
                        {evaluation.question_text}
                      </div>
                    </div>

                    {/* Student Answer */}
                    <div className="mb-4">
                      <h5 className="font-medium text-gray-700 mb-2">Your Answer:</h5>
                      <div className="bg-white rounded p-3">
                        <p className="text-gray-800 whitespace-pre-wrap">
                          {evaluation.student_answer || <em className="text-gray-500">No answer provided</em>}
                        </p>
                      </div>
                    </div>

                    {/* Scoring Rationale */}
                    <div className="mb-4">
                      <h5 className="font-medium text-gray-700 mb-2">Scoring Explanation:</h5>
                      <p className="text-gray-800 bg-white rounded p-3">{evaluation.scoring_rationale}</p>
                    </div>

                    {/* Feedback for Improvement */}
                    {evaluation.feedback && (
                      <div className="mb-4">
                        <h5 className="font-medium text-blue-700 mb-2">💡 How to Improve:</h5>
                        <p className="text-blue-800 bg-blue-50 rounded p-3">
                          {evaluation.feedback}
                        </p>
                      </div>
                    )}

                    {/* Key Concepts */}
                    {evaluation.key_concepts.length > 0 && (
                      <div className="mb-4">
                        <h5 className="font-medium text-green-700 mb-2">✓ Concepts You Demonstrated:</h5>
                        <div className="flex flex-wrap gap-2">
                          {evaluation.key_concepts.map((concept, idx) => (
                            <span key={idx} className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
                              {concept}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Misconceptions */}
                    {evaluation.misconceptions.length > 0 && (
                      <div>
                        <h5 className="font-medium text-red-700 mb-2">⚠️ Areas Needing Attention:</h5>
                        <div className="flex flex-wrap gap-2">
                          {evaluation.misconceptions.map((misconception, idx) => (
                            <span key={idx} className="px-2 py-1 bg-red-100 text-red-800 rounded-full text-xs">
                              {misconception}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Next Steps */}
        <div className="mt-8 bg-white rounded-lg shadow border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Next Steps</h3>
          <div className="space-y-3">
            {testResult.passed ? (
              <div className="flex items-center text-green-700">
                <CheckCircleIcon className="h-5 w-5 mr-2" />
                <span>Congratulations! You passed this test.</span>
              </div>
            ) : (
              <div className="flex items-center text-amber-700">
                <ExclamationTriangleIcon className="h-5 w-5 mr-2" />
                <span>Consider reviewing the material and trying again if allowed.</span>
              </div>
            )}
            
            <button
              onClick={() => router.push(`/student/assignment/reading/${testResult.assignment_id}`)}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Review Reading Material
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}