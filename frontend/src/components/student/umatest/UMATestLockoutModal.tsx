import React, { useState } from 'react';
import { LockClosedIcon } from '@heroicons/react/24/outline';
import { useRouter } from 'next/navigation';
import UMATestUnlockModal from './UMATestUnlockModal';

interface UMATestLockoutModalProps {
  isOpen: boolean;
  testAttemptId?: string;
  onContactTeacher?: () => void;
  onUnlockSuccess?: () => void;
}

export default function UMATestLockoutModal({ isOpen, testAttemptId, onContactTeacher, onUnlockSuccess }: UMATestLockoutModalProps) {
  const router = useRouter();
  const [showUnlockModal, setShowUnlockModal] = useState(false);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4 text-center">
        <div className="fixed inset-0 bg-gray-900 bg-opacity-75 transition-opacity" />
        
        <div className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
          <div className="bg-red-50 p-8 text-center">
            <LockClosedIcon className="mx-auto h-16 w-16 text-red-400 mb-4" />
            <h2 className="text-2xl font-bold text-red-800 mb-4">
              Test Locked
            </h2>
            <div className="text-red-700 space-y-3">
              <p>Your test has been locked because you left the test page twice.</p>
              <p>You must contact your teacher to unlock the test.</p>
              <p className="font-semibold">
                When your teacher unlocks the test, you will start completely over from the beginning.
              </p>
            </div>
            <div className="mt-6 space-y-3">
              <button
                onClick={() => setShowUnlockModal(true)}
                className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
              >
                I Have a Bypass Code
              </button>
              {onContactTeacher && (
                <button
                  onClick={onContactTeacher}
                  className="w-full bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300 transition-colors"
                >
                  Contact Teacher for Help
                </button>
              )}
              <button
                onClick={() => router.push('/student/dashboard')}
                className="w-full bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 transition-colors"
              >
                Return to Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Unlock Test Modal */}
      {testAttemptId && (
        <UMATestUnlockModal
          isOpen={showUnlockModal}
          testAttemptId={testAttemptId}
          onUnlockSuccess={() => {
            setShowUnlockModal(false);
            onUnlockSuccess?.();
          }}
          onCancel={() => setShowUnlockModal(false)}
        />
      )}
    </div>
  );
}