'use client'

import { useState } from 'react'
import { ReadingChunk } from '@/types/test'
import ImageModal from '../umaread/ImageModal'

interface ReadingTabsProps {
  chunks: ReadingChunk[]
}

interface ChunkImage {
  url: string
  thumbnail_url: string
  description?: string
  image_tag: string
}

export default function ReadingTabs({ chunks }: ReadingTabsProps) {
  const [activeTab, setActiveTab] = useState(0)
  const [selectedImage, setSelectedImage] = useState<ChunkImage | null>(null)

  const currentChunk = chunks[activeTab]

  // Create a map of image tags to image data for the current chunk
  const imageMap = (currentChunk.images || []).reduce((acc, img) => {
    if (img.image_tag) {
      acc[img.image_tag] = img
    }
    return acc
  }, {} as Record<string, ChunkImage>)

  // Helper function to render text with important tags highlighted
  const renderTextWithImportant = (text: string, baseKey: number) => {
    const segments: React.ReactNode[] = []
    const importantRegex = /<important>(.*?)<\/important>/g
    let lastIndex = 0
    let match
    let keyIndex = 0
    
    while ((match = importantRegex.exec(text)) !== null) {
      // Add text before the important tag
      if (match.index > lastIndex) {
        const textBefore = text.substring(lastIndex, match.index)
        if (textBefore) {
          segments.push(textBefore)
        }
      }
      
      // Add the highlighted important text
      segments.push(
        <span key={`important-${baseKey}-${keyIndex++}`} className="bg-yellow-200 font-semibold px-1">
          {match[1]}
        </span>
      )
      
      lastIndex = match.index + match[0].length
    }
    
    // Add any remaining text after the last important tag
    if (lastIndex < text.length) {
      const remainingText = text.substring(lastIndex)
      if (remainingText) {
        segments.push(remainingText)
      }
    }
    
    return segments.length > 0 ? segments : text
  }

  // Render content with embedded images
  const renderContent = () => {
    const segments: React.ReactNode[] = []
    let currentText = currentChunk.content
    let keyIndex = 0
    
    // Regex to find image tags
    const imageRegex = /<image>(.*?)<\/image>/g
    let lastIndex = 0
    let match
    
    while ((match = imageRegex.exec(currentText)) !== null) {
      // Add text before the image tag
      if (match.index > lastIndex) {
        const textBefore = currentText.substring(lastIndex, match.index)
        if (textBefore.trim()) {
          segments.push(
            <span key={`text-${keyIndex++}`}>
              {renderTextWithImportant(textBefore, keyIndex)}
            </span>
          )
        }
      }
      
      // Add the image
      const imageTag = match[1]
      const image = imageMap[imageTag]
      
      if (image) {
        segments.push(
          <button
            key={`img-${keyIndex++}`}
            onClick={() => setSelectedImage(image)}
            className="inline-block mx-2 my-2 relative group cursor-pointer overflow-hidden rounded-lg shadow-md hover:shadow-xl transition-shadow align-middle"
            style={{ maxWidth: '200px' }}
          >
            <img
              src={image.thumbnail_url || image.url}
              alt={image.description || ''}
              className="w-full h-auto object-cover"
              style={{ maxHeight: '150px' }}
            />
            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-opacity flex items-center justify-center">
              <span className="text-white opacity-0 group-hover:opacity-100 transition-opacity bg-black bg-opacity-60 px-2 py-1 rounded text-xs">
                Click to enlarge
              </span>
            </div>
          </button>
        )
      }
      
      lastIndex = match.index + match[0].length
    }
    
    // Add any remaining text after the last image
    if (lastIndex < currentText.length) {
      const remainingText = currentText.substring(lastIndex)
      if (remainingText.trim()) {
        segments.push(
          <span key={`text-${keyIndex++}`}>
            {renderTextWithImportant(remainingText, keyIndex)}
          </span>
        )
      }
    }
    
    return segments
  }

  return (
    <div className="h-full flex flex-col">
      {/* Tab Headers */}
      <div className="border-b border-gray-200">
        <div className="flex overflow-x-auto scrollbar-hide">
          {chunks.map((chunk, index) => (
            <button
              key={index}
              onClick={() => setActiveTab(index)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === index
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                  : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
              }`}
            >
              Section {index + 1}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="prose prose-gray max-w-none reading-content">
          {/* Apply user-select: none to prevent text selection */}
          <style jsx>{`
            .reading-content {
              -webkit-user-select: none;
              -moz-user-select: none;
              -ms-user-select: none;
              user-select: none;
            }
          `}</style>
          
          {/* Rendered content with embedded images */}
          <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
            {renderContent()}
          </div>
        </div>
      </div>

      {/* Image Modal */}
      {selectedImage && (
        <ImageModal
          imageUrl={selectedImage.url}
          altText={selectedImage.description || ''}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </div>
  )
}