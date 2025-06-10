'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { studentApi } from '@/lib/studentApi'
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  XMarkIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  CheckIcon
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

interface FlashCard extends VocabularyWord {
  showDefinition: boolean
}

export default function VocabularyFlashCardsPage() {
  const params = useParams()
  const router = useRouter()
  const assignmentId = params.id as string

  const [assignment, setAssignment] = useState<VocabularyAssignment | null>(null)
  const [cards, setCards] = useState<FlashCard[]>([])
  const [currentCardIndex, setCurrentCardIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [shuffled, setShuffled] = useState(false)

  useEffect(() => {
    fetchAssignment()
  }, [assignmentId])

  useEffect(() => {
    if (assignment) {
      initializeCards()
    }
  }, [assignment])


  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.key === 'ArrowLeft') {
        handlePrevious()
      } else if (event.key === 'ArrowRight') {
        handleNext()
      } else if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault()
        flipCard()
      } else if (event.key === 'Escape') {
        handleBack()
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [currentCardIndex, cards])

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

  const initializeCards = () => {
    const flashCards: FlashCard[] = assignment!.words.map(word => ({
      ...word,
      showDefinition: false
    }))
    setCards(flashCards)
  }

  const shuffleCards = () => {
    const shuffledCards = [...cards]
    for (let i = shuffledCards.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[shuffledCards[i], shuffledCards[j]] = [shuffledCards[j], shuffledCards[i]]
    }
    setCards(shuffledCards)
    setCurrentCardIndex(0)
    setShuffled(true)
  }


  const flipCard = () => {
    setCards(prev => prev.map((card, index) => 
      index === currentCardIndex 
        ? { ...card, showDefinition: !card.showDefinition }
        : card
    ))
  }


  const handleNext = () => {
    if (currentCardIndex < cards.length - 1) {
      setCurrentCardIndex(currentCardIndex + 1)
    }
  }

  const handlePrevious = () => {
    if (currentCardIndex > 0) {
      setCurrentCardIndex(currentCardIndex - 1)
    }
  }

  const handleBack = () => {
    router.push(`/student/assignment/vocabulary/${assignmentId}`)
  }

  const resetSession = () => {
    setCards(prev => prev.map(card => ({ 
      ...card,
      showDefinition: false 
    })))
    setCurrentCardIndex(0)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading flash cards...</p>
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

  const currentCard = cards[currentCardIndex]

  if (cards.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow-sm">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-4 flex items-center justify-between">
              <button
                onClick={handleBack}
                className="flex items-center text-gray-600 hover:text-gray-800 transition-colors"
              >
                <XMarkIcon className="h-5 w-5 mr-2" />
                Exit Flash Cards
              </button>
              <h1 className="text-lg font-medium text-gray-900">{assignment.title}</h1>
              <div></div>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center min-h-[calc(100vh-80px)]">
          <div className="text-center">
            <CheckIcon className="h-16 w-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No Cards Available</h2>
            <p className="text-gray-600 mb-6">
              There are no vocabulary words available for this assignment.
            </p>
            <div className="space-x-4">
              <button
                onClick={handleBack}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                Go Back
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-blue-50">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 flex items-center justify-between">
            <button
              onClick={handleBack}
              className="flex items-center text-gray-600 hover:text-gray-800 transition-colors"
            >
              <XMarkIcon className="h-5 w-5 mr-2" />
              Exit Flash Cards
            </button>
            
            <div className="text-center">
              <h1 className="text-lg font-medium text-gray-900">{assignment.title}</h1>
              <p className="text-sm text-gray-500">
                Card {currentCardIndex + 1} of {cards.length}
              </p>
            </div>
            
            <div className="text-sm text-gray-500">
              Flash Cards Study Session
            </div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-gray-50 border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-3 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={shuffleCards}
                className="flex items-center px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                <ArrowPathIcon className="h-4 w-4 mr-2" />
                Shuffle
              </button>
              
              <div className="text-sm text-gray-500">
                {cards.length} vocabulary words
              </div>
            </div>

            <button
              onClick={resetSession}
              className="text-sm text-gray-600 hover:text-gray-800"
            >
              Reset Cards
            </button>
          </div>
        </div>
      </div>

      {/* Flash Card */}
      <main className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-2xl w-full">
          <div 
            className={`relative w-full h-96 cursor-pointer transition-transform duration-200 ${
              currentCard.showDefinition ? 'scale-105' : 'scale-100'
            }`}
            onClick={flipCard}
          >
            <div className="absolute inset-0 bg-white rounded-2xl shadow-xl border-2 border-gray-200 hover:shadow-2xl transition-shadow">
              <div className="h-full flex flex-col justify-center items-center p-8">
                {!currentCard.showDefinition ? (
                  // Front of card (word)
                  <div className="text-center">
                    <h2 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
                      {currentCard.word}
                    </h2>
                    <p className="text-lg text-gray-500">
                      Click to reveal definition
                    </p>
                  </div>
                ) : (
                  // Back of card (definition)
                  <div className="text-center">
                    <h3 className="text-2xl font-semibold text-gray-800 mb-4">
                      {currentCard.word}
                    </h3>
                    <p className="text-lg text-gray-700 mb-6 leading-relaxed">
                      {currentCard.definition}
                    </p>
                    {currentCard.example_1 && (
                      <p className="text-base text-gray-600 italic">
                        "{currentCard.example_1}"
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>


      {/* Navigation */}
      <div className="bg-white border-t border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={handlePrevious}
              disabled={currentCardIndex === 0}
              className={`flex items-center px-6 py-3 rounded-lg font-medium transition-colors ${
                currentCardIndex === 0
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              Previous
            </button>

            <div className="text-center">
              <p className="text-sm text-gray-600 mb-2">
                Press Space or click card to flip
              </p>
              <div className="flex justify-center space-x-1">
                {cards.slice(0, 10).map((_, index) => (
                  <div
                    key={index}
                    className={`w-2 h-2 rounded-full ${
                      index === currentCardIndex
                        ? 'bg-primary-600'
                        : 'bg-gray-300'
                    }`}
                  />
                ))}
                {cards.length > 10 && (
                  <span className="text-xs text-gray-400 ml-2">
                    +{cards.length - 10} more
                  </span>
                )}
              </div>
            </div>

            <button
              onClick={handleNext}
              disabled={currentCardIndex === cards.length - 1}
              className={`flex items-center px-6 py-3 rounded-lg font-medium transition-colors ${
                currentCardIndex === cards.length - 1
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
    </div>
  )
}