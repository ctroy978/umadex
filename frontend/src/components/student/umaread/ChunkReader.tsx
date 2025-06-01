'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, BookOpen, Loader2 } from 'lucide-react';
import ImageModal from './ImageModal';
import type { ChunkContent, ChunkImage } from '@/types/umaread';

interface ChunkReaderProps {
  chunk: ChunkContent;
  onNavigate: ((direction: 'prev' | 'next') => void) | null;
  onComplete: (() => void) | null;
  isLoading?: boolean;
  hideNavigation?: boolean;
  largeText?: boolean;
}

export default function ChunkReader({ 
  chunk, 
  onNavigate, 
  onComplete,
  isLoading = false,
  hideNavigation = false,
  largeText = false
}: ChunkReaderProps) {
  const [selectedImage, setSelectedImage] = useState<ChunkImage | null>(null);

  // Create a map of image tags to image data
  const imageMap = chunk.images.reduce((acc, img) => {
    if (img.image_tag) {
      acc[img.image_tag] = img;
    }
    return acc;
  }, {} as Record<string, ChunkImage>);

  // Render content with embedded images
  const renderContent = () => {
    // Split content into segments, handling image tags
    const segments: React.ReactNode[] = [];
    let currentText = chunk.content;
    let keyIndex = 0;
    
    // Regex to find image tags
    const imageRegex = /<image>(.*?)<\/image>/g;
    let lastIndex = 0;
    let match;
    
    while ((match = imageRegex.exec(currentText)) !== null) {
      // Add text before the image tag
      if (match.index > lastIndex) {
        const textBefore = currentText.substring(lastIndex, match.index);
        if (textBefore.trim()) {
          // Split by double newlines to preserve paragraphs
          const paragraphs = textBefore.split(/\n\n+/).filter(p => p.trim());
          paragraphs.forEach(paragraph => {
            segments.push(
              <p key={`text-${keyIndex++}`} className={`text-gray-800 mb-6 ${
                largeText 
                  ? 'text-xl leading-loose' 
                  : 'text-base sm:text-lg leading-relaxed'
              }`}>
                {paragraph.trim()}
              </p>
            );
          });
        }
      }
      
      // Add the image
      const imageTag = match[1];
      const image = imageMap[imageTag];
      
      if (image) {
        segments.push(
          <button
            key={`img-${keyIndex++}`}
            onClick={() => setSelectedImage(image)}
            className="float-left mr-4 mb-4 relative group cursor-pointer overflow-hidden rounded-lg shadow-md hover:shadow-xl transition-shadow"
            style={{ maxWidth: '300px' }}
          >
            <img
              src={image.thumbnail_url || image.url}
              alt={image.description || ''}
              className="w-full h-auto object-cover"
              style={{ maxHeight: '225px' }}
            />
            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-opacity flex items-center justify-center">
              <span className="text-white opacity-0 group-hover:opacity-100 transition-opacity bg-black bg-opacity-50 px-2 py-1 rounded text-sm">
                Click to enlarge
              </span>
            </div>
          </button>
        );
      }
      
      lastIndex = match.index + match[0].length;
    }
    
    // Add any remaining text after the last image
    if (lastIndex < currentText.length) {
      const remainingText = currentText.substring(lastIndex);
      if (remainingText.trim()) {
        // Split by double newlines to preserve paragraphs
        const paragraphs = remainingText.split(/\n\n+/).filter(p => p.trim());
        paragraphs.forEach(paragraph => {
          segments.push(
            <p key={`text-${keyIndex++}`} className={`text-gray-800 mb-6 ${
              largeText 
                ? 'text-xl leading-loose' 
                : 'text-base sm:text-lg leading-relaxed'
            }`}>
              {paragraph.trim()}
            </p>
          );
        });
      }
    }
    
    return segments;
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6 flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-gray-400 animate-spin" />
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-lg shadow-sm">
        {/* Content - no header needed */}
        <div className={`${largeText ? 'p-8' : 'p-6'} max-h-[80vh] overflow-y-auto`}>
          <div className="prose prose-lg max-w-none">
            <div className="clearfix">
              {renderContent()}
            </div>
          </div>
        </div>

      </div>

      {/* Image Modal */}
      {selectedImage && (
        <ImageModal
          imageUrl={selectedImage.url}
          altText={selectedImage.description}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </>
  );
}