'use client';

import React from 'react';
import { ReadingAssignmentMetadata } from '@/types/reading';

interface MetadataFormProps {
  data: Partial<ReadingAssignmentMetadata>;
  onChange: (data: Partial<ReadingAssignmentMetadata>) => void;
  onNext: () => void;
}

const GRADE_LEVELS = ['K-2', '3-5', '6-8', '9-10', '11-12', 'College', 'Adult Education'] as const;
const GENRES = [
  'Adventure', 'Fantasy', 'Historical', 'Mystery', 'Mythology',
  'Realistic Fiction', 'Science Fiction', 'Biography', 'Essay',
  'Informational', 'Science', 'Other'
] as const;
const SUBJECTS = ['English Literature', 'History', 'Science', 'Social Studies', 'ESL/ELL', 'Other'] as const;

export default function MetadataForm({ data, onChange, onNext }: MetadataFormProps) {
  const handleInputChange = (field: keyof ReadingAssignmentMetadata, value: any) => {
    onChange({ ...data, [field]: value });
  };

  const isFormValid = () => {
    return !!(
      data.assignment_title &&
      data.work_title &&
      data.grade_level &&
      data.work_type &&
      data.literary_form &&
      data.genre &&
      data.subject
    );
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">Create Reading Assignment - Step 1: Metadata</h2>
      
      <form className="space-y-6">
        <div>
          <label htmlFor="assignment_title" className="block text-sm font-medium text-gray-700 mb-2">
            Assignment Title *
          </label>
          <input
            type="text"
            id="assignment_title"
            value={data.assignment_title || ''}
            onChange={(e) => handleInputChange('assignment_title', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="e.g., Greek Mythology Reading"
          />
        </div>

        <div>
          <label htmlFor="work_title" className="block text-sm font-medium text-gray-700 mb-2">
            Work Title *
          </label>
          <input
            type="text"
            id="work_title"
            value={data.work_title || ''}
            onChange={(e) => handleInputChange('work_title', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="e.g., Tales of Ancient Greece"
          />
        </div>

        <div>
          <label htmlFor="author" className="block text-sm font-medium text-gray-700 mb-2">
            Author (Optional)
          </label>
          <input
            type="text"
            id="author"
            value={data.author || ''}
            onChange={(e) => handleInputChange('author', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="e.g., Jane Smith"
          />
        </div>

        <div>
          <label htmlFor="grade_level" className="block text-sm font-medium text-gray-700 mb-2">
            Grade Level *
          </label>
          <select
            id="grade_level"
            value={data.grade_level || ''}
            onChange={(e) => handleInputChange('grade_level', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                checked={data.work_type === 'fiction'}
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
                checked={data.work_type === 'non-fiction'}
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
                  checked={data.literary_form === form}
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
            value={data.genre || ''}
            onChange={(e) => handleInputChange('genre', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
            value={data.subject || ''}
            onChange={(e) => handleInputChange('subject', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select a subject</option>
            {SUBJECTS.map(subject => (
              <option key={subject} value={subject}>{subject}</option>
            ))}
          </select>
        </div>

        <div className="flex justify-end pt-6">
          <button
            type="button"
            onClick={onNext}
            disabled={!isFormValid()}
            className={`px-6 py-3 rounded-lg font-medium ${
              isFormValid()
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Next: Add Content
          </button>
        </div>
      </form>
    </div>
  );
}