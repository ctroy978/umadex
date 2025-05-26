'use client';

import React, { useState, useRef, useEffect } from 'react';
import ImageManager from './ImageManager';
import ChunkPreview from './ChunkPreview';
import ValidationMessages from './ValidationMessages';
import { AssignmentImage, MarkupValidationResult } from '@/types/reading';

interface ContentEditorProps {
  assignmentId: string;
  content: string;
  onChange: (content: string) => void;
  onBack: () => void;
  onValidate: () => Promise<MarkupValidationResult>;
  onPublish: () => Promise<void>;
  images: AssignmentImage[];
  onImageUpload: (file: File, customName?: string) => Promise<AssignmentImage>;
  onImageDelete: (imageId: string) => Promise<void>;
}

export default function ContentEditor({
  assignmentId,
  content,
  onChange,
  onBack,
  onValidate,
  onPublish,
  images,
  onImageUpload,
  onImageDelete,
}: ContentEditorProps) {
  const [validationResult, setValidationResult] = useState<MarkupValidationResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-save functionality
  useEffect(() => {
    const saveTimer = setInterval(() => {
      if (content) {
        // Auto-save logic would go here
        console.log('Auto-saving...');
      }
    }, 30000); // Every 30 seconds

    return () => clearInterval(saveTimer);
  }, [content]);

  const insertTag = (tag: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = content.substring(start, end);
    const newText = `<${tag}>${selectedText}</${tag}>`;
    
    const newContent = content.substring(0, start) + newText + content.substring(end);
    onChange(newContent);
    
    // Reset cursor position
    setTimeout(() => {
      textarea.selectionStart = start + tag.length + 2;
      textarea.selectionEnd = start + tag.length + 2 + selectedText.length;
      textarea.focus();
    }, 0);
  };


  const handleValidate = async () => {
    setIsValidating(true);
    try {
      const result = await onValidate();
      setValidationResult(result);
    } catch (error) {
      console.error('Validation error:', error);
    } finally {
      setIsValidating(false);
    }
  };

  const handlePublish = async () => {
    // First validate
    await handleValidate();
    
    // Check if validation passed
    if (validationResult && !validationResult.is_valid) {
      return;
    }

    setIsPublishing(true);
    try {
      await onPublish();
    } catch (error) {
      console.error('Publishing error:', error);
    } finally {
      setIsPublishing(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">Create Reading Assignment - Step 2: Content</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content Area */}
        <div className="lg:col-span-2 space-y-4">
          {/* Markup Helpers */}
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Markup Helpers</h3>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => insertTag('chunk')}
                className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm font-medium"
              >
                Insert &lt;chunk&gt;
              </button>
              <button
                type="button"
                onClick={() => insertTag('important')}
                className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200 text-sm font-medium"
              >
                Insert &lt;important&gt;
              </button>
              <div className="flex-1" />
              <span className="text-xs text-gray-500 self-center">
                Select text first, then click to wrap with tags
              </span>
            </div>
          </div>

          {/* Content Textarea */}
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <label htmlFor="content" className="block text-sm font-medium text-gray-700 mb-2">
              Content with Markup
            </label>
            <textarea
              ref={textareaRef}
              id="content"
              value={content}
              onChange={(e) => onChange(e.target.value)}
              className="w-full h-96 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
              placeholder="Paste or type your content here. Use <chunk> tags to divide the text into sections..."
            />
          </div>

          {/* Validation Messages */}
          {validationResult && (
            <ValidationMessages validationResult={validationResult} />
          )}

          {/* Action Buttons */}
          <div className="flex justify-between">
            <button
              type="button"
              onClick={onBack}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Back to Metadata
            </button>
            
            <div className="space-x-3">
              <button
                type="button"
                onClick={handleValidate}
                disabled={isValidating || !content}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
              >
                {isValidating ? 'Validating...' : 'Validate Markup'}
              </button>
              
              <button
                type="button"
                onClick={handlePublish}
                disabled={isPublishing || !validationResult?.is_valid}
                className={`px-6 py-2 rounded-lg font-medium ${
                  validationResult?.is_valid
                    ? 'bg-green-600 text-white hover:bg-green-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                {isPublishing ? 'Publishing...' : 'Publish Assignment'}
              </button>
            </div>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          {/* Image Manager */}
          <ImageManager
            images={images}
            onUpload={onImageUpload}
            onDelete={onImageDelete}
          />

          {/* Chunk Preview */}
          <ChunkPreview content={content} images={images} />
        </div>
      </div>
    </div>
  );
}