'use client'

import { useState } from 'react'
import { umalectureApi } from '@/lib/umalectureApi'

export default function DebugLecture() {
  const [lectureId, setLectureId] = useState('')
  const [results, setResults] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const checkAssignments = async () => {
    if (!lectureId) {
      alert('Please enter a lecture ID')
      return
    }

    setLoading(true)
    try {
      const assignments = await umalectureApi.getClassroomAssignments(lectureId)
      setResults(assignments)
    } catch (err: any) {
      setResults({ error: err.response?.data || err.message })
    }
    setLoading(false)
  }

  const forceUnlink = async () => {
    if (!lectureId) {
      alert('Please enter a lecture ID')
      return
    }

    if (!confirm('Are you sure you want to unlink this lecture from ALL classrooms?')) {
      return
    }

    setLoading(true)
    try {
      const result = await umalectureApi.unlinkAllClassrooms(lectureId)
      setResults(result)
      alert('Successfully unlinked from all classrooms!')
    } catch (err: any) {
      setResults({ error: err.response?.data || err.message })
    }
    setLoading(false)
  }

  const tryDelete = async () => {
    if (!lectureId) {
      alert('Please enter a lecture ID')
      return
    }

    setLoading(true)
    try {
      const result = await umalectureApi.deleteLecture(lectureId)
      setResults({ success: true, ...result })
      alert('Successfully archived lecture!')
    } catch (err: any) {
      setResults({ 
        error: true, 
        status: err.response?.status,
        data: err.response?.data,
        message: err.message 
      })
    }
    setLoading(false)
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">UMALecture Debug Tool</h1>
      
      <div className="mb-6">
        <label className="block text-sm font-medium mb-2">Lecture ID:</label>
        <input
          type="text"
          value={lectureId}
          onChange={(e) => setLectureId(e.target.value)}
          placeholder="e.g., 6192e502-b859-48b9-bd43-5bca914b242a"
          className="w-full px-3 py-2 border border-gray-300 rounded-md"
        />
      </div>

      <div className="flex gap-4 mb-6">
        <button
          onClick={checkAssignments}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          Check Classroom Assignments
        </button>
        
        <button
          onClick={forceUnlink}
          disabled={loading}
          className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:opacity-50"
        >
          Force Unlink All Classrooms
        </button>
        
        <button
          onClick={tryDelete}
          disabled={loading}
          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
        >
          Try Delete/Archive
        </button>
      </div>

      {results && (
        <div className="bg-gray-100 p-4 rounded-md">
          <h2 className="font-semibold mb-2">Results:</h2>
          <pre className="whitespace-pre-wrap text-sm">
            {JSON.stringify(results, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}