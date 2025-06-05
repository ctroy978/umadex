import React, { useState } from 'react';
import { LockOpenIcon } from '@heroicons/react/24/outline';
import { testApi } from '@/lib/testApi';

interface UnlockTestModalProps {
  isOpen: boolean;
  testAttemptId: string;
  onUnlockSuccess: () => void;
  onCancel: () => void;
}

export default function UnlockTestModal({ 
  isOpen, 
  testAttemptId, 
  onUnlockSuccess, 
  onCancel 
}: UnlockTestModalProps) {
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
      await testApi.unlockWithBypassCode(testAttemptId, bypassCode.trim());
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

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4 text-center">
        <div className="fixed inset-0 bg-gray-900 bg-opacity-75 transition-opacity" />
        
        <div className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md">
          <div className="bg-white px-6 py-8">
            <div className="text-center">
              <LockOpenIcon className="mx-auto h-12 w-12 text-blue-600 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Unlock Test with Bypass Code
              </h3>
              <p className="text-sm text-gray-600 mb-6">
                Enter the bypass code provided by your teacher to unlock and restart your test.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label htmlFor="bypass-code" className="block text-sm font-medium text-gray-700 mb-2">
                  Bypass Code
                </label>
                <input
                  id="bypass-code"
                  type="text"
                  value={bypassCode}
                  onChange={(e) => setBypassCode(e.target.value)}
                  placeholder="Enter bypass code"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-center text-lg font-mono"
                  disabled={isUnlocking}
                />
                <p className="text-xs text-gray-500 mt-2">
                  Format: <span className="font-mono">!BYPASS-1234</span> or <span className="font-mono">ABC12345</span>
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
                <p className="text-sm text-amber-800">
                  <strong>Important:</strong> Unlocking the test will reset all your progress. You will start from the beginning.
                </p>
              </div>
            </div>

            <div className="mt-6 flex space-x-3">
              <button
                onClick={handleUnlock}
                disabled={isUnlocking || !bypassCode.trim()}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isUnlocking ? 'Unlocking...' : 'Unlock Test'}
              </button>
              <button
                onClick={onCancel}
                disabled={isUnlocking}
                className="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}