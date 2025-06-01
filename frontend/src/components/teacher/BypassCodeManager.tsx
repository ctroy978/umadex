'use client';

import { useState, useEffect } from 'react';
import { teacherApi } from '@/lib/teacherApi';
import { EyeIcon, EyeSlashIcon, KeyIcon } from '@heroicons/react/24/outline';

interface BypassCodeManagerProps {
  // No props needed - this is teacher-specific
}

export default function BypassCodeManager({}: BypassCodeManagerProps) {
  const [hasCode, setHasCode] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [showCode, setShowCode] = useState(false);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    loadBypassCodeStatus();
  }, []);

  const loadBypassCodeStatus = async () => {
    try {
      const status = await teacherApi.getBypassCodeStatus();
      setHasCode(status.has_code);
      setLastUpdated(status.last_updated);
    } catch (error) {
      console.error('Error loading bypass code status:', error);
    }
  };

  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 4);
    setCode(value);
  };

  const handleSetCode = async () => {
    if (code.length !== 4) {
      setMessage({ type: 'error', text: 'Code must be exactly 4 digits' });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      await teacherApi.setBypassCode(code);
      setHasCode(true);
      setLastUpdated(new Date().toISOString());
      setMessage({ type: 'success', text: 'Bypass code set successfully' });
      setCode('');
      setShowCode(false);
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to set bypass code' });
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveCode = async () => {
    if (!confirm('Are you sure you want to remove the bypass code?')) {
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      await teacherApi.removeBypassCode();
      setHasCode(false);
      setLastUpdated(null);
      setMessage({ type: 'success', text: 'Bypass code removed successfully' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to remove bypass code' });
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-medium text-gray-900 flex items-center">
            <KeyIcon className="h-5 w-5 mr-2 text-gray-500" />
            Bypass Code
          </h3>
          <p className="text-sm text-gray-500 mt-1">Works across all your classrooms</p>
        </div>
      </div>

      <div className="text-sm text-gray-600 mb-4">
        <p>This code allows you to help students skip problematic AI questions in any of your classrooms.</p>
        <p className="mt-1">Students can enter <code className="bg-gray-100 px-1 py-0.5 rounded">!BYPASS-XXXX</code> as their answer.</p>
      </div>

      {hasCode ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
            <div>
              <p className="text-sm font-medium text-green-800">Code is set</p>
              {lastUpdated && (
                <p className="text-xs text-green-600 mt-1">
                  Last updated: {formatDate(lastUpdated)}
                </p>
              )}
            </div>
            <button
              onClick={handleRemoveCode}
              disabled={loading}
              className="text-sm text-red-600 hover:text-red-800 font-medium disabled:opacity-50"
            >
              Remove Code
            </button>
          </div>

          <div className="p-3 bg-amber-50 rounded-lg">
            <p className="text-sm text-amber-800">
              <strong>Security Note:</strong> Keep this code secure and change it if compromised.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <div className="relative flex-1">
              <input
                type={showCode ? 'text' : 'password'}
                value={code}
                onChange={handleCodeChange}
                placeholder="Enter 4 digits"
                maxLength={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => setShowCode(!showCode)}
                className="absolute right-2 top-2.5 text-gray-500 hover:text-gray-700"
              >
                {showCode ? (
                  <EyeSlashIcon className="h-5 w-5" />
                ) : (
                  <EyeIcon className="h-5 w-5" />
                )}
              </button>
            </div>
            <button
              onClick={handleSetCode}
              disabled={loading || code.length !== 4}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Set Code
            </button>
          </div>

          {code.length > 0 && code.length < 4 && (
            <p className="text-xs text-gray-500">
              {4 - code.length} more digit{4 - code.length !== 1 ? 's' : ''} needed
            </p>
          )}
        </div>
      )}

      {message && (
        <div
          className={`mt-4 p-3 rounded-lg text-sm ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800'
              : 'bg-red-50 text-red-800'
          }`}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}