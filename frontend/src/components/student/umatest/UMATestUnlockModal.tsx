import React, { useState } from 'react';
import { LockOpenIcon } from '@heroicons/react/24/outline';
import { umatestApi } from '@/lib/umatestApi';

interface UMATestUnlockModalProps {
  isOpen: boolean;
  testAttemptId: string;
  onUnlockSuccess: () => void;
  onCancel: () => void;
}

export default function UMATestUnlockModal({ 
  isOpen, 
  testAttemptId, 
  onUnlockSuccess, 
  onCancel 
}: UMATestUnlockModalProps) {
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
      await umatestApi.unlockTest(testAttemptId, bypassCode.trim());
      onUnlockSuccess();
    } catch (err: any) {
      console.error('Failed to unlock test:', err);
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isUnlocking) {
      handleUnlock();
    }
  };

  return (
    <div className="fixed inset-0 z-[60] overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4 text-center">
        <div className="fixed inset-0 bg-gray-900 bg-opacity-75 transition-opacity" onClick={onCancel} />
        
        <div className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md">
          <div className="bg-white px-6 py-6">
            <div className="flex items-center mb-4">
              <LockOpenIcon className="h-8 w-8 text-blue-600 mr-3" />
              <h3 className="text-lg font-semibold text-gray-900">
                Unlock Test with Bypass Code
              </h3>
            </div>
            
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-4">
                Enter the bypass code provided by your teacher to unlock the test.
              </p>
              
              <input
                type="text"
                value={bypassCode}
                onChange={(e) => setBypassCode(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter bypass code"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                autoFocus
                disabled={isUnlocking}
              />
              
              {error && (
                <p className="mt-2 text-sm text-red-600">
                  {error}
                </p>
              )}
            </div>
            
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
              <p className="text-sm text-yellow-800">
                <strong>Important:</strong> Unlocking the test will reset all your progress. 
                You will start from the beginning with no saved answers.
              </p>
            </div>
            
            <div className="flex justify-end space-x-3">
              <button
                onClick={onCancel}
                disabled={isUnlocking}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                onClick={handleUnlock}
                disabled={isUnlocking || !bypassCode.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isUnlocking ? 'Unlocking...' : 'Unlock Test'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}