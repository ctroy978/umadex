'use client';

import { useState } from 'react';
import { X } from 'lucide-react';

interface CrunchTextModalProps {
  isOpen: boolean;
  onClose: () => void;
  simplifiedText: string;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

export default function CrunchTextModal({
  isOpen,
  onClose,
  simplifiedText,
  isLoading,
  error,
  onRetry
}: CrunchTextModalProps) {
  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Easier Reading Version
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              This is a simplified version to help with reading comprehension
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="flex items-center space-x-3">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <span className="text-gray-600">Creating easier version...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="text-center py-12">
              <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <h3 className="text-red-800 font-medium mb-2">
                  Unable to create simplified version
                </h3>
                <p className="text-red-600 text-sm mb-4">
                  {error}
                </p>
                <button
                  onClick={onRetry}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}

          {!isLoading && !error && simplifiedText && (
            <div className="prose prose-lg max-w-none">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <p className="text-blue-800 text-sm mb-0">
                  <strong>Reading Tip:</strong> This simplified version uses easier words and shorter sentences 
                  while keeping all the important information. After reading this, you can close the window 
                  and continue with the original text and questions.
                </p>
              </div>
              
              <div className="whitespace-pre-wrap leading-relaxed text-gray-900">
                {simplifiedText}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 p-6">
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-500">
              This is a reading aid. Continue with the original text for your assignment.
            </p>
            <button
              onClick={onClose}
              className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}