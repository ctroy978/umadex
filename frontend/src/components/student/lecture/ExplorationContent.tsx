import { useState } from 'react'
import { Search } from 'lucide-react'
import { ExplorationModal } from './ExplorationModal'

interface ExplorationContentProps {
  content: string
  topicId: string
  topicTitle: string
  difficultyLevel: string
  gradeLevel: string
  lectureId: string
}

export function ExplorationContent({
  content,
  topicId,
  topicTitle,
  difficultyLevel,
  gradeLevel,
  lectureId,
}: ExplorationContentProps) {
  const [selectedTerm, setSelectedTerm] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const processContent = (text: string) => {
    // Split content while preserving explore tags
    const parts = text.split(/(<explore>.*?<\/explore>)/g)
    
    return parts.map((part, index) => {
      // Check if this part is an explore tag
      const exploreMatch = part.match(/<explore>(.*?)<\/explore>/)
      
      if (exploreMatch) {
        const term = exploreMatch[1]
        return (
          <span
            key={index}
            className="exploration-point"
            onClick={() => {
              setSelectedTerm(term)
              setModalOpen(true)
            }}
          >
            {term}
            <Search className="inline-block ml-1 h-3 w-3" />
          </span>
        )
      }
      
      
      // Regular text - split by newlines to handle paragraphs
      const lines = part.split('\n')
      return lines.map((line, lineIndex) => {
        if (line.trim() === '') {
          return lineIndex < lines.length - 1 ? <br key={`${index}-${lineIndex}`} /> : null
        }
        return (
          <span key={`${index}-${lineIndex}`}>
            {line}
            {lineIndex < lines.length - 1 && <br />}
          </span>
        )
      })
    })
  }

  return (
    <>
      <div className="exploration-content">
        {processContent(content)}
      </div>

      {selectedTerm && (
        <ExplorationModal
          isOpen={modalOpen}
          onClose={() => {
            setModalOpen(false)
            setSelectedTerm(null)
          }}
          term={selectedTerm}
          topicId={topicId}
          topicTitle={topicTitle}
          difficultyLevel={difficultyLevel}
          gradeLevel={gradeLevel}
          lectureId={lectureId}
          lectureContext={content}
        />
      )}

      <style jsx>{`
        .exploration-content {
          color: rgb(209 213 219);
          line-height: 1.75;
        }

        :global(.exploration-point) {
          color: rgb(59 130 246);
          text-decoration: underline;
          text-decoration-style: dotted;
          text-underline-offset: 2px;
          cursor: pointer;
          transition: all 0.2s;
          padding: 0 2px;
          border-radius: 0.25rem;
        }

        :global(.exploration-point:hover) {
          background-color: rgba(59, 130, 246, 0.1);
          text-decoration-style: solid;
        }
      `}</style>
    </>
  )
}