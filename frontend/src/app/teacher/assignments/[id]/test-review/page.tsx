'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { tokenStorage } from '@/lib/tokenStorage';
import TeacherGuard from '@/components/TeacherGuard';

interface TestQuestion {
  question: string;
  answer_key: string;
  grading_context: string;
  difficulty: number;
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
  console.log('TestReviewPage component rendering with params:', params);
  const router = useRouter();
  const { user, isLoading } = useAuth();
  console.log('User from useAuth:', !!user);
  console.log('Auth loading:', isLoading);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
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
    const token = tokenStorage.getAccessToken();
    console.log('useEffect triggered - token:', !!token, 'user:', !!user, 'isLoading:', isLoading, 'params.id:', params.id);
    if (token && user && !isLoading && !hasAttemptedFetch) {
      console.log('Token and user exist, calling fetchTest');
      setHasAttemptedFetch(true);
      fetchTest();
    } else {
      console.log('Waiting for auth - token:', !!token, 'user:', !!user, 'isLoading:', isLoading);
    }
  }, [user, isLoading, params.id, hasAttemptedFetch]);

  const fetchTest = async () => {
    try {
      const token = tokenStorage.getAccessToken();
      console.log('Fetching test for assignment:', params.id);
      console.log('API URL:', `${process.env.NEXT_PUBLIC_API_URL}/v1/tests/assignment/${params.id}`);
      console.log('Token present:', !!token);
      
      if (!token) {
        console.error('No token available');
        setError('Authentication required');
        setLoading(false);
        return;
      }
      
      // First, check if a test exists for this assignment
      // We need to query by assignment_id, not test_id
      // For now, try to fetch existing test, if not found, generate one
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/tests/assignment/${params.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);

      if (!response.ok) {
        if (response.status === 404) {
          console.log('Test not found, checking if assignment exists...');
          // First check if the assignment exists
          const assignmentCheck = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/teacher/assignments/reading/${params.id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          
          if (!assignmentCheck.ok) {
            setError('Assignment not found. Please create the assignment first.');
            return;
          }
          
          // Assignment exists, try to generate test
          await generateTest();
          return;
        }
        throw new Error('Failed to fetch test');
      }

      const data = await response.json();
      console.log('Test data received:', data);
      setTest(data);
      setTestId(data.id);
      setQuestions(data.test_questions);
      setTimeLimit(data.time_limit_minutes);
      setMaxAttempts(data.max_attempts);
      setTeacherNotes(data.teacher_notes || '');
    } catch (err) {
      console.error('Error in fetchTest:', err);
      setError('Failed to load test. The assignment may have been deleted.');
    } finally {
      console.log('Setting loading to false');
      setLoading(false);
    }
  };

  const generateTest = async () => {
    try {
      const token = tokenStorage.getAccessToken();
      console.log('Generating test for assignment:', params.id);
      
      if (!token) {
        console.error('No token available for generation');
        setError('Authentication required');
        setLoading(false);
        return;
      }
      
      // params.id is the assignment ID
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/tests/${params.id}/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      console.log('Generate response status:', response.status);
      console.log('Generate response ok:', response.ok);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Generate error response:', errorText);
        throw new Error('Failed to generate test');
      }

      const data = await response.json();
      console.log('Generated test data:', data);
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
      console.log('Setting loading to false in generateTest');
      setLoading(false);
    }
  };

  const regenerateQuestions = async () => {
    if (!testId || !confirm('This will replace all current questions with new ones. Are you sure?')) return;
    
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const token = tokenStorage.getAccessToken();
      
      // Delete the existing test
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/tests/${testId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      // Generate a new test
      await generateTest();
    } catch (err) {
      console.error('Error regenerating test:', err);
      setError('Failed to regenerate test questions');
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

    try {
      const token = tokenStorage.getAccessToken();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/tests/${testId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          questions,
          time_limit_minutes: timeLimit,
          max_attempts: maxAttempts,
          teacher_notes: teacherNotes
        })
      });

      if (!response.ok) {
        throw new Error('Failed to save test');
      }

      setSuccess('Test saved successfully!');
    } catch (err) {
      setError('Failed to save test');
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
      const token = tokenStorage.getAccessToken();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/tests/${testId}/approve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ expires_days: expirationDays })
      });

      if (!response.ok) {
        throw new Error('Failed to approve test');
      }

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

  if (loading) {
    return (
      <TeacherGuard>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-lg">Loading...</div>
        </div>
      </TeacherGuard>
    );
  }

  if (!test) {
    return (
      <TeacherGuard>
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
      </TeacherGuard>
    );
  }

  return (
    <TeacherGuard>
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
                  onChange={(e) => setTimeLimit(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label htmlFor="maxAttempts" className="block text-sm font-medium text-gray-700 mb-1">
                  Maximum Attempts
                </label>
                <select
                  id="maxAttempts"
                  value={maxAttempts}
                  onChange={(e) => setMaxAttempts(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                onChange={(e) => setTeacherNotes(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                  <button
                    onClick={() => removeQuestion(index)}
                    className="text-red-600 hover:text-red-700 p-2"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Question Text</label>
                  <textarea
                    value={question.question}
                    onChange={(e) => updateQuestion(index, 'question', e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Answer Key
                    <span className="text-xs text-gray-500 ml-2">(What students should include in their answer)</span>
                  </label>
                  <textarea
                    value={question.answer_key}
                    onChange={(e) => updateQuestion(index, 'answer_key', e.target.value)}
                    rows={3}
                    placeholder="Example: Student should explain that the protagonist felt lonely because they moved to a new city and left all their friends behind, as described in paragraph 3."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Grading Context
                    <span className="text-xs text-gray-500 ml-2">(Relevant text passages for evaluating the answer)</span>
                  </label>
                  <textarea
                    value={question.grading_context}
                    onChange={(e) => updateQuestion(index, 'grading_context', e.target.value)}
                    rows={3}
                    placeholder='Example: "Sarah stared out the window of her new apartment, the unfamiliar skyline reminding her of how far she was from everyone she loved." (Paragraph 3)'
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Difficulty Level</label>
                  <select
                    value={question.difficulty}
                    onChange={(e) => updateQuestion(index, 'difficulty', parseInt(e.target.value))}
                    className="w-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          <button
            onClick={addQuestion}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 flex items-center"
          >
            + Add Question
          </button>
          {test.status === 'draft' && (
            <button
              onClick={regenerateQuestions}
              disabled={loading}
              className="px-4 py-2 border border-amber-300 text-amber-700 rounded-md hover:bg-amber-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              🔄 Regenerate All Questions
            </button>
          )}
          <div className="flex-1" />
          <button
            onClick={() => router.push('/teacher/uma-read')}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={saveTest}
            disabled={saving || test.status !== 'draft'}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save Draft
          </button>
          <button
            onClick={approveTest}
            disabled={saving || test.status !== 'draft' || questions.length === 0}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Processing...' : 'Approve Test'}
          </button>
        </div>
      </div>
    </TeacherGuard>
  );
}