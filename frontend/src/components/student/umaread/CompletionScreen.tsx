'use client';

import { CheckCircle, Trophy, ArrowLeft, FileCheck } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface CompletionScreenProps {
  title: string;
  author?: string;
  totalChunks: number;
  difficultyLevel: number;
  assignmentId: string;
  hasTest?: boolean;
}

export default function CompletionScreen({ 
  title, 
  author, 
  totalChunks,
  difficultyLevel,
  assignmentId,
  hasTest = false
}: CompletionScreenProps) {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
          {/* Success Icon */}
          <div className="mb-6 flex justify-center">
            <div className="relative">
              <CheckCircle className="w-24 h-24 text-green-500" />
              <Trophy className="w-12 h-12 text-yellow-500 absolute bottom-0 right-0" />
            </div>
          </div>

          {/* Completion Message */}
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Congratulations!
          </h1>
          <p className="text-xl text-gray-600 mb-6">
            You've completed the reading assignment
          </p>

          {/* Assignment Details */}
          <div className="bg-gray-50 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-1">
              {title}
            </h2>
            {author && (
              <p className="text-gray-600 mb-4">by {author}</p>
            )}
            
            <div className="grid grid-cols-2 gap-4 text-left max-w-sm mx-auto">
              <div>
                <p className="text-sm text-gray-500">Chunks Completed</p>
                <p className="text-lg font-semibold text-gray-900">{totalChunks}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Final Difficulty</p>
                <p className="text-lg font-semibold text-gray-900">Level {difficultyLevel}</p>
              </div>
            </div>
          </div>

          {/* Achievement Message */}
          <p className="text-gray-600 mb-8">
            Great job! You've successfully read and comprehended all sections of this text. 
            Your reading comprehension skills are improving!
          </p>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {hasTest && (
              <button
                onClick={() => router.push(`/student/test/${assignmentId}`)}
                className="inline-flex items-center px-6 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors"
              >
                <FileCheck className="w-5 h-5 mr-2" />
                Take Completion Test
              </button>
            )}
            <button
              onClick={() => router.push('/student/dashboard')}
              className="inline-flex items-center px-6 py-3 bg-gray-600 text-white font-medium rounded-lg hover:bg-gray-700 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 mr-2" />
              Return to Dashboard
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}