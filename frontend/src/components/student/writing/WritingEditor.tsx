import { useEffect, useRef } from 'react'
import { CloudArrowUpIcon } from '@heroicons/react/24/outline'

interface WritingEditorProps {
  content: string
  onChange: (content: string) => void
  onWordCountChange: (count: number) => void
  selectedTechniques: string[]
  wordCount: number
  minWords: number
  maxWords: number
  saving: boolean
}

export default function WritingEditor({
  content,
  onChange,
  onWordCountChange,
  selectedTechniques,
  wordCount,
  minWords,
  maxWords,
  saving
}: WritingEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    // Count words whenever content changes
    const words = content.trim().split(/\s+/).filter(word => word.length > 0)
    onWordCountChange(words.length)
  }, [content, onWordCountChange])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [content])

  // Prevent copy and paste
  useEffect(() => {
    const handlePaste = (e: Event) => {
      e.preventDefault()
      return false
    }

    const handleCopy = (e: Event) => {
      e.preventDefault()
      return false
    }

    const handleCut = (e: Event) => {
      e.preventDefault()
      return false
    }

    const handleContextMenu = (e: Event) => {
      e.preventDefault()
      return false
    }

    const textarea = textareaRef.current
    if (textarea) {
      textarea.addEventListener('paste', handlePaste)
      textarea.addEventListener('copy', handleCopy)
      textarea.addEventListener('cut', handleCut)
      textarea.addEventListener('contextmenu', handleContextMenu)

      return () => {
        textarea.removeEventListener('paste', handlePaste)
        textarea.removeEventListener('copy', handleCopy)
        textarea.removeEventListener('cut', handleCut)
        textarea.removeEventListener('contextmenu', handleContextMenu)
      }
    }
  }, [])

  const getWordCountColor = () => {
    if (wordCount < minWords) return 'text-red-600'
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
    return 'Word count OK'
  }

  return (
    <div className="bg-white rounded-lg shadow-md">
      <div className="border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Your Response</h3>
        <div className="flex items-center gap-4">
          {saving && (
            <div className="flex items-center text-sm text-gray-500">
              <CloudArrowUpIcon className="h-4 w-4 mr-1 animate-pulse" />
              Saving...
            </div>
          )}
          <div className={`text-sm font-medium ${getWordCountColor()}`}>
            {wordCount} / {minWords}-{maxWords} words
          </div>
        </div>
      </div>
      
      <div className="p-6">
        {/* Anti-cheat notice */}
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">
            <strong>Note:</strong> Copy and paste functions are disabled for this assignment. Please type your response directly.
          </p>
        </div>

        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            // Prevent Ctrl+C, Ctrl+V, Ctrl+X, Cmd+C, Cmd+V, Cmd+X
            if ((e.ctrlKey || e.metaKey) && ['c', 'v', 'x', 'a'].includes(e.key.toLowerCase())) {
              e.preventDefault()
              return false
            }
          }}
          placeholder="Start writing your response here..."
          className="w-full min-h-[400px] p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          style={{ 
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
            userSelect: 'none',
            WebkitUserSelect: 'none',
            MozUserSelect: 'none',
            msUserSelect: 'none'
          }}
        />
        
        {/* Word count status */}
        <div className={`mt-2 text-sm ${getWordCountColor()}`}>
          {getWordCountMessage()}
        </div>

        {/* Selected techniques reminder */}
        {selectedTechniques.length > 0 && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-900 font-medium mb-1">
              Remember to use these techniques:
            </p>
            <p className="text-sm text-blue-700">
              {selectedTechniques.join(', ')}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}