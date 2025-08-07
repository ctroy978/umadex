'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, BookOpen, Loader2, Zap } from 'lucide-react';
import ImageModal from './ImageModal';
import CrunchTextModal from './CrunchTextModal';
import { umareadApi } from '@/lib/umareadApi';
import type { ChunkContent, ChunkImage } from '@/types/umaread';

interface ChunkReaderProps {
  chunk: ChunkContent;
  assignmentId: string;
  onNavigate: ((direction: 'prev' | 'next') => void) | null;
  onComplete: (() => void) | null;
  isLoading?: boolean;
  hideNavigation?: boolean;
  largeText?: boolean;
}

export default function ChunkReader({ 
  chunk, 
  assignmentId,
  onNavigate, 
  onComplete,
  isLoading = false,
  hideNavigation = false,
  largeText = false
}: ChunkReaderProps) {
  const [selectedImage, setSelectedImage] = useState<ChunkImage | null>(null);
  const [showCrunchModal, setShowCrunchModal] = useState(false);
  const [simplifiedText, setSimplifiedText] = useState('');
  const [crunchLoading, setCrunchLoading] = useState(false);
  const [crunchError, setCrunchError] = useState<string | null>(null);

  const handleCrunchText = async () => {
    setShowCrunchModal(true);
    setCrunchLoading(true);
    setCrunchError(null);
    
    try {
      const response = await umareadApi.crunchText(assignmentId, chunk.chunk_number);
      setSimplifiedText(response.simplified_text);
    } catch (error) {
      console.error('Error getting simplified text:', error);
      setCrunchError('Unable to generate simplified text. Please try again.');
    } finally {
      setCrunchLoading(false);
    }
  };

  const handleRetrycrunch = () => {
    handleCrunchText();
  };

  const handleCloseCrunchModal = () => {
    setShowCrunchModal(false);
    setCrunchError(null);
    setSimplifiedText('');
  };

  // Create a map of image tags to image data
  const imageMap = chunk.images.reduce((acc, img) => {
    if (img.image_tag) {
      acc[img.image_tag] = img;
    }
    return acc;
  }, {} as Record<string, ChunkImage>);

  // Helper function to render text with important tags highlighted
  const renderTextWithImportant = (text: string, baseKey: number) => {
    const segments: React.ReactNode[] = [];
    const importantRegex = /<important>(.*?)<\/important>/g;
    let lastIndex = 0;
    let match;
    let keyIndex = 0;
    
    while ((match = importantRegex.exec(text)) !== null) {
      // Add text before the important tag
      if (match.index > lastIndex) {
        const textBefore = text.substring(lastIndex, match.index);
        if (textBefore) {
          segments.push(textBefore);
        }
      }
      
      // Add the highlighted important text
      segments.push(
        <span key={`important-${baseKey}-${keyIndex++}`} className="bg-yellow-200 font-semibold px-1">
          {match[1]}
        </span>
      );
      
      lastIndex = match.index + match[0].length;
    }
    
    // Add any remaining text after the last important tag
    if (lastIndex < text.length) {
      const remainingText = text.substring(lastIndex);
      if (remainingText) {
        segments.push(remainingText);
      }
    }
    
    return segments.length > 0 ? segments : text;
  };

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
                {renderTextWithImportant(paragraph.trim(), keyIndex)}
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
          <div key={`img-wrapper-${keyIndex++}`} className="my-4 flex justify-center clear-both">
            <button
              onClick={() => setSelectedImage(image)}
              className="relative group cursor-pointer overflow-hidden rounded-lg shadow-md hover:shadow-xl transition-shadow"
              style={{ width: '200px', height: '200px' }}
            >
              <img
                src={image.thumbnail_url || image.url}
                alt={image.description || ''}
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-opacity flex items-center justify-center">
                <span className="text-white opacity-0 group-hover:opacity-100 transition-opacity bg-black bg-opacity-60 px-2 py-1 rounded text-xs font-medium">
                  Click to view
                </span>
              </div>
            </button>
          </div>
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
              {renderTextWithImportant(paragraph.trim(), keyIndex)}
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
      <div className="bg-white rounded-lg shadow-sm select-none"
           onCopy={(e) => e.preventDefault()}
           onPaste={(e) => e.preventDefault()}
           onCut={(e) => e.preventDefault()}
           onDragStart={(e) => e.preventDefault()}
           onContextMenu={(e) => e.preventDefault()}
           style={{ userSelect: 'none', WebkitUserSelect: 'none', msUserSelect: 'none' }}>
        {/* Header with controls */}
        <div className="flex justify-between items-center p-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900 flex items-center">
            <BookOpen className="w-5 h-5 mr-2 text-blue-600" />
            Reading Text
          </h2>
          <div className="flex gap-2">
            <button
              onClick={handleCrunchText}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-1.5"
              title="Get an easier-to-read version of this text"
            >
              <Zap className="w-4 h-4" />
              Crunch Text
            </button>
          </div>
        </div>

        {/* Content */}
        <div className={`${largeText ? 'p-8' : 'p-6'} max-h-[80vh] overflow-y-auto`}>
          <div className="prose prose-lg max-w-none">
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

      {/* Crunch Text Modal */}
      <CrunchTextModal
        isOpen={showCrunchModal}
        onClose={handleCloseCrunchModal}
        simplifiedText={simplifiedText}
        isLoading={crunchLoading}
        error={crunchError}
        onRetry={handleRetrycrunch}
      />
    </>
  );
}