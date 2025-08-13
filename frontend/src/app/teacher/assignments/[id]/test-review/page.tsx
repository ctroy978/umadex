'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthSupabase } from '@/hooks/useAuthSupabase';
import { apiRequest } from '@/lib/api';

interface TestQuestion {
  question: string;
  answer_key: string;
  grading_context: string;
  difficulty: number;
  answer_explanation?: string;
  evaluation_criteria?: string;
  [key: string]: any; // Allow for any additional fields from backend
}

interface TestData {
  id: string;
  assignment_id: string;
  assignment_title: string;
  status: string;
  test_questions: TestQuestion[];
  time_limit_minutes: number;
  max_attempts: number;
  teacher_notes?: string;
  expires_at?: string;
  created_at: string;
}

export default function TestReviewPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { user, isLoading } = useAuthSupabase();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [test, setTest] = useState<TestData | null>(null);
  const [testId, setTestId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<TestQuestion[]>([]);
  const [timeLimit, setTimeLimit] = useState(60);
  const [maxAttempts, setMaxAttempts] = useState(1);
  const [teacherNotes, setTeacherNotes] = useState('');
  const [expirationDays, setExpirationDays] = useState(30);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [hasAttemptedFetch, setHasAttemptedFetch] = useState(false);

  useEffect(() => {
    if (user && !isLoading && !hasAttemptedFetch) {
      setHasAttemptedFetch(true);
      fetchTest();
    } else if (!isLoading && !user) {
      // User is not authenticated
      setError('Please login to access this page');
      setLoading(false);
    }
  }, [user, isLoading, params.id, hasAttemptedFetch]);

  const fetchTest = async () => {
    try {
      // First, check if a test exists for this assignment
      // We need to query by assignment_id, not test_id
      // For now, try to fetch existing test, if not found, generate one
      try {
        const data = await apiRequest<TestData>(`/v1/tests/assignment/${params.id}`);
        setTest(data);
        setTestId(data.id);
        setQuestions(data.test_questions);
        setTimeLimit(data.time_limit_minutes);
        setMaxAttempts(data.max_attempts);
        setTeacherNotes(data.teacher_notes || '');
      } catch (error: any) {
        if (error.response?.status === 404 || error.message?.includes('404')) {
          // First check if the assignment exists
          try {
            await apiRequest(`/v1/teacher/assignments/reading/${params.id}`);
            // Assignment exists, try to generate test
            await generateTest();
            return;
          } catch (assignmentError: any) {
            if (assignmentError.response?.status === 404 || assignmentError.message?.includes('404')) {
              setError('Assignment not found. Please create the assignment first.');
            } else {
              throw assignmentError;
            }
            return;
          }
        } else {
          throw error;
        }
      }
    } catch (err) {
      console.error('Error in fetchTest:', err);
      setError('Failed to load test. The assignment may have been deleted.');
    } finally {
      setLoading(false);
    }
  };

  const generateTest = async () => {
    try {
      // params.id is the assignment ID
      const data = await apiRequest<TestData>(`/v1/tests/${params.id}/generate`, {
        method: 'POST',
        timeout: 120000 // 2 minutes timeout for Gemini API
      });

      setTest(data);
      setTestId(data.id);
      setQuestions(data.test_questions);
      setTimeLimit(data.time_limit_minutes);
      setMaxAttempts(data.max_attempts);
      setTeacherNotes(data.teacher_notes || '');
      setSuccess('Test generated successfully!');
    } catch (err) {
      console.error('Error in generateTest:', err);
      setError('Failed to generate test. The assignment may not exist.');
    } finally {
      setLoading(false);
    }
  };

  const regenerateQuestions = async () => {
    if (!testId || !confirm('This will replace all current questions with new ones. Are you sure?')) return;
    
    setRegenerating(true);
    setLoading(true); // Show loading screen
    setError('');
    setSuccess('');

    try {
      // Delete the existing test
      await apiRequest(`/v1/tests/${testId}`, {
        method: 'DELETE'
      });

      // Clear the testId to ensure the page knows the test was deleted
      setTestId(null);
      // Don't clear test here - keep it for UI display during regeneration

      // Small delay to ensure database transaction completes
      await new Promise(resolve => setTimeout(resolve, 500));

      // Generate a new test
      await generateTest();
      setSuccess('Test questions regenerated successfully!');
    } catch (err) {
      console.error('Error regenerating test:', err);
      setError('Failed to regenerate test questions. Please try again.');
    } finally {
      setRegenerating(false);
      setLoading(false);
    }
  };

  const updateQuestion = (index: number, field: keyof TestQuestion, value: string | number) => {
    const updatedQuestions = [...questions];
    updatedQuestions[index] = {
      ...updatedQuestions[index],
      [field]: value
    };
    setQuestions(updatedQuestions);
    // Clear success message when user makes changes
    if (success) setSuccess('');
  };

  const addQuestion = () => {
    setQuestions([...questions, {
      question: '',
      answer_key: '',
      grading_context: '',
      difficulty: 5
    }]);
  };

  const removeQuestion = (index: number) => {
    setQuestions(questions.filter((_, i) => i !== index));
  };

  const saveTest = async () => {
    if (!testId) return;
    
    setSaving(true);
    setError('');
    setSuccess('');

    // Validate questions before sending
    const invalidQuestions = questions.filter((q, index) => {
      if (!q.question || !q.answer_key || !q.grading_context) {
        return true;
      }
      return false;
    });

    if (invalidQuestions.length > 0) {
      setError('Please fill in all required fields for each question (question text, answer key, and grading context)');
      setSaving(false);
      return;
    }

    try {
      // Ensure questions have the correct structure
      const formattedQuestions = questions.map(q => ({
        question: String(q.question || ''),
        answer_key: String(q.answer_key || ''),
        grading_context: String(q.grading_context || ''),
        difficulty: Number(q.difficulty) || 5,
        // Include optional fields if they exist
        ...(q.answer_explanation && { answer_explanation: String(q.answer_explanation) }),
        ...(q.evaluation_criteria && { evaluation_criteria: String(q.evaluation_criteria) })
      }));
      
      const payload = {
        questions: formattedQuestions,
        time_limit_minutes: timeLimit,
        max_attempts: maxAttempts,
        teacher_notes: teacherNotes
      };
      console.log('Sending payload:', payload);
      console.log('Formatted questions:', formattedQuestions);
      
      await apiRequest(`/v1/tests/${testId}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      });

      setSuccess('Test saved successfully!');
      
      // Clear success message after 3 seconds
      setTimeout(() => {
        setSuccess('');
      }, 3000);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to save test');
      }
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const approveTest = async () => {
    if (!testId) return;
    
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      // First save any changes
      await saveTest();

      // Then approve
      await apiRequest(`/v1/tests/${testId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ expires_days: expirationDays })
      });

      setSuccess('Test approved! Students can now take this test.');
      setTimeout(() => {
        router.push('/teacher/uma-read');
      }, 2000);
    } catch (err) {
      setError('Failed to approve test');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading || regenerating) {
    return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="inline-block animate-spin text-4xl mb-4">⟳</div>
            <div className="text-lg">{regenerating ? 'Regenerating test questions...' : 'Loading test...'}</div>
            <div className="text-sm text-gray-500 mt-2">{regenerating ? 'This may take up to 2 minutes' : 'Please wait...'}</div>
          </div>
        </div>
    );
  }

  if (!test) {
    return (
        <div className="container mx-auto p-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 mb-2">{error || 'Test not found'}</p>
            <button
              onClick={() => router.push('/teacher/uma-read')}
              className="text-blue-600 hover:text-blue-700 underline"
            >
              Return to UMARead assignments
            </button>
          </div>
        </div>
    );
  }

  return (
      <div className="container mx-auto p-4 max-w-6xl">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Test Review</h1>
          <p className="text-gray-600">Assignment: {test.assignment_title}</p>
          <p className="text-sm text-gray-500">Status: {test.status}</p>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {success && (
          <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-green-800">{success}</p>
          </div>
        )}

        {test.status === 'approved' && (
          <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-blue-800">This test has been approved and is available for students. You cannot make changes to an approved test.</p>
          </div>
        )}

        {/* Test Settings */}
        <div className="mb-6 bg-white rounded-lg shadow border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold">Test Settings</h2>
          </div>
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label htmlFor="timeLimit" className="block text-sm font-medium text-gray-700 mb-1">
                  Time Limit (minutes)
                </label>
                <input
                  id="timeLimit"
                  type="number"
                  min="10"
                  max="180"
                  value={timeLimit}
                  onChange={(e) => {
                    setTimeLimit(parseInt(e.target.value));
                    if (success) setSuccess('');
                  }}
                  disabled={test.status !== 'draft'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
              <div>
                <label htmlFor="maxAttempts" className="block text-sm font-medium text-gray-700 mb-1">
                  Maximum Attempts
                </label>
                <select
                  id="maxAttempts"
                  value={maxAttempts}
                  onChange={(e) => {
                    setMaxAttempts(parseInt(e.target.value));
                    if (success) setSuccess('');
                  }}
                  disabled={test.status !== 'draft'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  <option value="1">1 attempt</option>
                  <option value="2">2 attempts</option>
                  <option value="3">3 attempts</option>
                </select>
              </div>
              <div>
                <label htmlFor="expiration" className="block text-sm font-medium text-gray-700 mb-1">
                  Expiration (days after approval)
                </label>
                <input
                  id="expiration"
                  type="number"
                  min="1"
                  max="365"
                  value={expirationDays}
                  onChange={(e) => setExpirationDays(parseInt(e.target.value))}
                  disabled={test.status !== 'draft'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
            </div>
            <div>
              <label htmlFor="teacherNotes" className="block text-sm font-medium text-gray-700 mb-1">
                Teacher Notes (optional)
              </label>
              <textarea
                id="teacherNotes"
                placeholder="Any notes about this test..."
                value={teacherNotes}
                onChange={(e) => {
                  setTeacherNotes(e.target.value);
                  if (success) setSuccess('');
                }}
                rows={3}
                disabled={test.status !== 'draft'}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>
          </div>
        </div>

        {/* Questions */}
        <div className="space-y-4 mb-6">
          {questions.map((question, index) => (
            <div key={index} className="bg-white rounded-lg shadow border border-gray-200">
              <div className="p-6 border-b border-gray-200">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold">Question {index + 1}</h3>
                  {test.status === 'draft' && (
                    <button
                      onClick={() => removeQuestion(index)}
                      className="text-red-600 hover:text-red-700 p-2"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Question Text <span className="text-red-500">*</span></label>
                  <textarea
                    value={question.question}
                    onChange={(e) => updateQuestion(index, 'question', e.target.value)}
                    rows={2}
                    disabled={test.status !== 'draft'}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Answer Key <span className="text-red-500">*</span>
                    <span className="text-xs text-gray-500 ml-2">(What students should include in their answer)</span>
                  </label>
                  <textarea
                    value={question.answer_key}
                    onChange={(e) => updateQuestion(index, 'answer_key', e.target.value)}
                    rows={3}
                    disabled={test.status !== 'draft'}
                    placeholder="Example: Student should explain that the protagonist felt lonely because they moved to a new city and left all their friends behind, as described in paragraph 3."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Grading Context <span className="text-red-500">*</span>
                    <span className="text-xs text-gray-500 ml-2">(Relevant text passages for evaluating the answer)</span>
                  </label>
                  <textarea
                    value={question.grading_context}
                    onChange={(e) => updateQuestion(index, 'grading_context', e.target.value)}
                    rows={3}
                    disabled={test.status !== 'draft'}
                    placeholder='Example: "Sarah stared out the window of her new apartment, the unfamiliar skyline reminding her of how far she was from everyone she loved." (Paragraph 3)'
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm disabled:bg-gray-100 disabled:cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Difficulty Level</label>
                  <select
                    value={question.difficulty}
                    onChange={(e) => updateQuestion(index, 'difficulty', parseInt(e.target.value))}
                    disabled={test.status !== 'draft'}
                    className="w-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8].map(level => (
                      <option key={level} value={level}>
                        Level {level}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col md:flex-row gap-4">
          {test.status === 'draft' && (
            <button
              onClick={addQuestion}
              className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 flex items-center"
            >
              + Add Question
            </button>
          )}
          {test.status === 'draft' && (
            <button
              onClick={regenerateQuestions}
              disabled={regenerating || loading}
              className="px-4 py-2 border border-amber-300 text-amber-700 rounded-md hover:bg-amber-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {regenerating ? (
                <>
                  <span className="inline-block animate-spin">⟳</span>
                  Regenerating Questions...
                </>
              ) : (
                <>
                  🔄 Regenerate All Questions
                </>
              )}
            </button>
          )}
          <div className="flex-1" />
          <button
            onClick={() => router.push('/teacher/uma-read')}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          {test.status === 'draft' && (
            <button
              onClick={saveTest}
              disabled={saving}
              className={`px-4 py-2 border rounded-md transition-all duration-200 ${
                success.includes('saved') 
                  ? 'border-green-500 bg-green-50 text-green-700' 
                  : 'border-gray-300 hover:bg-gray-50'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {saving ? 'Saving...' : success.includes('saved') ? '✓ Saved' : 'Save Draft'}
            </button>
          )}
          {test.status === 'draft' && (
            <button
              onClick={approveTest}
              disabled={saving || questions.length === 0}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Processing...' : 'Approve Test'}
            </button>
          )}
        </div>
      </div>
  );
}