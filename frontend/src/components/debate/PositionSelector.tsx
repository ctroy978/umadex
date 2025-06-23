'use client'

import { useState } from 'react'
import { HandThumbUpIcon, HandThumbDownIcon } from '@heroicons/react/24/outline'

interface PositionSelectorProps {
  onSelect: (position: 'pro' | 'con', reason?: string) => Promise<void>
  topic: string
}

export default function PositionSelector({ onSelect, topic }: PositionSelectorProps) {
  const [position, setPosition] = useState<'pro' | 'con' | ''>('')
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!position) return

    try {
      setSubmitting(true)
      await onSelect(position as 'pro' | 'con', reason.trim() || undefined)
    } catch (err) {
      // Error handled by parent
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full shadow-xl">
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Choose Your Final Position</h2>
          <p className="text-sm text-gray-600">
            You've argued both sides. Now choose the position you believe in most strongly for the final debate.
          </p>
        </div>

        <div className="space-y-4 mb-6">
          <div 
            className={`flex items-start space-x-3 p-4 rounded-lg border-2 hover:bg-gray-50 cursor-pointer ${
              position === 'pro' ? 'border-green-500 bg-green-50' : 'border-gray-200'
            }`}
            onClick={() => setPosition('pro')}
          >
            <input
              type="radio"
              id="pro"
              name="position"
              value="pro"
              checked={position === 'pro'}
              onChange={() => setPosition('pro')}
              className="mt-1 h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300"
            />
            <label htmlFor="pro" className="flex-1 cursor-pointer">
              <div className="flex items-center mb-2">
                <HandThumbUpIcon className="h-5 w-5 text-green-600 mr-2" />
                <span className="font-semibold text-green-600">PRO - I Support This</span>
              </div>
              <p className="text-sm text-gray-600">
                I believe the arguments in favor are stronger and more convincing.
              </p>
            </label>
          </div>

          <div 
            className={`flex items-start space-x-3 p-4 rounded-lg border-2 hover:bg-gray-50 cursor-pointer ${
              position === 'con' ? 'border-red-500 bg-red-50' : 'border-gray-200'
            }`}
            onClick={() => setPosition('con')}
          >
            <input
              type="radio"
              id="con"
              name="position"
              value="con"
              checked={position === 'con'}
              onChange={() => setPosition('con')}
              className="mt-1 h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300"
            />
            <label htmlFor="con" className="flex-1 cursor-pointer">
              <div className="flex items-center mb-2">
                <HandThumbDownIcon className="h-5 w-5 text-red-600 mr-2" />
                <span className="font-semibold text-red-600">CON - I Oppose This</span>
              </div>
              <p className="text-sm text-gray-600">
                I believe the arguments against are stronger and more convincing.
              </p>
            </label>
          </div>
        </div>

        {position && (
          <div className="mb-6">
            <label htmlFor="reason" className="block text-sm font-medium text-gray-700 mb-2">
              Why did you choose this position? (Optional)
            </label>
            <textarea
              id="reason"
              placeholder="Briefly explain your choice..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              maxLength={200}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 sm:text-sm"
            />
            <p className="text-xs text-gray-500 text-right mt-1">
              {reason.length}/200 characters
            </p>
          </div>
        )}

        <div className="flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={!position || submitting}
            className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white ${
              !position || submitting
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500'
            }`}
          >
            {submitting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Confirming...
              </>
            ) : (
              'Confirm Choice'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}