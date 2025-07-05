import { useState, useRef, useEffect } from 'react'
import { X, Send, Lightbulb, Link, Search, BookOpen, Loader2 } from 'lucide-react'
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

const QUICK_ACTIONS = [
  { id: 'example', label: 'Give Example', icon: Lightbulb, prompt: 'Can you give me a real-world example of' },
  { id: 'connection', label: 'Show Connection', icon: Link, prompt: 'How does this relate to' },
  { id: 'simpler', label: 'Simpler', icon: Search, prompt: 'Can you explain this in simpler terms?' },
  { id: 'detail', label: 'More Detail', icon: BookOpen, prompt: 'Can you provide more detail about' },
]

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
  const [inputValue, setInputValue] = useState('')
  const [wordCount, setWordCount] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Initialize with automatic explanation when modal opens
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      fetchInitialExplanation()
    }
  }, [isOpen])

  // Update word count
  useEffect(() => {
    const words = inputValue.trim().split(/\s+/).filter(word => word.length > 0)
    setWordCount(words.length)
  }, [inputValue])

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
        content: response.response,
        timestamp: new Date(),
      }])
    } catch (err) {
      setError('Failed to load explanation. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (!inputValue.trim() || wordCount > 200 || isLoading) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)
    setError(null)

    try {
      const response = await exploreUMALectureTerm({
        lecture_id: lectureId,
        topic_id: topicId,
        exploration_term: term,
        question: userMessage.content,
        difficulty_level: difficultyLevel,
        grade_level: gradeLevel,
        lecture_context: lectureContext.substring(0, 500),
        conversation_history: messages.map(m => ({
          role: m.role,
          content: m.content,
        })),
      })

      if (response.is_on_topic) {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: response.response,
          timestamp: new Date(),
        }])
      } else {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'system',
          content: response.redirect_message || 'Please keep your questions focused on understanding the term.',
          timestamp: new Date(),
        }])
      }
    } catch (err) {
      setError('Failed to send message. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleQuickAction = (action: typeof QUICK_ACTIONS[0]) => {
    const prompt = action.id === 'simpler' || action.id === 'detail' 
      ? action.prompt 
      : `${action.prompt} ${term}?`
    setInputValue(prompt)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleClose = () => {
    setMessages([])
    setInputValue('')
    setError(null)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 rounded-lg w-full max-w-2xl h-[600px] flex flex-col">
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
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-3 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : message.role === 'system'
                      ? 'bg-yellow-600 bg-opacity-20 text-yellow-200 border border-yellow-600'
                      : 'bg-gray-800 text-gray-200'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  <p className="text-xs opacity-70 mt-1">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))
          )}
          {isLoading && messages.length > 0 && (
            <div className="flex justify-start">
              <div className="bg-gray-800 rounded-lg p-3">
                <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Actions */}
        <div className="px-4 py-2 border-t border-gray-700">
          <div className="flex gap-2 flex-wrap">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.id}
                onClick={() => handleQuickAction(action)}
                className="flex items-center gap-1 px-3 py-1 bg-gray-800 hover:bg-gray-700 
                         text-gray-300 rounded-full text-sm transition-colors"
              >
                <action.icon className="h-3 w-3" />
                {action.label}
              </button>
            ))}
          </div>
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-700">
          {error && (
            <div className="mb-2 text-sm text-red-400">{error}</div>
          )}
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={`Ask about ${term}...`}
                className="w-full px-3 py-2 bg-gray-800 text-white rounded-lg resize-none
                         placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={2}
                disabled={isLoading}
              />
              <div className={`absolute bottom-2 right-2 text-xs ${
                wordCount > 200 ? 'text-red-400' : 'text-gray-500'
              }`}>
                {wordCount}/200 words
              </div>
            </div>
            <button
              onClick={handleSubmit}
              disabled={!inputValue.trim() || wordCount > 200 || isLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 
                       disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}