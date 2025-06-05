'use client';

import { useState, useEffect } from 'react';
import { teacherApi } from '@/lib/teacherApi';
import { EyeIcon, EyeSlashIcon, KeyIcon, ClockIcon, DocumentDuplicateIcon, TrashIcon } from '@heroicons/react/24/outline';

interface BypassCodeManagerProps {
  // No props needed - this is teacher-specific
}

interface OneTimeCode {
  id: string;
  bypass_code: string;
  context_type: string;
  student_email?: string;
  created_at: string;
  expires_at: string;
  used: boolean;
}

export default function BypassCodeManager({}: BypassCodeManagerProps) {
  const [hasCode, setHasCode] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [showCode, setShowCode] = useState(false);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [oneTimeCodes, setOneTimeCodes] = useState<OneTimeCode[]>([]);
  const [studentEmail, setStudentEmail] = useState('');
  const [showOneTimeSection, setShowOneTimeSection] = useState(false);

  useEffect(() => {
    loadBypassCodeStatus();
    loadOneTimeCodes();
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

  const loadOneTimeCodes = async () => {
    try {
      const codes = await teacherApi.getActiveOneTimeCodes();
      setOneTimeCodes(codes);
    } catch (error) {
      console.error('Error loading one-time codes:', error);
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

  const generateOneTimeCode = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const newCode = await teacherApi.generateOneTimeBypassCode(
        'general',
        studentEmail || undefined
      );
      await loadOneTimeCodes();
      setMessage({ type: 'success', text: 'One-time code generated successfully' });
      setStudentEmail('');
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to generate one-time code' });
    } finally {
      setLoading(false);
    }
  };

  const revokeOneTimeCode = async (codeId: string) => {
    if (!confirm('Are you sure you want to revoke this code?')) {
      return;
    }

    try {
      await teacherApi.revokeOneTimeCode(codeId);
      await loadOneTimeCodes();
      setMessage({ type: 'success', text: 'Code revoked successfully' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to revoke code' });
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setMessage({ type: 'success', text: 'Code copied to clipboard' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to copy code' });
    }
  };

  const getTimeRemaining = (expiresAt: string) => {
    const now = new Date();
    const expiry = new Date(expiresAt);
    const diff = expiry.getTime() - now.getTime();
    
    if (diff <= 0) return 'Expired';
    
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes}m remaining`;
    
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m remaining`;
  };

  return (
    <div className="space-y-6">
      {/* Permanent Bypass Code Section */}
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 flex items-center">
              <KeyIcon className="h-5 w-5 mr-2 text-gray-500" />
              Classroom Bypass Code
            </h3>
            <p className="text-sm text-gray-500 mt-1">For in-person classroom use</p>
          </div>
        </div>

        <div className="text-sm text-gray-600 mb-4">
          <p>This permanent code allows you to help students in your classroom.</p>
          <p className="mt-1">Students enter <code className="bg-gray-100 px-1 py-0.5 rounded">!BYPASS-XXXX</code> to skip problematic questions.</p>
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

      {/* One-Time Bypass Codes Section */}
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 flex items-center">
              <ClockIcon className="h-5 w-5 mr-2 text-gray-500" />
              One-Time Bypass Codes
            </h3>
            <p className="text-sm text-gray-500 mt-1">For remote students</p>
          </div>
          <button
            onClick={() => setShowOneTimeSection(!showOneTimeSection)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {showOneTimeSection ? 'Hide' : 'Show'}
          </button>
        </div>

        {showOneTimeSection && (
          <>
            <div className="text-sm text-gray-600 mb-4">
              <p>Generate temporary codes for remote students. Each code expires after 1 hour or single use.</p>
              <p className="mt-1">Students enter the 8-character code directly (e.g., <code className="bg-gray-100 px-1 py-0.5 rounded">ABC12345</code>).</p>
            </div>

            <div className="space-y-4">
              <div className="flex items-end space-x-2">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Student Email (optional)
                  </label>
                  <input
                    type="email"
                    value={studentEmail}
                    onChange={(e) => setStudentEmail(e.target.value)}
                    placeholder="student@example.com"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <button
                  onClick={generateOneTimeCode}
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  Generate Code
                </button>
              </div>

              {oneTimeCodes.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Active Codes</h4>
                  <div className="space-y-2">
                    {oneTimeCodes.map((code) => (
                      <div
                        key={code.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                      >
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <code className="text-sm font-mono bg-white px-2 py-1 rounded border">
                              {code.bypass_code}
                            </code>
                            <button
                              onClick={() => copyToClipboard(code.bypass_code)}
                              className="text-gray-500 hover:text-gray-700"
                              title="Copy to clipboard"
                            >
                              <DocumentDuplicateIcon className="h-4 w-4" />
                            </button>
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {code.student_email && `For: ${code.student_email} • `}
                            {getTimeRemaining(code.expires_at)}
                          </div>
                        </div>
                        <button
                          onClick={() => revokeOneTimeCode(code.id)}
                          className="text-red-600 hover:text-red-800 ml-2"
                          title="Revoke code"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}