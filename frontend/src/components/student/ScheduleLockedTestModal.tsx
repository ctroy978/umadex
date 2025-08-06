import React, { useState } from 'react';
import { LockClosedIcon } from '@heroicons/react/24/outline';

interface ScheduleLockedTestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCodeSubmit: (code: string) => void;
  testType?: string;
  nextAvailableTime?: string;
}

export default function ScheduleLockedTestModal({ 
  isOpen, 
  onClose, 
  onCodeSubmit,
  testType = 'test',
  nextAvailableTime
}: ScheduleLockedTestModalProps) {
  const [bypassCode, setBypassCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!bypassCode.trim()) {
      setError('Please enter a bypass code');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onCodeSubmit(bypassCode.trim());
    } catch (err: any) {
      setError('Invalid or expired bypass code');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isSubmitting) {
      handleSubmit();
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4 text-center">
        <div 
          className="fixed inset-0 bg-gray-900 bg-opacity-75 transition-opacity" 
          onClick={onClose}
        />
        
        <div className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md">
          <div className="bg-white px-6 py-8">
            <div className="text-center">
              <LockClosedIcon className="mx-auto h-12 w-12 text-amber-600 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Test Currently Locked
              </h3>
              <p className="text-sm text-gray-600 mb-2">
                This {testType} is only available during scheduled testing hours.
              </p>
              {nextAvailableTime && (
                <p className="text-xs text-gray-500 mb-4">
                  Next available: {nextAvailableTime}
                </p>
              )}
              <div className="bg-amber-50 border border-amber-200 rounded-md p-3 mb-4">
                <p className="text-sm text-amber-800">
                  If your teacher has provided you with a one-time bypass code, you can enter it below to access the {testType} now.
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label htmlFor="bypass-code" className="block text-sm font-medium text-gray-700 mb-2">
                  One-Time Bypass Code
                </label>
                <input
                  id="bypass-code"
                  type="text"
                  value={bypassCode}
                  onChange={(e) => {
                    setBypassCode(e.target.value);
                    setError(null);
                  }}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter code from teacher"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-center text-lg font-mono uppercase"
                  disabled={isSubmitting}
                  autoFocus
                />
                <p className="text-xs text-gray-500 mt-2">
                  Ask your teacher for the bypass code if you need to take this {testType} outside of scheduled hours.
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}
            </div>

            <div className="mt-6 flex space-x-3">
              <button
                onClick={handleSubmit}
                disabled={isSubmitting || !bypassCode.trim()}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? 'Verifying...' : 'Unlock Test'}
              </button>
              <button
                onClick={onClose}
                disabled={isSubmitting}
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