'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import MetadataForm from '@/components/AssignmentCreator/MetadataForm';
import ContentEditor from '@/components/AssignmentCreator/ContentEditor';
import { ReadingAssignmentMetadata, ReadingAssignment, AssignmentImage } from '@/types/reading';
import { readingApi } from '@/lib/readingApi';

export default function NewReadingAssignment() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [metadata, setMetadata] = useState<Partial<ReadingAssignmentMetadata>>({});
  const [assignment, setAssignment] = useState<ReadingAssignment | null>(null);
  const [content, setContent] = useState('');
  const [images, setImages] = useState<AssignmentImage[]>([]);

  const handleMetadataSubmit = async () => {
    try {
      // Create draft with initial content
      const draftData = {
        ...metadata as ReadingAssignmentMetadata,
        raw_content: content || '', // Empty content is now allowed
      };
      
      const createdAssignment = await readingApi.createDraft(draftData);
      setAssignment(createdAssignment);
      setContent(createdAssignment.raw_content);
      setImages(createdAssignment.images || []);
      setStep(2);
    } catch (error) {
      console.error('Error creating draft:', error);
      alert('Failed to create draft. Please try again.');
    }
  };

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
    // Don't auto-save on every keystroke - let auto-save timer handle it
  };

  // Auto-save functionality
  const saveContent = async () => {
    if (assignment && content !== assignment.raw_content) {
      try {
        console.log('Saving content...');
        const updated = await readingApi.updateAssignment(assignment.id, {
          raw_content: content,
        });
        setAssignment(updated);
        console.log('Content saved successfully');
      } catch (error) {
        console.error('Error saving content:', error);
      }
    }
  };

  const handleBack = () => {
    setStep(1);
  };

  const handleValidate = async () => {
    if (!assignment) return;
    
    try {
      // Save content first
      await saveContent();
      
      const result = await readingApi.validateMarkup(assignment.id);
      return result;
    } catch (error) {
      console.error('Validation error:', error);
      throw error;
    }
  };

  const handlePublish = async () => {
    if (!assignment) return;
    
    try {
      const result = await readingApi.publishAssignment(assignment.id);
      if (result.success) {
        alert(`Assignment published successfully! Created ${result.chunk_count} chunks.`);
        router.push('/teacher/uma-read');
      } else {
        alert(`Failed to publish: ${result.message}`);
      }
    } catch (error) {
      console.error('Publishing error:', error);
      alert('Failed to publish assignment. Please try again.');
    }
  };

  const handleImageUpload = async (file: File, customName?: string) => {
    if (!assignment) throw new Error('No assignment created yet');
    
    try {
      const uploadedImage = await readingApi.uploadImage(assignment.id, file, customName);
      setImages([...images, uploadedImage]);
      return uploadedImage;
    } catch (error) {
      console.error('Image upload error:', error);
      throw error;
    }
  };

  const handleImageDelete = async (imageId: string) => {
    if (!assignment) return;
    
    try {
      await readingApi.deleteImage(assignment.id, imageId);
      setImages(images.filter(img => img.id !== imageId));
    } catch (error) {
      console.error('Image delete error:', error);
      throw error;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Progress Indicator */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center py-4">
            <div className="flex items-center">
              <div className={`flex items-center ${step >= 1 ? 'text-blue-600' : 'text-gray-400'}`}>
                <span className={`flex items-center justify-center w-8 h-8 rounded-full ${
                  step >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200'
                }`}>
                  1
                </span>
                <span className="ml-2 font-medium">Metadata</span>
              </div>
              
              <div className={`mx-8 w-24 h-1 ${step >= 2 ? 'bg-blue-600' : 'bg-gray-200'}`} />
              
              <div className={`flex items-center ${step >= 2 ? 'text-blue-600' : 'text-gray-400'}`}>
                <span className={`flex items-center justify-center w-8 h-8 rounded-full ${
                  step >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200'
                }`}>
                  2
                </span>
                <span className="ml-2 font-medium">Content</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Step Content */}
      <div className="py-8">
        {step === 1 ? (
          <MetadataForm
            data={metadata}
            onChange={setMetadata}
            onNext={handleMetadataSubmit}
          />
        ) : (
          <ContentEditor
            assignmentId={assignment?.id || ''}
            content={content}
            onChange={handleContentChange}
            onBack={handleBack}
            onValidate={handleValidate}
            onPublish={handlePublish}
            images={images}
            onImageUpload={handleImageUpload}
            onImageDelete={handleImageDelete}
          />
        )}
      </div>
    </div>
  );
}