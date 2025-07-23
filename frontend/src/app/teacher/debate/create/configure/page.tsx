'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
  ArrowLeftIcon, 
  ArrowPathIcon,
  CheckIcon,
  InformationCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import { debateApi } from '@/lib/debateApi'
import DebatePreview from '@/components/debate/DebatePreview'
import type { 
  DebateAssignmentMetadata, 
  DebateConfiguration,
  DebateAssignmentCreate,
  DifficultyLevel,
  FallacyFrequency
} from '@/types/debate'
import AntiCheatWrapper from '@/components/debate/AntiCheatWrapper'

export default function DebateConfigurePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [metadata, setMetadata] = useState<DebateAssignmentMetadata | null>(null)
  
  const [config, setConfig] = useState<DebateConfiguration>({
    roundsPerDebate: 3,
    debateCount: 3,
    timeLimitHours: 8,
    difficultyLevel: 'intermediate',
    fallacyFrequency: 'every_2_3',
    aiPersonalitiesEnabled: true,
    contentModerationEnabled: true,
    autoFlagOffTopic: true
  })

  useEffect(() => {
    // Load metadata from session storage
    const savedMetadata = sessionStorage.getItem('debate_metadata')
    if (!savedMetadata) {
      // If no metadata, redirect back to step 1
      router.push('/teacher/debate/create')
      return
    }
    setMetadata(JSON.parse(savedMetadata))
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!metadata) return
    
    setLoading(true)
    try {
      const assignmentData: DebateAssignmentCreate = {
        ...metadata,
        ...config
      }
      
      const assignment = await debateApi.createAssignment(assignmentData)
      
      // Clear session storage
      sessionStorage.removeItem('debate_metadata')
      
      // Redirect to assignment detail or list page
      router.push('/teacher/debate')
    } catch (error) {
      alert('Failed to create assignment. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleBack = () => {
    // Save current config to session storage before going back
    sessionStorage.setItem('debate_config', JSON.stringify(config))
    router.push('/teacher/debate/create')
  }

  if (!metadata) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <AntiCheatWrapper>
      <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <button
          onClick={handleBack}
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to Basic Information
        </button>
        
        <h1 className="text-3xl font-bold text-gray-900">Create Debate Assignment</h1>
        <p className="mt-2 text-gray-600">Step 2 of 2: Configure Debate Settings</p>
      </div>

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center">
          <div className="flex-1">
            <div className="h-2 bg-gray-200 rounded-full">
              <div className="h-2 bg-blue-600 rounded-full" style={{ width: '100%' }} />
            </div>
          </div>
          <div className="ml-4 text-sm text-gray-600">100% Complete</div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Debate Structure */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Debate Structure</h2>
          
          {/* Number of Debates */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Debates per Student
            </label>
            <div className="flex items-center space-x-4">
              {[1, 2, 3, 4, 5].map(num => (
                <label key={num} className="flex items-center">
                  <input
                    type="radio"
                    value={num}
                    checked={config.debateCount === num}
                    onChange={(e) => setConfig(prev => ({ ...prev, debateCount: Number(e.target.value) }))}
                    className="mr-2"
                  />
                  <span>{num}</span>
                </label>
              ))}
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Students will debate this topic multiple times with different AI opponents
            </p>
          </div>

          {/* Rounds per Debate */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Rounds per Debate
            </label>
            <div className="flex items-center space-x-4">
              {[2, 3, 4].map(num => (
                <label key={num} className="flex items-center">
                  <input
                    type="radio"
                    value={num}
                    checked={config.roundsPerDebate === num}
                    onChange={(e) => setConfig(prev => ({ ...prev, roundsPerDebate: Number(e.target.value) }))}
                    className="mr-2"
                  />
                  <span>{num} rounds</span>
                </label>
              ))}
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Each round consists of one argument from the student and one from the AI
            </p>
          </div>

          {/* Time Limit */}
          <div>
            <label htmlFor="timeLimit" className="block text-sm font-medium text-gray-700 mb-2">
              Time Limit per Debate
            </label>
            <select
              id="timeLimit"
              value={config.timeLimitHours}
              onChange={(e) => setConfig(prev => ({ ...prev, timeLimitHours: Number(e.target.value) }))}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value={4}>4 hours</option>
              <option value={6}>6 hours</option>
              <option value={8}>8 hours</option>
              <option value={12}>12 hours</option>
              <option value={24}>24 hours</option>
            </select>
            <p className="mt-1 text-sm text-gray-500">
              Students must complete each debate within this time limit
            </p>
          </div>
        </div>

        {/* Difficulty Settings */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Difficulty Settings</h2>
          
          {/* Difficulty Level */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Difficulty Level
            </label>
            <div className="space-y-2">
              {(['beginner', 'intermediate', 'advanced'] as DifficultyLevel[]).map(level => (
                <label key={level} className="flex items-start">
                  <input
                    type="radio"
                    value={level}
                    checked={config.difficultyLevel === level}
                    onChange={(e) => setConfig(prev => ({ ...prev, difficultyLevel: e.target.value as DifficultyLevel }))}
                    className="mt-1 mr-3"
                  />
                  <div>
                    <span className="font-medium capitalize">{level}</span>
                    <p className="text-sm text-gray-500">
                      {level === 'beginner' && 'AI provides simple arguments and helpful hints'}
                      {level === 'intermediate' && 'AI provides balanced arguments with moderate challenge'}
                      {level === 'advanced' && 'AI provides sophisticated arguments and counterpoints'}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Fallacy Frequency */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Logical Fallacy Frequency
              <span className="ml-2 text-gray-500 font-normal">
                (teaches students to identify flawed arguments)
              </span>
            </label>
            <select
              value={config.fallacyFrequency}
              onChange={(e) => setConfig(prev => ({ ...prev, fallacyFrequency: e.target.value as FallacyFrequency }))}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="every_1_2">Every 1-2 rounds (Frequent)</option>
              <option value="every_2_3">Every 2-3 rounds (Moderate)</option>
              <option value="every_3_4">Every 3-4 rounds (Occasional)</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>
        </div>

        {/* AI & Moderation Settings */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">AI & Moderation Settings</h2>
          
          {/* AI Personalities */}
          <div className="mb-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={config.aiPersonalitiesEnabled}
                onChange={(e) => setConfig(prev => ({ ...prev, aiPersonalitiesEnabled: e.target.checked }))}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mr-3"
              />
              <div>
                <span className="text-sm font-medium text-gray-700">Enable AI Personalities</span>
                <p className="text-sm text-gray-500">
                  Each AI opponent will have a unique debating style and personality
                </p>
              </div>
            </label>
          </div>

          {/* Content Moderation */}
          <div className="mb-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={config.contentModerationEnabled}
                onChange={(e) => setConfig(prev => ({ ...prev, contentModerationEnabled: e.target.checked }))}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mr-3"
              />
              <div>
                <span className="text-sm font-medium text-gray-700">Enable Content Moderation</span>
                <p className="text-sm text-gray-500">
                  Automatically flag inappropriate content for teacher review
                </p>
              </div>
            </label>
          </div>

          {/* Auto-flag Off-topic */}
          {config.contentModerationEnabled && (
            <div className="ml-7">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={config.autoFlagOffTopic}
                  onChange={(e) => setConfig(prev => ({ ...prev, autoFlagOffTopic: e.target.checked }))}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mr-3"
                />
                <div>
                  <span className="text-sm font-medium text-gray-700">Auto-flag Off-topic Posts</span>
                  <p className="text-sm text-gray-500">
                    Flag posts that appear unrelated to the debate topic
                  </p>
                </div>
              </label>
            </div>
          )}
        </div>

        {/* Important Notice */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">Important</h3>
              <p className="mt-1 text-sm text-yellow-700">
                Content moderation helps maintain a safe learning environment but is not 100% accurate. 
                Please review flagged content regularly and adjust settings as needed for your classroom.
              </p>
            </div>
          </div>
        </div>

        {/* Form Actions */}
        <div className="flex justify-between pt-6">
          <button
            type="button"
            onClick={() => setShowPreview(true)}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Preview Assignment
          </button>
          <div className="space-x-3">
            <button
              type="button"
              onClick={handleBack}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <ArrowPathIcon className="animate-spin -ml-1 mr-2 h-4 w-4" />
                  Creating...
                </>
              ) : (
                <>
                  <CheckIcon className="-ml-1 mr-2 h-4 w-4" />
                  Create Assignment
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Preview Modal */}
      {showPreview && metadata && (
        <DebatePreview
          metadata={metadata}
          config={config}
          onClose={() => setShowPreview(false)}
        />
      )}
      </div>
    </AntiCheatWrapper>
  )
}