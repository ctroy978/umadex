import React, { useState } from 'react';
import { LockOpenIcon } from '@heroicons/react/24/outline';
import { studentApi } from '@/lib/studentApi';

interface VocabularyUnlockModalProps {
  isOpen: boolean;
  testAttemptId: string;
  onUnlockSuccess: () => void;
  onCancel: () => void;
}

export default function VocabularyUnlockModal({ 
  isOpen, 
  testAttemptId, 
  onUnlockSuccess, 
  onCancel 
}: VocabularyUnlockModalProps) {
  const [bypassCode, setBypassCode] = useState('');
  const [isUnlocking, setIsUnlocking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleUnlock = async () => {
    if (!bypassCode.trim()) {
      setError('Please enter a bypass code');
      return;
    }

    setIsUnlocking(true);
    setError(null);

    try {
      await studentApi.unlockVocabularyTestWithBypassCode(testAttemptId, bypassCode.trim());
      onUnlockSuccess();
    } catch (err: any) {
      console.error('Failed to unlock vocabulary test:', err);
      let errorMessage = 'Invalid or expired bypass code';
      
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          // Handle FastAPI validation errors
          errorMessage = err.response.data.detail.map((e: any) => e.msg).join(', ');
        }
      }
      
      setError(errorMessage);
    } finally {
      setIsUnlocking(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4 text-center">
        <div className="fixed inset-0 bg-gray-900 bg-opacity-75 transition-opacity" />
        
        <div className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md">
          <div className="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
            <div className="sm:flex sm:items-start">
              <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
                <LockOpenIcon className="h-6 w-6 text-blue-600" aria-hidden="true" />
              </div>
              <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left flex-1">
                <h3 className="text-base font-semibold leading-6 text-gray-900">
                  Unlock Vocabulary Test
                </h3>
                <div className="mt-2">
                  <p className="text-sm text-gray-500">
                    Enter the bypass code provided by your teacher to unlock this test.
                  </p>
                  <p className="mt-2 text-sm font-medium text-orange-600">
                    Note: Unlocking will restart the test from the beginning.
                  </p>
                </div>
                <div className="mt-4">
                  <input
                    type="text"
                    value={bypassCode}
                    onChange={(e) => setBypassCode(e.target.value)}
                    placeholder="Enter bypass code"
                    className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
                    autoFocus
                    maxLength={20}
                  />
                  {error && (
                    <p className="mt-2 text-sm text-red-600">{error}</p>
                  )}
                </div>
              </div>
            </div>
          </div>
          <div className="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
            <button
              type="button"
              className="inline-flex w-full justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed sm:ml-3 sm:w-auto"
              onClick={handleUnlock}
              disabled={isUnlocking || !bypassCode.trim()}
            >
              {isUnlocking ? 'Unlocking...' : 'Unlock Test'}
            </button>
            <button
              type="button"
              className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto"
              onClick={onCancel}
              disabled={isUnlocking}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}