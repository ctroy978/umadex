import React, { useState, useEffect } from 'react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface SecurityWarningModalProps {
  isOpen: boolean;
  onAcknowledge: () => void;
}

export default function SecurityWarningModal({ isOpen, onAcknowledge }: SecurityWarningModalProps) {
  const [countdown, setCountdown] = useState(10);

  useEffect(() => {
    if (isOpen && countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [isOpen, countdown]);

  useEffect(() => {
    if (isOpen) {
      setCountdown(10);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4 text-center">
        <div className="fixed inset-0 bg-gray-900 bg-opacity-75 transition-opacity" />
        
        <div className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
          <div className="bg-red-50 border-l-4 border-red-400 p-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <ExclamationTriangleIcon className="h-8 w-8 text-red-400" aria-hidden="true" />
              </div>
              <div className="ml-3 flex-1">
                <h3 className="text-lg font-medium text-red-800">
                  Test Security Warning
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>You have left the test page. This is your first and only warning.</p>
                  <p className="mt-2 font-semibold">
                    If you leave the test page again, your test will be locked and you will need your teacher to unlock it. When unlocked, you will start the test completely over.
                  </p>
                </div>
                <div className="mt-4">
                  <button
                    type="button"
                    onClick={onAcknowledge}
                    disabled={countdown > 0}
                    className={`inline-flex justify-center rounded-md px-4 py-2 text-sm font-semibold text-white shadow-sm ${
                      countdown > 0 
                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                        : 'bg-red-600 hover:bg-red-700 focus:ring-4 focus:ring-red-500 focus:ring-opacity-50'
                    }`}
                  >
                    {countdown > 0 ? `Wait ${countdown}s...` : 'I Understand - Continue Test'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}