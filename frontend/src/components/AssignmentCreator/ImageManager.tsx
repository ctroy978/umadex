'use client';

import React, { useState, useRef } from 'react';
import { AssignmentImage } from '@/types/reading';

interface ImageManagerProps {
  images: AssignmentImage[];
  onUpload: (file: File) => Promise<AssignmentImage>;
  onDelete: (imageId: string) => Promise<void>;
}

export default function ImageManager({ images, onUpload, onDelete }: ImageManagerProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const MAX_IMAGES = 10;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      await handleFiles(e.target.files);
    }
  };

  const validateImage = (file: File): string | null => {
    const maxSize = 5 * 1024 * 1024; // 5MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

    if (file.size > maxSize) {
      return `Image must be smaller than 5MB (current: ${(file.size / 1024 / 1024).toFixed(1)}MB)`;
    }
    
    if (!allowedTypes.includes(file.type)) {
      return 'Please upload JPEG, PNG, GIF, or WebP images';
    }
    
    return null;
  };

  const handleFiles = async (files: FileList) => {
    setIsUploading(true);
    setUploadError(null);
    
    try {
      for (let i = 0; i < files.length; i++) {
        if (images.length >= MAX_IMAGES) {
          setUploadError(`Maximum ${MAX_IMAGES} images allowed per assignment`);
          break;
        }
        
        const file = files[i];
        const error = validateImage(file);
        
        if (error) {
          setUploadError(error);
          continue;
        }
        
        if (file.type.startsWith('image/')) {
          await onUpload(file);
        }
      }
    } catch (error: any) {
      setUploadError(error.message || 'Failed to upload image');
    } finally {
      setIsUploading(false);
      // Clear file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (imageId: string) => {
    if (confirm('Are you sure you want to delete this image?')) {
      try {
        await onDelete(imageId);
      } catch (error) {
        console.error('Delete error:', error);
      }
    }
  };

  const copyToClipboard = async (tag: string) => {
    const text = `<image>${tag}</image>`;
    try {
      await navigator.clipboard.writeText(text);
      // Show brief success feedback
      const button = document.getElementById(`copy-${tag}`);
      if (button) {
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        setTimeout(() => {
          button.textContent = originalText;
        }, 1500);
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
      <h3 className="text-lg font-medium mb-4">Uploaded Images</h3>
      
      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-4 text-center ${
          dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300'
        } ${images.length >= MAX_IMAGES ? 'opacity-50 cursor-not-allowed' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/jpeg,image/png,image/gif,image/webp"
          onChange={handleChange}
          className="hidden"
          disabled={images.length >= MAX_IMAGES}
        />
        
        <div className="space-y-2">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || images.length >= MAX_IMAGES}
            className="text-sm text-blue-600 hover:text-blue-500 disabled:text-gray-400 disabled:cursor-not-allowed"
          >
            {isUploading ? 'Uploading...' : 
             images.length >= MAX_IMAGES ? 'Maximum images reached' :
             'Click to upload or drag and drop'}
          </button>
          
          <p className="text-xs text-gray-500">
            JPEG, PNG, GIF, or WebP up to 5MB each
          </p>
        </div>
      </div>

      {/* Error message */}
      {uploadError && (
        <div className="mt-2 text-sm text-red-600">
          {uploadError}
        </div>
      )}

      {/* Image List */}
      <div className="mt-4 space-y-2 max-h-96 overflow-y-auto">
        {images.map((image) => (
          <div
            key={image.id}
            className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded"
          >
            <img
              src={
                image.thumbnail_url.startsWith('http://') || image.thumbnail_url.startsWith('https://')
                  ? image.thumbnail_url 
                  : `${(process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') || 'http://localhost')}${image.thumbnail_url}`
              }
              alt={image.file_name || image.image_tag}
              className="w-16 h-12 object-cover rounded"
            />
            
            <div className="flex-1">
              <code className="text-sm bg-gray-100 px-2 py-1 rounded font-mono">
                &lt;image&gt;{image.image_tag}&lt;/image&gt;
              </code>
              <button
                id={`copy-${image.image_tag}`}
                onClick={() => copyToClipboard(image.image_tag)}
                className="ml-2 text-sm text-blue-600 hover:underline"
              >
                Copy
              </button>
              {image.file_name && (
                <p className="text-xs text-gray-500 mt-1">{image.file_name}</p>
              )}
            </div>
            
            <button
              type="button"
              onClick={() => handleDelete(image.id)}
              className="p-1 text-red-500 hover:text-red-700"
              title="Delete image"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ))}
        
        {images.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">
            No images uploaded yet
          </p>
        )}
      </div>
      
      {/* Image count */}
      <div className="mt-4 text-sm text-gray-600">
        {images.length} of {MAX_IMAGES} images used
      </div>
    </div>
  );
}