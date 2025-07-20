'use client';

import { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import type { Question, SubmitAnswerResponse } from '@/types/umaread';

interface QuestionFlowProps {
  question: Question;
  onSubmit: (answer: string, timeSpent: number) => Promise<SubmitAnswerResponse>;
  onProceed: () => void;
  onLoadNextQuestion?: () => void;
  onRequestSimpler?: () => void;
  isLoading?: boolean;
}

export default function QuestionFlow({ 
  question, 
  onSubmit, 
  onProceed,
  onLoadNextQuestion,
  onRequestSimpler,
  isLoading = false 
}: QuestionFlowProps) {
  const [answer, setAnswer] = useState('');
  const [startTime, setStartTime] = useState<number>(Date.now());
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SubmitAnswerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSubmitTime, setLastSubmitTime] = useState<number>(0);
  
  const MAX_CHARS = 500;
  const MIN_SUBMIT_INTERVAL = 3000; // 3 seconds between submissions

  // Reset state when question changes
  useEffect(() => {
    setAnswer('');
    setStartTime(Date.now());
    setResult(null);
    setError(null);
    setLastSubmitTime(0); // Reset spam prevention timer
  }, [question.question_text]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Check for spam prevention
    const now = Date.now();
    if (now - lastSubmitTime < MIN_SUBMIT_INTERVAL) {
      setError('Please wait a few seconds before submitting again.');
      return;
    }
    
    if (answer.trim().length < 10) {
      setError('Please provide a more detailed answer (at least 10 characters).');
      return;
    }
    
    if (answer.length > MAX_CHARS) {
      setError(`Answer must be ${MAX_CHARS} characters or less.`);
      return;
    }

    setSubmitting(true);
    setError(null);
    setLastSubmitTime(now);

    try {
      const timeSpent = Math.floor((Date.now() - startTime) / 1000);
      const response = await onSubmit(answer, timeSpent);
      setResult(response);

      // Don't auto-proceed - let student read feedback and decide when to continue
    } catch (err) {
      setError('Failed to submit answer. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const getQuestionTypeLabel = () => {
    return question.question_type === 'summary' 
      ? 'Summary Question' 
      : 'Comprehension Question';
  };

  const getDifficultyInfo = () => {
    if (!question.difficulty_level || question.question_type === 'summary') return null;
    
    const descriptions = {
      1: 'Basic Facts',
      2: 'Details & Specifics',
      3: 'Stated Relationships',
      4: 'Main Ideas',
      5: 'Simple Inference',
      6: 'Implied Meaning',
      7: 'Purpose & Significance',
      8: 'Complex Analysis'
    };
    
    return {
      level: question.difficulty_level,
      description: descriptions[question.difficulty_level] || `Level ${question.difficulty_level}`
    };
  };

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      {/* Question Header */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-600">
              {getQuestionTypeLabel()}
            </span>
            {getDifficultyInfo() && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Level {getDifficultyInfo().level}: {getDifficultyInfo().description}
              </span>
            )}
          </div>
          {question.attempt_number > 1 && (
            <span className="text-sm text-gray-500">
              Attempt {question.attempt_number}
            </span>
          )}
        </div>
        
        <h3 className="text-lg font-semibold text-gray-900">
          {question.question_text}
        </h3>
      </div>

      {/* Previous Feedback */}
      {question.previous_feedback && !result && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-start">
            <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5 mr-2 flex-shrink-0" />
            <div className="text-sm text-amber-800">
              <p className="font-medium mb-1">Previous Feedback:</p>
              <p>{question.previous_feedback}</p>
            </div>
          </div>
        </div>
      )}

      {/* Answer Form */}
      {!result?.is_correct && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="answer" className="sr-only">
              Your answer
            </label>
            <textarea
              id="answer"
              value={answer}
              onChange={(e) => {
                const value = e.target.value;
                if (value.length <= MAX_CHARS) {
                  setAnswer(value);
                }
              }}
              placeholder={
                question.question_type === 'summary'
                  ? "Write your summary here (2-3 sentences)..."
                  : "Write your answer here..."
              }
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-base"
              rows={8}
              disabled={submitting || isLoading}
              required
              maxLength={MAX_CHARS}
            />
            <div className="mt-1 flex justify-between text-xs">
              <span className="text-gray-500">
                {answer.length < 10 && answer.length > 0 && (
                  <span className="text-red-600">Minimum 10 characters required</span>
                )}
              </span>
              <span className={`${answer.length > MAX_CHARS * 0.9 ? 'text-amber-600' : 'text-gray-500'}`}>
                {answer.length} / {MAX_CHARS} characters
              </span>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || isLoading || answer.trim().length < 10 || answer.length > MAX_CHARS}
            className="w-full sm:w-auto px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Evaluating...
              </>
            ) : (
              'Submit Answer'
            )}
          </button>
        </form>
      )}

      {/* Result Feedback */}
      {result && (
        <div className={`mt-4 p-4 rounded-lg ${
          result.is_correct 
            ? 'bg-green-50 border border-green-200' 
            : 'bg-red-50 border border-red-200'
        }`}>
          <div className="flex items-start">
            {result.is_correct ? (
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 mr-2 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 mr-2 flex-shrink-0" />
            )}
            <div className="flex-1">
              <p className={`text-sm ${
                result.is_correct ? 'text-green-700' : 'text-red-700'
              }`}>
                {result.feedback}
              </p>
              
              {/* Difficulty change notification */}
              {result.difficulty_changed && result.new_difficulty_level && (
                <p className="text-sm text-gray-600 mt-2">
                  Reading level adjusted to {result.new_difficulty_level}
                </p>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="mt-4 flex gap-2">
            {/* Check if this is a bypass response */}
            {result.is_correct && result.feedback?.includes('Instructor override accepted') && (
              <>
                {result.next_question_type ? (
                  <button
                    onClick={() => {
                      // Clear the result and load next question
                      setResult(null);
                      setAnswer('');
                      setStartTime(Date.now());
                      setLastSubmitTime(0); // Reset spam prevention
                      if (onLoadNextQuestion) {
                        onLoadNextQuestion();
                      }
                    }}
                    className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Continue to {result.next_question_type === 'comprehension' ? 'Comprehension' : 'Summary'} Question
                  </button>
                ) : (
                  <button
                    onClick={onProceed}
                    className="px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors"
                  >
                    Continue to Next Section
                  </button>
                )}
              </>
            )}
            
            {/* Normal correct answer handling (non-bypass) */}
            {result.is_correct && !result.feedback?.includes('Instructor override accepted') && (
              <>
                {result.next_question_type && (
                  <button
                    onClick={() => {
                      // Clear the result and load next question
                      setResult(null);
                      setAnswer('');
                      setStartTime(Date.now());
                      setLastSubmitTime(0); // Reset spam prevention
                      if (onLoadNextQuestion) {
                        onLoadNextQuestion();
                      }
                    }}
                    className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Continue to {result.next_question_type === 'comprehension' ? 'Comprehension' : 'Summary'} Question
                  </button>
                )}
                
                {result.can_proceed && !result.next_question_type && (
                  <button
                    onClick={onProceed}
                    className="px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors"
                  >
                    Continue to Next Chunk
                  </button>
                )}
              </>
            )}
            
            {!result.is_correct && (
              <>
                {onRequestSimpler && question.question_type === 'comprehension' && question.difficulty_level && question.difficulty_level > 1 && (
                  <button
                    onClick={() => {
                      setResult(null);
                      setAnswer('');
                      setStartTime(Date.now());
                      onRequestSimpler();
                    }}
                    disabled={isLoading}
                    className="px-4 py-2 bg-amber-600 text-white font-medium rounded-lg hover:bg-amber-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Loading Simpler Question...
                      </>
                    ) : (
                      'Try a Simpler Question'
                    )}
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}