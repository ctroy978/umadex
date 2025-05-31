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
  const [imagePositions, setImagePositions] = useState<Map<number, ChunkImage>>(new Map());

  // Process content to determine image positions
  useEffect(() => {
    if (!chunk.images.length) return;

    // Simple algorithm: distribute images evenly through the content
    const paragraphs = chunk.content.split('\n\n').filter(p => p.trim());
    const imageInterval = Math.max(1, Math.floor(paragraphs.length / chunk.images.length));
    
    const positions = new Map<number, ChunkImage>();
    chunk.images.forEach((img, idx) => {
      const position = Math.min(
        (idx + 1) * imageInterval,
        paragraphs.length - 1
      );
      positions.set(position, img);
    });
    
    setImagePositions(positions);
  }, [chunk]);

  // Render content with embedded images
  const renderContent = () => {
    const paragraphs = chunk.content.split('\n\n').filter(p => p.trim());
    
    return paragraphs.map((paragraph, idx) => (
      <div key={idx}>
        <p className={`text-gray-800 mb-6 ${
          largeText 
            ? 'text-xl leading-loose' 
            : 'text-base sm:text-lg leading-relaxed'
        }`}>
          {paragraph}
        </p>
        
        {imagePositions.has(idx) && (
          <div className="my-6 flex justify-center">
            <button
              onClick={() => setSelectedImage(imagePositions.get(idx)!)}
              className="relative group cursor-pointer overflow-hidden rounded-lg shadow-md hover:shadow-xl transition-shadow"
            >
              <img
                src={imagePositions.get(idx)!.thumbnail_url || imagePositions.get(idx)!.url}
                alt={imagePositions.get(idx)!.description}
                className="w-full max-w-md h-auto object-cover"
                style={{ maxHeight: '300px' }}
              />
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-opacity flex items-center justify-center">
                <span className="text-white opacity-0 group-hover:opacity-100 transition-opacity bg-black bg-opacity-50 px-3 py-1 rounded">
                  Click to enlarge
                </span>
              </div>
            </button>
            {imagePositions.get(idx)!.description && (
              <p className="text-sm text-gray-600 mt-2 text-center italic">
                {imagePositions.get(idx)!.description}
              </p>
            )}
          </div>
        )}
      </div>
    ));
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
            {renderContent()}
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