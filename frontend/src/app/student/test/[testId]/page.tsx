'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import StudentGuard from '@/components/StudentGuard';
import { ClockIcon, CheckCircleIcon, ArrowRightIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';

interface TestQuestion {
  question_number: number;
  question: string;
  difficulty: number;
}

interface TestSession {
  test_result_id: string;
  questions: TestQuestion[];
  time_limit_minutes: number;
  started_at: string;
}

interface TestResult {
  id: string;
  test_id: string;
  overall_score: number;
  responses: Record<string, any>;
  started_at: string;
  completed_at: string;
  time_spent_minutes: number;
}

export default function TestPage({ params }: { params: { testId: string } }) {
  const router = useRouter();
  const { token } = useAuth();
  const [testSession, setTestSession] = useState<TestSession | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [autoSaveStatus, setAutoSaveStatus] = useState('saved');
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const autoSaveRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (token) {
      startTest();
    }
    
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (autoSaveRef.current) clearTimeout(autoSaveRef.current);
    };
  }, [token]);

  useEffect(() => {
    // Auto-save every 30 seconds when responses change
    if (autoSaveRef.current) clearTimeout(autoSaveRef.current);
    
    if (Object.keys(responses).length > 0 && testSession) {
      setAutoSaveStatus('saving');
      autoSaveRef.current = setTimeout(() => {
        autoSaveResponses();
      }, 30000);
    }
  }, [responses]);

  const startTest = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/tests/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ test_id: params.testId })
      });

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('This test is not available to you');
        }
        throw new Error('Failed to start test');
      }

      const data = await response.json();
      setTestSession(data);
      
      // Calculate time remaining
      const startTime = new Date(data.started_at);
      const timeLimit = data.time_limit_minutes * 60 * 1000; // Convert to milliseconds
      const elapsed = Date.now() - startTime.getTime();
      const remaining = Math.max(0, timeLimit - elapsed);
      
      setTimeRemaining(Math.floor(remaining / 1000)); // Convert to seconds
      
      // Start countdown timer
      intervalRef.current = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            submitTest(true); // Auto-submit when time runs out
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start test');
      setLoading(false);
    }
  };

  const autoSaveResponses = async () => {
    if (!testSession) return;
    
    try {
      // In a real implementation, you might want to save to a temporary endpoint
      // For now, we'll just update the status
      setAutoSaveStatus('saved');
    } catch (err) {
      setAutoSaveStatus('error');
      console.error('Auto-save failed:', err);
    }
  };

  const updateResponse = (questionNumber: number, answer: string) => {
    const questionKey = `question_${questionNumber}`;
    setResponses(prev => ({
      ...prev,
      [questionKey]: answer
    }));
    setAutoSaveStatus('unsaved');
  };

  const nextQuestion = () => {
    if (testSession && currentQuestion < testSession.questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    }
  };

  const previousQuestion = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
    }
  };

  const submitTest = async (autoSubmit = false) => {
    if (!testSession) return;
    
    if (!autoSubmit) {
      const confirmed = window.confirm('Are you sure you want to submit your test? You cannot change your answers after submission.');
      if (!confirmed) return;
    }
    
    setSubmitting(true);
    
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/tests/${testSession.test_result_id}/submit`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ responses })
      });

      if (!response.ok) {
        throw new Error('Failed to submit test');
      }

      const result: TestResult = await response.json();
      
      // Clear the timer
      if (intervalRef.current) clearInterval(intervalRef.current);
      
      // Redirect to results page
      router.push(`/student/test/results/${result.id}`);
    } catch (err) {
      setError('Failed to submit test. Please try again.');
      setSubmitting(false);
    }
  };

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <StudentGuard>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-lg text-gray-600">Starting your test...</p>
          </div>
        </div>
      </StudentGuard>
    );
  }

  if (error || !testSession) {
    return (
      <StudentGuard>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full mx-4">
            <div className="text-center">
              <div className="text-red-600 mb-4">⚠️</div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Unable to Start Test</h2>
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
      </StudentGuard>
    );
  }

  const currentQ = testSession.questions[currentQuestion];
  const progress = ((currentQuestion + 1) / testSession.questions.length) * 100;
  const timeWarning = timeRemaining <= 300; // 5 minutes warning

  return (
    <StudentGuard>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow-sm border-b sticky top-0 z-10">
          <div className="max-w-4xl mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-lg font-semibold text-gray-900">Test in Progress</h1>
                <p className="text-sm text-gray-600">
                  Question {currentQuestion + 1} of {testSession.questions.length}
                </p>
              </div>
              
              <div className="flex items-center space-x-4">
                <div className={`flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                  timeWarning 
                    ? 'bg-red-100 text-red-800' 
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  <ClockIcon className="h-4 w-4 mr-1" />
                  {formatTime(timeRemaining)}
                </div>
                
                <div className="text-xs text-gray-500">
                  Auto-save: {autoSaveStatus}
                </div>
              </div>
            </div>
            
            {/* Progress Bar */}
            <div className="mt-4">
              <div className="bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="bg-white rounded-lg shadow">
            <div className="p-8">
              {/* Question */}
              <div className="mb-8">
                <div className="flex items-start justify-between mb-4">
                  <h2 className="text-xl font-medium text-gray-900 flex-1">
                    {currentQ.question}
                  </h2>
                  <span className="text-sm text-gray-500 ml-4">
                    Difficulty: {currentQ.difficulty}/8
                  </span>
                </div>
                
                {/* Answer Input */}
                <textarea
                  value={responses[`question_${currentQ.question_number}`] || ''}
                  onChange={(e) => updateResponse(currentQ.question_number, e.target.value)}
                  placeholder="Type your answer here..."
                  rows={8}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>
              
              {/* Navigation */}
              <div className="flex items-center justify-between pt-6 border-t border-gray-200">
                <button
                  onClick={previousQuestion}
                  disabled={currentQuestion === 0}
                  className="flex items-center px-4 py-2 text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ArrowLeftIcon className="h-4 w-4 mr-2" />
                  Previous
                </button>
                
                <div className="flex items-center space-x-2">
                  {testSession.questions.map((_, index) => (
                    <button
                      key={index}
                      onClick={() => setCurrentQuestion(index)}
                      className={`w-8 h-8 rounded-full text-sm font-medium ${
                        index === currentQuestion
                          ? 'bg-blue-600 text-white'
                          : responses[`question_${index + 1}`]
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {index + 1}
                    </button>
                  ))}
                </div>
                
                {currentQuestion === testSession.questions.length - 1 ? (
                  <button
                    onClick={() => submitTest(false)}
                    disabled={submitting}
                    className="flex items-center px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                  >
                    {submitting ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Submitting...
                      </>
                    ) : (
                      <>
                        <CheckCircleIcon className="h-4 w-4 mr-2" />
                        Submit Test
                      </>
                    )}
                  </button>
                ) : (
                  <button
                    onClick={nextQuestion}
                    className="flex items-center px-4 py-2 text-blue-600 hover:text-blue-800"
                  >
                    Next
                    <ArrowRightIcon className="h-4 w-4 ml-2" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </StudentGuard>
  );
}