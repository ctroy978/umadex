'use client';

import { useEffect } from 'react';
import { X } from 'lucide-react';

interface ImageModalProps {
  imageUrl: string;
  altText: string;
  onClose: () => void;
}

export default function ImageModal({ imageUrl, altText, onClose }: ImageModalProps) {
  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4 select-none"
      onClick={onClose}
      onCopy={(e) => e.preventDefault()}
      onPaste={(e) => e.preventDefault()}
      onCut={(e) => e.preventDefault()}
      onDragStart={(e) => e.preventDefault()}
      onContextMenu={(e) => e.preventDefault()}
      style={{ userSelect: 'none', WebkitUserSelect: 'none', msUserSelect: 'none' }}
    >
      <div 
        className="relative max-w-7xl max-h-[90vh] bg-white rounded-lg shadow-xl select-none"
        onClick={(e) => e.stopPropagation()}
        style={{ userSelect: 'none', WebkitUserSelect: 'none', msUserSelect: 'none' }}
      >
        <button
          onClick={onClose}
          className="absolute top-2 right-2 z-10 p-2 bg-white rounded-full shadow-lg hover:bg-gray-100 transition-colors"
          aria-label="Close image"
        >
          <X className="w-6 h-6 text-gray-700" />
        </button>
        
        <div className="p-2">
          <img
            src={imageUrl}
            alt={altText}
            className="max-w-full max-h-[calc(90vh-4rem)] object-contain"
          />
        </div>
      </div>
    </div>
  );
}