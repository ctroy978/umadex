'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { studentApi } from '@/lib/studentApi'
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  SpeakerWaveIcon,
  XMarkIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline'

interface VocabularyWord {
  id: string
  word: string
  definition: string
  example_1?: string
  example_2?: string
  audio_url?: string
  phonetic_text?: string
  position: number
}

interface VocabularyAssignment {
  id: string
  title: string
  context_description: string
  grade_level: string
  subject_area: string
  classroom_name: string
  teacher_name: string
  words: VocabularyWord[]
  settings: {
    delivery_mode: string
    group_size: number
    groups_count: number
    released_groups: number[]
  }
}

export default function VocabularyPresentationPage() {
  const params = useParams()
  const router = useRouter()
  const assignmentId = params.id as string

  const [assignment, setAssignment] = useState<VocabularyAssignment | null>(null)
  const [currentWordIndex, setCurrentWordIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [audioLoading, setAudioLoading] = useState(false)
  const [audioError, setAudioError] = useState(false)
  
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    fetchAssignment()
  }, [assignmentId])

  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.key === 'ArrowLeft') {
        handlePrevious()
      } else if (event.key === 'ArrowRight') {
        handleNext()
      } else if (event.key === 'Escape') {
        handleBack()
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [currentWordIndex, assignment])

  const fetchAssignment = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await studentApi.getVocabularyAssignment(assignmentId)
      setAssignment(data)
    } catch (err: any) {
      console.error('Failed to fetch vocabulary assignment:', err)
      if (err.response?.status === 404) {
        setError('Assignment not found or you don\'t have access to it.')
      } else if (err.response?.status === 403) {
        setError('This assignment is not currently active.')
      } else {
        setError('Failed to load assignment. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleNext = () => {
    if (assignment && currentWordIndex < assignment.words.length - 1) {
      setCurrentWordIndex(currentWordIndex + 1)
      setAudioError(false)
    }
  }

  const handlePrevious = () => {
    if (currentWordIndex > 0) {
      setCurrentWordIndex(currentWordIndex - 1)
      setAudioError(false)
    }
  }

  const handleBack = () => {
    router.push(`/student/assignment/vocabulary/${assignmentId}`)
  }

  const playAudio = async () => {
    const currentWord = assignment?.words[currentWordIndex]
    if (!currentWord?.audio_url || !audioRef.current) return

    try {
      setAudioLoading(true)
      setAudioError(false)
      
      audioRef.current.src = currentWord.audio_url
      await audioRef.current.play()
    } catch (error) {
      console.error('Error playing audio:', error)
      setAudioError(true)
    } finally {
      setAudioLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading vocabulary words...</p>
        </div>
      </div>
    )
  }

  if (error || !assignment || assignment.words.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 mb-4">{error || 'No vocabulary words available'}</p>
          <button
            onClick={handleBack}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  const currentWord = assignment.words[currentWordIndex]

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 flex items-center justify-between">
            <button
              onClick={handleBack}
              className="flex items-center text-gray-600 hover:text-gray-800 transition-colors"
            >
              <XMarkIcon className="h-5 w-5 mr-2" />
              Exit Study
            </button>
            
            <div className="text-center">
              <h1 className="text-lg font-medium text-gray-900">{assignment.title}</h1>
              <p className="text-sm text-gray-500">
                Word {currentWordIndex + 1} of {assignment.words.length}
              </p>
            </div>
            
            <div className="text-sm text-gray-500">
              Use ← → arrow keys to navigate
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-gray-200 h-1">
        <div 
          className="bg-primary-600 h-1 transition-all duration-300"
          style={{ width: `${((currentWordIndex + 1) / assignment.words.length) * 100}%` }}
        />
      </div>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-4xl w-full">
          <div className="bg-white rounded-2xl shadow-xl p-8 md:p-12">
            {/* Word */}
            <div className="text-center mb-8">
              <h2 className="text-4xl md:text-6xl font-bold text-gray-900 mb-4">
                {currentWord.word}
              </h2>
              
              {/* Pronunciation */}
              <div className="flex items-center justify-center space-x-4">
                {currentWord.audio_url && (
                  <button
                    onClick={playAudio}
                    disabled={audioLoading}
                    className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      audioLoading 
                        ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                        : audioError
                          ? 'bg-red-100 text-red-600 hover:bg-red-200'
                          : 'bg-blue-100 text-blue-600 hover:bg-blue-200'
                    }`}
                  >
                    <SpeakerWaveIcon className="h-4 w-4 mr-2" />
                    {audioLoading ? 'Loading...' : audioError ? 'Audio Error' : 'Play Pronunciation'}
                  </button>
                )}
                
                {currentWord.phonetic_text && (
                  <span className="text-lg text-gray-600 font-mono">
                    /{currentWord.phonetic_text}/
                  </span>
                )}
                
                {!currentWord.audio_url && !currentWord.phonetic_text && (
                  <span className="text-sm text-gray-400">No pronunciation available</span>
                )}
              </div>
            </div>

            {/* Definition */}
            <div className="mb-8">
              <h3 className="text-xl font-semibold text-gray-800 mb-3">Definition</h3>
              <div className="bg-gray-50 rounded-lg p-6">
                <p className="text-lg text-gray-700 leading-relaxed">
                  {currentWord.definition}
                </p>
              </div>
            </div>

            {/* Examples */}
            {(currentWord.example_1 || currentWord.example_2) && (
              <div className="mb-8">
                <h3 className="text-xl font-semibold text-gray-800 mb-3">Examples</h3>
                <div className="space-y-4">
                  {currentWord.example_1 && (
                    <div className="bg-blue-50 rounded-lg p-6 border-l-4 border-blue-400">
                      <p className="text-gray-700 italic">"{currentWord.example_1}"</p>
                    </div>
                  )}
                  {currentWord.example_2 && (
                    <div className="bg-green-50 rounded-lg p-6 border-l-4 border-green-400">
                      <p className="text-gray-700 italic">"{currentWord.example_2}"</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Navigation */}
      <div className="bg-white border-t border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={handlePrevious}
              disabled={currentWordIndex === 0}
              className={`flex items-center px-6 py-3 rounded-lg font-medium transition-colors ${
                currentWordIndex === 0
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              Previous
            </button>

            <div className="text-center">
              <p className="text-sm text-gray-600">
                Word {currentWordIndex + 1} of {assignment.words.length}
              </p>
              <div className="flex mt-2 space-x-1">
                {assignment.words.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentWordIndex(index)}
                    className={`w-3 h-3 rounded-full transition-colors ${
                      index === currentWordIndex
                        ? 'bg-primary-600'
                        : index < currentWordIndex
                          ? 'bg-green-400'
                          : 'bg-gray-300'
                    }`}
                  />
                ))}
              </div>
            </div>

            <button
              onClick={handleNext}
              disabled={currentWordIndex === assignment.words.length - 1}
              className={`flex items-center px-6 py-3 rounded-lg font-medium transition-colors ${
                currentWordIndex === assignment.words.length - 1
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-primary-600 text-white hover:bg-primary-700'
              }`}
            >
              Next
              <ArrowRightIcon className="h-4 w-4 ml-2" />
            </button>
          </div>
        </div>
      </div>

      {/* Hidden audio element */}
      <audio ref={audioRef} preload="none" />
    </div>
  )
}