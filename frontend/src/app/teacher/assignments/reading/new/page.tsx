'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import MetadataForm from '@/components/AssignmentCreator/MetadataForm';
import ContentEditor from '@/components/AssignmentCreator/ContentEditor';
import { ReadingAssignmentMetadata, ReadingAssignment, AssignmentImage } from '@/types/reading';
import { readingApi } from '@/lib/readingApi';
import { supabase } from '@/lib/supabase';

export default function NewReadingAssignment() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [step, setStep] = useState(1);
  const [metadata, setMetadata] = useState<Partial<ReadingAssignmentMetadata>>({});
  const [assignment, setAssignment] = useState<ReadingAssignment | null>(null);
  const [content, setContent] = useState('');
  const [images, setImages] = useState<AssignmentImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPublishing, setIsPublishing] = useState(false);

  // Load assignment if ID is in URL
  useEffect(() => {
    const loadAssignment = async () => {
      const assignmentId = searchParams.get('id');
      const stepParam = searchParams.get('step');
      
      if (assignmentId) {
        try {
          const loadedAssignment = await readingApi.getAssignmentForEdit(assignmentId);
          setAssignment(loadedAssignment);
          setContent(loadedAssignment.raw_content || '');
          setImages(loadedAssignment.images || []);
          setMetadata({
            assignment_title: loadedAssignment.assignment_title,
            work_title: loadedAssignment.work_title,
            author: loadedAssignment.author,
            grade_level: loadedAssignment.grade_level,
            work_type: loadedAssignment.work_type,
            subject: loadedAssignment.subject,
            description: loadedAssignment.description,
            start_date: loadedAssignment.start_date,
            end_date: loadedAssignment.end_date,
          });
          // Set step based on URL or default to content editing
          setStep(stepParam === '1' ? 1 : 2);
        } catch (error) {
          console.error('Error loading assignment:', error);
        }
      }
      setLoading(false);
    };

    loadAssignment();
  }, [searchParams]);

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
      
      // Update URL to include assignment ID without navigating
      const newUrl = `/teacher/assignments/reading/new?id=${createdAssignment.id}&step=2`;
      window.history.pushState({}, '', newUrl);
      
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
      alert('Failed to validate assignment. Please check your content and try again.');
      throw error;
    }
  };

  const handlePublish = async () => {
    if (!assignment || isPublishing) return;
    
    setIsPublishing(true);
    
    // Set a timeout to prevent infinite loading
    const timeoutId = setTimeout(() => {
      setIsPublishing(false);
      alert('Publishing is taking longer than expected. Please check your assignment and try again.');
    }, 60000); // 60 seconds timeout
    
    try {
      const result = await readingApi.publishAssignment(assignment.id);
      clearTimeout(timeoutId);
      
      if (result.success) {
        // Show success message
        alert(`Assignment published successfully! Created ${result.chunk_count} chunks.`);
        
        // Small delay to ensure the alert is shown before navigation
        setTimeout(() => {
          router.push('/teacher/uma-read');
        }, 100);
      } else {
        alert(`Failed to publish: ${result.message}`);
        setIsPublishing(false);
      }
    } catch (error) {
      clearTimeout(timeoutId);
      console.error('Publishing error:', error);
      
      // Check for specific error types
      if (error instanceof Error) {
        if (error.message.includes('timeout')) {
          alert('The request timed out. Please check your internet connection and try again.');
        } else {
          alert(`Failed to publish assignment: ${error.message}`);
        }
      } else {
        alert('Failed to publish assignment. Please try again.');
      }
      
      setIsPublishing(false);
    }
  };

  const handleImageUpload = async (file: File, customName?: string) => {
    if (!assignment) throw new Error('No assignment created yet');
    
    try {
      // Generate a unique filename
      const fileExt = file.name.split('.').pop();
      const fileName = `${Date.now()}-${Math.random().toString(36).substring(7)}.${fileExt}`;
      const filePath = `assignments/${assignment.id}/${fileName}`;
      
      // Upload to Supabase Storage
      const { data: storageData, error: storageError } = await supabase.storage
        .from('reading-images')
        .upload(filePath, file, {
          cacheControl: '3600',
          upsert: false
        });
      
      if (storageError) {
        throw new Error(`Storage upload failed: ${storageError.message}`);
      }
      
      // Get the public URL
      const { data: { publicUrl } } = supabase.storage
        .from('reading-images')
        .getPublicUrl(filePath);
      
      // Get image dimensions
      const img = new Image();
      const dimensions = await new Promise<{ width: number; height: number }>((resolve) => {
        img.onload = () => resolve({ width: img.width, height: img.height });
        img.src = URL.createObjectURL(file);
      });
      
      // Save reference to backend
      const uploadedImage = await readingApi.createImageReference({
        assignment_id: assignment.id,
        filename: fileName,
        storage_path: filePath,
        public_url: publicUrl,
        custom_name: customName,
        width: dimensions.width,
        height: dimensions.height,
        file_size: file.size,
        mime_type: file.type
      });
      
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
      // Find the image to get its storage path
      const imageToDelete = images.find(img => img.id === imageId);
      
      if (imageToDelete && imageToDelete.storage_path) {
        // Delete from Supabase Storage
        const { error: storageError } = await supabase.storage
          .from('reading-images')
          .remove([imageToDelete.storage_path]);
        
        if (storageError) {
          console.error('Error deleting from storage:', storageError);
        }
      }
      
      // Delete reference from backend
      await readingApi.deleteImage(assignment.id, imageId);
      setImages(images.filter(img => img.id !== imageId));
    } catch (error) {
      console.error('Image delete error:', error);
      throw error;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

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

      {/* Publishing Overlay */}
      {isPublishing && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full">
            <div className="flex flex-col items-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
              <p className="text-lg font-medium">Publishing assignment...</p>
              <p className="text-sm text-gray-500 mt-2">Please wait while we process your content</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}