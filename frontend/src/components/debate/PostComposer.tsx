'use client'

import { useState, useRef, useEffect } from 'react'
import { studentDebateApi } from '@/lib/studentDebateApi'
import { PaperAirplaneIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { RhetoricalTechnique } from '@/types/debate'

interface PostComposerProps {
  onSubmit: (content: string, selectedTechnique?: string) => Promise<void>
  disabled?: boolean
  minWords?: number
  maxWords?: number
}

export default function PostComposer({ 
  onSubmit, 
  disabled = false,
  minWords = 75,
  maxWords = 300
}: PostComposerProps) {
  const [content, setContent] = useState('')
  const [wordCount, setWordCount] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [selectedTechnique, setSelectedTechnique] = useState<string>('')
  const [techniques, setTechniques] = useState<RhetoricalTechnique[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    setWordCount(studentDebateApi.countWords(content))
  }, [content])

  useEffect(() => {
    // Load rhetorical techniques for dropdown
    loadTechniques()
  }, [])

  const loadTechniques = async () => {
    try {
      const data = await studentDebateApi.getTechniques()
      setTechniques(data.proper)
    } catch (err) {
      // Failed to load techniques
    }
  }

  const handleSubmit = async () => {
    if (wordCount < minWords || wordCount > maxWords || disabled || submitting) {
      return
    }

    try {
      setSubmitting(true)
      await onSubmit(content, selectedTechnique || undefined)
      setContent('')
      setWordCount(0)
      setSelectedTechnique('')
    } catch (err) {
      // Error handled by parent
    } finally {
      setSubmitting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const getWordCountColor = () => {
    if (wordCount < minWords) return 'text-orange-600'
    if (wordCount > maxWords) return 'text-red-600'
    return 'text-green-600'
  }

  const getWordCountMessage = () => {
    if (wordCount < minWords) {
      return `${minWords - wordCount} more words needed`
    }
    if (wordCount > maxWords) {
      return `${wordCount - maxWords} words over limit`
    }
    return 'Good to go!'
  }

  return (
    <div className="p-4">
      <div className="space-y-3">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your argument here..."
          className="w-full min-h-[120px] px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 sm:text-sm resize-none"
          disabled={disabled || submitting}
        />
        
        {/* Rhetorical Technique Dropdown */}
        <div className="flex items-center">
          <label htmlFor="technique-select" className="text-sm font-medium text-gray-700 mr-2">
            Rhetorical Technique (Optional):
          </label>
          <select
            id="technique-select"
            value={selectedTechnique}
            onChange={(e) => setSelectedTechnique(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 sm:text-sm"
            disabled={disabled || submitting}
          >
            <option value="">No specific technique selected</option>
            {techniques.map((technique) => (
              <option key={technique.name} value={technique.name}>
                {technique.displayName}
              </option>
            ))}
          </select>
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="text-sm">
              <span className={`font-medium ${getWordCountColor()}`}>
                {wordCount}/{minWords}-{maxWords} words
              </span>
              <span className="text-gray-500 ml-2">
                ({getWordCountMessage()})
              </span>
            </div>
            
            {wordCount > 0 && wordCount < minWords && (
              <div className="flex items-center text-orange-600 text-sm">
                <ExclamationCircleIcon className="h-4 w-4 mr-1" />
                Minimum {minWords} words required
              </div>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-500">
              Press Ctrl+Enter to submit
            </span>
            <button
              onClick={handleSubmit}
              disabled={
                wordCount < minWords || 
                wordCount > maxWords || 
                disabled || 
                submitting ||
                content.trim().length === 0
              }
              className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white ${
                wordCount < minWords || 
                wordCount > maxWords || 
                disabled || 
                submitting ||
                content.trim().length === 0
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500'
              }`}
            >
              {submitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Sending...
                </>
              ) : (
                <>
                  <PaperAirplaneIcon className="h-4 w-4 mr-2 -rotate-45" />
                  Submit
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}