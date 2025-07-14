'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { authFetch } from '@/lib/api'

export default function UMATestDebugPage() {
  const params = useParams()
  const testId = params.testId as string
  const [debugData, setDebugData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchDebugData() {
      try {
        const response = await authFetch(`/api/v1/student/umatest/test/debug/${testId}`)
        if (!response.ok) {
          throw new Error(`Failed to fetch debug data: ${response.statusText}`)
        }
        const data = await response.json()
        setDebugData(data)
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchDebugData()
  }, [testId])

  if (loading) return <div className="p-8">Loading debug data...</div>
  if (error) return <div className="p-8 text-red-500">Error: {error}</div>
  if (!debugData) return <div className="p-8">No data found</div>

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">UMATest Debug Information</h1>
      
      <div className="bg-gray-100 p-4 rounded mb-6">
        <h2 className="text-lg font-semibold mb-2">Test Attempt Details</h2>
        <p>Test ID: {debugData.test_attempt_id}</p>
        <p>Status: {debugData.status}</p>
        <p>Score: {debugData.score ?? 'Not scored'}</p>
        <p>Submitted: {debugData.submitted_at ? new Date(debugData.submitted_at).toLocaleString() : 'Not submitted'}</p>
        <p>Evaluated: {debugData.evaluated_at ? new Date(debugData.evaluated_at).toLocaleString() : 'Not evaluated'}</p>
      </div>

      <div className="bg-blue-100 p-4 rounded mb-6">
        <h2 className="text-lg font-semibold mb-2">Answer Data</h2>
        <p>Total answers saved: {debugData.answers_count}</p>
        <p>Answer indices: {debugData.answer_indices?.join(', ') || 'None'}</p>
      </div>

      <div className="bg-green-100 p-4 rounded mb-6">
        <h2 className="text-lg font-semibold mb-2">Evaluation Data</h2>
        <p>Total evaluations: {debugData.evaluations_count}</p>
        <p>Evaluation indices: {debugData.evaluation_indices?.join(', ') || 'None'}</p>
      </div>

      <div className="bg-yellow-100 p-4 rounded">
        <h2 className="text-lg font-semibold mb-2">Evaluation Scores by Question</h2>
        {debugData.evaluation_scores && Object.keys(debugData.evaluation_scores).length > 0 ? (
          <table className="w-full">
            <thead>
              <tr>
                <th className="text-left">Question Index</th>
                <th className="text-left">Score</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(debugData.evaluation_scores).map(([index, score]) => (
                <tr key={index}>
                  <td>{index}</td>
                  <td>{score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No evaluation scores found</p>
        )}
      </div>

      <div className="mt-6 text-sm text-gray-600">
        <p>To use this debug page after submitting a test:</p>
        <p>1. Copy the test_attempt_id from the URL or console</p>
        <p>2. Navigate to: /student/umatest/debug/[test_attempt_id]</p>
      </div>
    </div>
  )
}