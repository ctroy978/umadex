'use client'

import { useState } from 'react'
import { ReadingChunk } from '@/types/test'
import ImageModal from '../umaread/ImageModal'

interface ReadingTabsProps {
  chunks: ReadingChunk[]
}

export default function ReadingTabs({ chunks }: ReadingTabsProps) {
  const [activeTab, setActiveTab] = useState(0)
  const [selectedImage, setSelectedImage] = useState<{ url: string; alt: string } | null>(null)

  const currentChunk = chunks[activeTab]

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
          
          {/* Chunk Text */}
          <div 
            className="whitespace-pre-wrap text-gray-800 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: currentChunk.content }}
          />
          
          {/* Chunk Image */}
          {currentChunk.has_image && currentChunk.image && (
            <div className="mt-6">
              <img
                src={currentChunk.image.thumbnail_url || currentChunk.image.url}
                alt={currentChunk.image.alt_text}
                className="w-full max-w-md mx-auto rounded-lg shadow-sm cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => setSelectedImage({
                  url: currentChunk.image!.url,
                  alt: currentChunk.image!.alt_text
                })}
              />
              <p className="text-sm text-gray-600 text-center mt-2">
                Click image to enlarge
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Image Modal */}
      {selectedImage && (
        <ImageModal
          imageUrl={selectedImage.url}
          altText={selectedImage.alt}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </div>
  )
}