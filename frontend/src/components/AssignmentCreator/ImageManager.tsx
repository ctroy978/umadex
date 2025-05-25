'use client';

import React, { useState, useRef } from 'react';
import { AssignmentImage } from '@/types/reading';

interface ImageManagerProps {
  images: AssignmentImage[];
  onUpload: (file: File, customName?: string) => Promise<AssignmentImage>;
  onDelete: (imageId: string) => Promise<void>;
  onInsert: (imageKey: string) => void;
}

export default function ImageManager({ images, onUpload, onDelete, onInsert }: ImageManagerProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleFiles = async (files: FileList) => {
    setIsUploading(true);
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.type.startsWith('image/')) {
          await onUpload(file);
        }
      }
    } catch (error) {
      console.error('Upload error:', error);
    } finally {
      setIsUploading(false);
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

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
      <h3 className="text-lg font-medium mb-4">Images</h3>
      
      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-4 text-center ${
          dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*"
          onChange={handleChange}
          className="hidden"
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
            disabled={isUploading}
            className="text-sm text-blue-600 hover:text-blue-500"
          >
            {isUploading ? 'Uploading...' : 'Click to upload or drag and drop'}
          </button>
          
          <p className="text-xs text-gray-500">PNG, JPG, GIF up to 10MB</p>
        </div>
      </div>

      {/* Image List */}
      <div className="mt-4 space-y-2 max-h-96 overflow-y-auto">
        {images.map((image) => (
          <div
            key={image.id}
            className="flex items-center space-x-3 p-2 hover:bg-gray-50 rounded"
          >
            <img
              src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost'}${image.file_url}`}
              alt={image.custom_name || image.image_key}
              className="w-16 h-16 object-cover rounded"
            />
            
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {image.image_key}
              </p>
              {image.custom_name && (
                <p className="text-xs text-gray-500 truncate">{image.custom_name}</p>
              )}
            </div>
            
            <div className="flex space-x-1">
              <button
                type="button"
                onClick={() => onInsert(image.image_key)}
                className="p-1 text-blue-600 hover:text-blue-800"
                title="Insert image"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
              
              <button
                type="button"
                onClick={() => handleDelete(image.id)}
                className="p-1 text-red-600 hover:text-red-800"
                title="Delete image"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        ))}
        
        {images.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">
            No images uploaded yet
          </p>
        )}
      </div>
    </div>
  );
}