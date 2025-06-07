'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { umareadApi } from '@/lib/umareadApi';
import { studentApi } from '@/lib/studentApi';
import ChunkReader from '@/components/student/umaread/ChunkReader';
import QuestionFlow from '@/components/student/umaread/QuestionFlow';
import ProgressIndicator from '@/components/student/umaread/ProgressIndicator';
import CompletionScreen from '@/components/student/umaread/CompletionScreen';
import type { 
  AssignmentStartResponse, 
  ChunkContent, 
  Question,
  StudentProgress 
} from '@/types/umaread';


export default function UMAReadAssignmentPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { id } = params;
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assignment, setAssignment] = useState<AssignmentStartResponse | null>(null);
  const [chunk, setChunk] = useState<ChunkContent | null>(null);
  const [question, setQuestion] = useState<Question | null>(null);
  const [progress, setProgress] = useState<StudentProgress | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [hasTest, setHasTest] = useState(false);

  // Initialize assignment
  useEffect(() => {
    loadAssignment();
  }, [id]);

  // Load chunk when assignment is ready
  useEffect(() => {
    if (assignment && assignment.status !== 'completed') {
      loadChunk(assignment.current_chunk);
      loadProgress();
    }
  }, [assignment]);

  // Load question automatically when chunk is loaded
  useEffect(() => {
    if (chunk && !question) {
      loadQuestion();
    }
  }, [chunk]);

  const loadAssignment = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await umareadApi.startAssignment(id);
      setAssignment(data);
      
      // Check if assignment is already complete
      if (data.status === 'completed') {
        setIsComplete(true);
        // Check if there's a test available
        try {
          const testStatus = await studentApi.getAssignmentTestStatus(id);
          setHasTest(testStatus.has_test);
        } catch (err) {
          console.error('Failed to check test status:', err);
        }
        // Show completion screen instead of trying to load chunks
        setLoading(false);
        return;
      }
    } catch (err: any) {
      console.error('Failed to load assignment:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to load assignment';
      setError(errorMessage);
      
      // Auto-retry on 500 errors
      if (err.response?.status === 500 && retryCount < 2) {
        setRetryCount(prev => prev + 1);
        setTimeout(() => {
          loadAssignment();
        }, 1000);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadChunk = async (chunkNumber: number) => {
    if (!assignment) return;
    
    try {
      setLoading(true);
      const data = await umareadApi.getChunk(id, chunkNumber);
      setChunk(data);
      setQuestion(null); // Reset question when loading new chunk
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load chunk');
    } finally {
      setLoading(false);
    }
  };

  const loadQuestion = async () => {
    if (!assignment || !chunk) return;
    
    
    try {
      setLoading(true);
      const data = await umareadApi.getCurrentQuestion(id, chunk.chunk_number);
      setQuestion(data);
    } catch (err: any) {
      console.error('Error loading question:', err.response?.data);
      if (err.response?.status === 400 && err.response?.data?.detail?.includes('already completed')) {
        // Chunk is complete, move to next
        handleNavigate('next');
      } else {
        setError(err.response?.data?.detail || 'Failed to load question');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadProgress = async () => {
    try {
      const data = await umareadApi.getProgress(id);
      setProgress(data);
    } catch (err) {
      // Progress loading is optional, don't show error
    }
  };

  const handleNavigate = (direction: 'prev' | 'next') => {
    // Navigation is now handled only through question completion
    if (!chunk) return;
    
    const newChunk = direction === 'next' 
      ? chunk.chunk_number + 1 
      : chunk.chunk_number - 1;
    
    if (newChunk >= 1 && newChunk <= chunk.total_chunks) {
      loadChunk(newChunk);
    }
  };

  const handleSubmitAnswer = async (answer: string, timeSpent: number) => {
    if (!chunk) throw new Error('No chunk loaded');
    
    const response = await umareadApi.submitAnswer(id, chunk.chunk_number, {
      answer_text: answer,
      time_spent_seconds: timeSpent
    });
    
    // Refresh progress after answer
    loadProgress();
    
    // Don't automatically load next question - let student control it
    
    return response;
  };

  const handleProceedAfterQuestions = async () => {
    if (!chunk) return;
    
    if (chunk.has_next) {
      handleNavigate('next');
    } else {
      // Assignment complete - mark it as such
      setIsComplete(true);
      
      // Check if there's a test available
      try {
        const testStatus = await studentApi.getAssignmentTestStatus(id);
        setHasTest(testStatus.has_test);
      } catch (err) {
        console.error('Failed to check test status:', err);
      }
      
      // Update assignment status in backend (in real implementation)
      // For now, just update local state
    }
  }

  const handleRequestSimpler = async () => {
    if (!chunk) return;
    
    try {
      setLoading(true);
      // Clear any existing errors
      setError(null);
      const simplerQuestion = await umareadApi.requestSimplerQuestion(id, chunk.chunk_number);
      setQuestion(simplerQuestion);
    } catch (err: any) {
      console.error('Failed to get simpler question:', err);
      // Don't set global error - just retry the current question
      // This prevents showing the error page
      loadQuestion();
    } finally {
      setLoading(false);
    }
  };

  if (loading && !assignment) {
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
            <p className="text-gray-600 text-lg font-medium">Loading assignment...</p>
            <p className="text-gray-500 text-sm mt-2">Please wait while we prepare your reading</p>
          </div>
        </div>
    );
  }

  if (error) {
    return (
        <div className="min-h-screen bg-gray-50 p-4">
          <div className="max-w-2xl mx-auto mt-8">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-red-800 mb-2">Unable to Load Assignment</h3>
              <p className="text-red-700 mb-4">{error}</p>
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setError(null);
                    setRetryCount(0);
                    loadAssignment();
                  }}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                >
                  Try Again
                </button>
                <button
                  onClick={() => router.back()}
                  className="px-4 py-2 border border-red-300 text-red-600 rounded-md hover:bg-red-50 transition-colors"
                >
                  Go Back
                </button>
              </div>
              {retryCount > 0 && (
                <p className="text-sm text-red-600 mt-3">Retry attempt {retryCount} of 2</p>
              )}
            </div>
          </div>
        </div>
    );
  }

  if (!assignment) {
    return null;
  }

  // Show completion screen if assignment is complete
  if (isComplete) {
    return (
        <CompletionScreen
          title={assignment.title}
          author={assignment.author}
          totalChunks={assignment.total_chunks}
          difficultyLevel={progress?.difficulty_level || assignment.difficulty_level}
          assignmentId={id}
          hasTest={hasTest}
        />
    );
  }

  if (!chunk) {
    return null;
  }

  return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow-sm">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => router.back()}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ArrowLeft className="w-5 h-5 text-gray-600" />
                </button>
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">
                    {assignment.title}
                  </h1>
                  {assignment.author && (
                    <p className="text-sm text-gray-600">by {assignment.author}</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content - Full width for better reading */}
        <div className="max-w-7xl mx-auto px-6 py-6">
          {/* Progress Indicator */}
          {progress && (
            <ProgressIndicator
              currentChunk={chunk.chunk_number}
              totalChunks={chunk.total_chunks}
              completedChunks={progress.chunks_completed}
              difficultyLevel={progress.difficulty_level}
            />
          )}

          {/* Content Area - Side by side layout */}
          <div className="grid grid-cols-3 gap-8">
            {/* Left side: Reading Text (2/3 width) */}
            <div className="col-span-2">
              <ChunkReader
                chunk={chunk}
                onNavigate={null}
                onComplete={null}
                isLoading={loading}
                hideNavigation={true}
                largeText={true}
              />
            </div>
            
            {/* Right side: Questions (1/3 width) */}
            <div className="col-span-1">
              {question ? (
                <QuestionFlow
                  question={question}
                  onSubmit={handleSubmitAnswer}
                  onProceed={handleProceedAfterQuestions}
                  onLoadNextQuestion={loadQuestion}
                  onRequestSimpler={handleRequestSimpler}
                  isLoading={loading}
                />
              ) : (
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <div className="text-center py-8">
                    <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-3" />
                    <p className="text-gray-600 text-sm">Loading questions...</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
  )
}