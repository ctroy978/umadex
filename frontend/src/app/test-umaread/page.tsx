'use client';

import { useState } from 'react';
import { umareadApi } from '@/lib/umareadApi';

export default function TestUMAReadPage() {
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const testStartAssignment = async () => {
    setLoading(true);
    setError(null);
    try {
      // Use the Alice assignment ID from the database
      const response = await umareadApi.startAssignment('f9181803-65d6-4557-b50a-7866f5321157');
      setResult(response);
    } catch (err: any) {
      setError(err.message || 'Failed to start assignment');
    } finally {
      setLoading(false);
    }
  };

  const testGetChunk = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await umareadApi.getChunk('f9181803-65d6-4557-b50a-7866f5321157', 1);
      setResult(response);
    } catch (err: any) {
      setError(err.message || 'Failed to get chunk');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">UMARead API Test</h1>
        
        <div className="space-y-4 mb-8">
          <button
            onClick={testStartAssignment}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Loading...' : 'Test Start Assignment'}
          </button>
          
          <button
            onClick={testGetChunk}
            disabled={loading}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 ml-4"
          >
            {loading ? 'Loading...' : 'Test Get Chunk'}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <p className="text-red-700">Error: {error}</p>
          </div>
        )}

        {result && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">API Response:</h2>
            <pre className="bg-gray-100 p-4 rounded-lg overflow-auto">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}