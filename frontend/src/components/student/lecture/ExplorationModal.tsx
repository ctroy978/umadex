import { useState, useRef, useEffect } from 'react'
import { X, Loader2 } from 'lucide-react'
import { exploreUMALectureTerm } from '@/lib/umalectureApi'

interface ExplorationModalProps {
  isOpen: boolean
  onClose: () => void
  term: string
  topicId: string
  topicTitle: string
  difficultyLevel: string
  gradeLevel: string
  lectureId: string
  lectureContext: string
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

export function ExplorationModal({
  isOpen,
  onClose,
  term,
  topicId,
  topicTitle,
  difficultyLevel,
  gradeLevel,
  lectureId,
  lectureContext,
}: ExplorationModalProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Initialize with automatic explanation when modal opens
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      fetchInitialExplanation()
    }
  }, [isOpen])

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Anti-cheating: Prevent copy/paste and text selection
  useEffect(() => {
    if (!isOpen) return

    const preventCopyPaste = (e: Event) => {
      e.preventDefault()
      return false
    }

    const preventSelection = (e: Event) => {
      e.preventDefault()
      return false
    }

    const preventContextMenu = (e: Event) => {
      e.preventDefault()
      return false
    }

    // Add event listeners
    document.addEventListener('copy', preventCopyPaste)
    document.addEventListener('cut', preventCopyPaste)
    document.addEventListener('paste', preventCopyPaste)
    document.addEventListener('selectstart', preventSelection)
    document.addEventListener('contextmenu', preventContextMenu)

    // Cleanup
    return () => {
      document.removeEventListener('copy', preventCopyPaste)
      document.removeEventListener('cut', preventCopyPaste)
      document.removeEventListener('paste', preventCopyPaste)
      document.removeEventListener('selectstart', preventSelection)
      document.removeEventListener('contextmenu', preventContextMenu)
    }
  }, [isOpen])

  const fetchInitialExplanation = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await exploreUMALectureTerm({
        lecture_id: lectureId,
        topic_id: topicId,
        exploration_term: term,
        question: null,
        difficulty_level: difficultyLevel,
        grade_level: gradeLevel,
        lecture_context: lectureContext.substring(0, 500),
        conversation_history: [],
      })

      setMessages([{
        id: Date.now().toString(),
        role: 'assistant',
        content: response.response || '',
        timestamp: new Date(),
      }])
    } catch (err) {
      setError('Failed to load explanation. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }


  const handleClose = () => {
    setMessages([])
    setError(null)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div 
        className="bg-gray-900 rounded-lg w-full max-w-2xl h-[600px] flex flex-col select-none"
        onCopy={(e) => e.preventDefault()}
        onCut={(e) => e.preventDefault()}
        onPaste={(e) => e.preventDefault()}
        onContextMenu={(e) => e.preventDefault()}
        style={{
          WebkitUserSelect: 'none',
          MozUserSelect: 'none',
          msUserSelect: 'none',
          userSelect: 'none'
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div>
            <h3 className="text-lg font-medium text-white">Exploring: {term}</h3>
            <p className="text-sm text-gray-400 mt-1">{topicTitle} - {difficultyLevel}</p>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {isLoading && messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : error ? (
            <div className="text-center text-red-400 p-4">{error}</div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className="flex justify-start"
              >
                <div className="max-w-full rounded-lg p-4 bg-gray-800 text-gray-200">
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </div>
  )
}