'use client';

import React, { useState } from 'react';
import { ReadingAssignment, ReadingAssignmentUpdate } from '@/types/reading';

interface AssignmentMetadataEditorProps {
  assignment: ReadingAssignment;
  onSave: (data: ReadingAssignmentUpdate) => Promise<void>;
  onCancel: () => void;
}

const GRADE_LEVELS = ['K-2', '3-5', '6-8', '9-10', '11-12', 'College', 'Adult Education'] as const;
const GENRES = [
  'Adventure', 'Fantasy', 'Historical', 'Mystery', 'Mythology',
  'Realistic Fiction', 'Science Fiction', 'Biography', 'Essay',
  'Informational', 'Science', 'Other'
] as const;
const SUBJECTS = ['English Literature', 'History', 'Science', 'Social Studies', 'ESL/ELL', 'Other'] as const;

export default function AssignmentMetadataEditor({ assignment, onSave, onCancel }: AssignmentMetadataEditorProps) {
  const [formData, setFormData] = useState<ReadingAssignmentUpdate>({
    assignment_title: assignment.assignment_title,
    work_title: assignment.work_title,
    author: assignment.author,
    grade_level: assignment.grade_level as any,
    work_type: assignment.work_type as any,
    literary_form: assignment.literary_form as any,
    genre: assignment.genre as any,
    subject: assignment.subject as any,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleInputChange = (field: keyof ReadingAssignmentUpdate, value: any) => {
    setFormData({ ...formData, [field]: value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    setSaving(true);
    setError('');
    
    try {
      await onSave(formData);
    } catch (err) {
      setError('Failed to save metadata');
      console.error('Error saving metadata:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto p-6">
        <h2 className="text-2xl font-bold mb-6">Edit Assignment Metadata</h2>
        
        <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="assignment_title" className="block text-sm font-medium text-gray-700 mb-2">
            Assignment Title *
          </label>
          <input
            type="text"
            id="assignment_title"
            value={formData.assignment_title || ''}
            onChange={(e) => handleInputChange('assignment_title', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        <div>
          <label htmlFor="work_title" className="block text-sm font-medium text-gray-700 mb-2">
            Work Title *
          </label>
          <input
            type="text"
            id="work_title"
            value={formData.work_title || ''}
            onChange={(e) => handleInputChange('work_title', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        <div>
          <label htmlFor="author" className="block text-sm font-medium text-gray-700 mb-2">
            Author
          </label>
          <input
            type="text"
            id="author"
            value={formData.author || ''}
            onChange={(e) => handleInputChange('author', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label htmlFor="grade_level" className="block text-sm font-medium text-gray-700 mb-2">
            Grade Level *
          </label>
          <select
            id="grade_level"
            value={formData.grade_level || ''}
            onChange={(e) => handleInputChange('grade_level', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          >
            <option value="">Select a grade level</option>
            {GRADE_LEVELS.map(level => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Work Type *
          </label>
          <div className="space-x-6">
            <label className="inline-flex items-center">
              <input
                type="radio"
                name="work_type"
                value="fiction"
                checked={formData.work_type === 'fiction'}
                onChange={(e) => handleInputChange('work_type', e.target.value)}
                className="mr-2"
              />
              Fiction
            </label>
            <label className="inline-flex items-center">
              <input
                type="radio"
                name="work_type"
                value="non-fiction"
                checked={formData.work_type === 'non-fiction'}
                onChange={(e) => handleInputChange('work_type', e.target.value)}
                className="mr-2"
              />
              Non-Fiction
            </label>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Literary Form *
          </label>
          <div className="space-x-6">
            {['prose', 'poetry', 'drama', 'mixed'].map(form => (
              <label key={form} className="inline-flex items-center">
                <input
                  type="radio"
                  name="literary_form"
                  value={form}
                  checked={formData.literary_form === form}
                  onChange={(e) => handleInputChange('literary_form', e.target.value)}
                  className="mr-2"
                />
                {form.charAt(0).toUpperCase() + form.slice(1)}
              </label>
            ))}
          </div>
        </div>

        <div>
          <label htmlFor="genre" className="block text-sm font-medium text-gray-700 mb-2">
            Genre *
          </label>
          <select
            id="genre"
            value={formData.genre || ''}
            onChange={(e) => handleInputChange('genre', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          >
            <option value="">Select a genre</option>
            {GENRES.map(genre => (
              <option key={genre} value={genre}>{genre}</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-2">
            Subject *
          </label>
          <select
            id="subject"
            value={formData.subject || ''}
            onChange={(e) => handleInputChange('subject', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          >
            <option value="">Select a subject</option>
            {SUBJECTS.map(subject => (
              <option key={subject} value={subject}>{subject}</option>
            ))}
          </select>
        </div>

        {error && (
          <div className="text-red-600 text-sm">{error}</div>
        )}

        <div className="flex justify-end space-x-4 pt-6">
          <button
            type="button"
            onClick={onCancel}
            className="px-6 py-3 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className={`px-6 py-3 rounded-lg font-medium ${
              saving
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
    </div>
  );
}