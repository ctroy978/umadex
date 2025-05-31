'use client';

import { CheckCircle, Circle } from 'lucide-react';

interface ProgressIndicatorProps {
  currentChunk: number;
  totalChunks: number;
  completedChunks: number[];
  difficultyLevel: number;
}

export default function ProgressIndicator({
  currentChunk,
  totalChunks,
  completedChunks,
  difficultyLevel
}: ProgressIndicatorProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
      {/* Chunk Progress */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-sm font-medium text-gray-700">
            Chunk {currentChunk} of {totalChunks}
          </h3>
          <span className="text-sm text-gray-500">
            {completedChunks.length} completed
          </span>
        </div>
        
        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(completedChunks.length / totalChunks) * 100}%` }}
          />
        </div>
      </div>

      {/* Difficulty Level (subtle display) */}
      <div className="flex items-center justify-between">
        <div className="text-xs text-gray-500">
          Reading Level
        </div>
        <div className="flex space-x-1">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className={`w-2 h-2 rounded-full transition-colors ${
                i < difficultyLevel
                  ? 'bg-blue-500'
                  : 'bg-gray-300'
              }`}
            />
          ))}
        </div>
      </div>

      {/* Mobile-friendly chunk dots */}
      {totalChunks <= 10 && (
        <div className="flex flex-wrap gap-2 mt-4 justify-center">
          {[...Array(totalChunks)].map((_, i) => {
            const chunkNum = i + 1;
            const isCompleted = completedChunks.includes(chunkNum);
            const isCurrent = chunkNum === currentChunk;
            
            return (
              <div
                key={chunkNum}
                className={`flex items-center justify-center w-8 h-8 rounded-full text-xs font-medium transition-all ${
                  isCurrent
                    ? 'bg-blue-600 text-white ring-2 ring-blue-300'
                    : isCompleted
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-100 text-gray-500'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  chunkNum
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}