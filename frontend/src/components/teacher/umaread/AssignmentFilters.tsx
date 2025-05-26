'use client';

import React, { useState } from 'react';
import { ChevronDownIcon, FunnelIcon } from '@heroicons/react/24/outline';

export interface FilterValues {
  dateRange: string;
  dateFrom?: string;
  dateTo?: string;
  gradeLevel: string;
  workType: string;
  includeArchived: boolean;
}

interface AssignmentFiltersProps {
  filters: FilterValues;
  onChange: (filters: FilterValues) => void;
  onClearAll: () => void;
}

const GRADE_LEVELS = [
  { value: '', label: 'All Grades' },
  { value: 'K-2', label: 'K-2' },
  { value: '3-5', label: '3-5' },
  { value: '6-8', label: '6-8' },
  { value: '9-10', label: '9-10' },
  { value: '11-12', label: '11-12' },
  { value: 'College', label: 'College' },
  { value: 'Adult Education', label: 'Adult Education' }
];

const WORK_TYPES = [
  { value: '', label: 'All Types' },
  { value: 'fiction', label: 'Fiction' },
  { value: 'non-fiction', label: 'Non-Fiction' }
];

const DATE_RANGES = [
  { value: 'all', label: 'All Time' },
  { value: '7days', label: 'Last 7 days' },
  { value: '30days', label: 'Last 30 days' },
  { value: '3months', label: 'Last 3 months' },
  { value: 'custom', label: 'Custom range' }
];

export default function AssignmentFilters({
  filters,
  onChange,
  onClearAll
}: AssignmentFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showCustomDates, setShowCustomDates] = useState(filters.dateRange === 'custom');

  const handleDateRangeChange = (value: string) => {
    setShowCustomDates(value === 'custom');
    
    let dateFrom: string | undefined;
    let dateTo: string | undefined;
    
    if (value !== 'all' && value !== 'custom') {
      const now = new Date();
      dateTo = now.toISOString().split('T')[0];
      
      switch (value) {
        case '7days':
          dateFrom = new Date(now.setDate(now.getDate() - 7)).toISOString().split('T')[0];
          break;
        case '30days':
          dateFrom = new Date(now.setDate(now.getDate() - 30)).toISOString().split('T')[0];
          break;
        case '3months':
          dateFrom = new Date(now.setMonth(now.getMonth() - 3)).toISOString().split('T')[0];
          break;
      }
    }
    
    onChange({
      ...filters,
      dateRange: value,
      dateFrom: value === 'custom' ? filters.dateFrom : dateFrom,
      dateTo: value === 'custom' ? filters.dateTo : dateTo
    });
  };

  const hasActiveFilters = () => {
    return filters.dateRange !== 'all' || 
           filters.gradeLevel !== '' || 
           filters.workType !== '' || 
           filters.includeArchived;
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <FunnelIcon className="h-5 w-5 text-gray-500" />
          <span className="font-medium text-gray-700">Filters</span>
          {hasActiveFilters() && (
            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
              Active
            </span>
          )}
        </div>
        <ChevronDownIcon 
          className={`h-5 w-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
        />
      </button>

      {isExpanded && (
        <div className="px-4 py-4 border-t border-gray-200 space-y-4">
          {/* Date Range Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Date Range
            </label>
            <select
              value={filters.dateRange}
              onChange={(e) => handleDateRangeChange(e.target.value)}
              className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            >
              {DATE_RANGES.map(range => (
                <option key={range.value} value={range.value}>
                  {range.label}
                </option>
              ))}
            </select>
          </div>

          {/* Custom Date Range */}
          {showCustomDates && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  From
                </label>
                <input
                  type="date"
                  value={filters.dateFrom || ''}
                  onChange={(e) => onChange({ ...filters, dateFrom: e.target.value })}
                  className="block w-full px-3 py-2 text-sm border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  To
                </label>
                <input
                  type="date"
                  value={filters.dateTo || ''}
                  onChange={(e) => onChange({ ...filters, dateTo: e.target.value })}
                  className="block w-full px-3 py-2 text-sm border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          )}

          {/* Grade Level Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Grade Level
            </label>
            <select
              value={filters.gradeLevel}
              onChange={(e) => onChange({ ...filters, gradeLevel: e.target.value })}
              className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            >
              {GRADE_LEVELS.map(level => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
          </div>

          {/* Work Type Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Work Type
            </label>
            <select
              value={filters.workType}
              onChange={(e) => onChange({ ...filters, workType: e.target.value })}
              className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            >
              {WORK_TYPES.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {/* Include Archived Toggle */}
          <div className="flex items-center justify-between">
            <label htmlFor="include-archived" className="text-sm font-medium text-gray-700">
              Show Archived
            </label>
            <button
              type="button"
              onClick={() => onChange({ ...filters, includeArchived: !filters.includeArchived })}
              className={`${
                filters.includeArchived ? 'bg-blue-600' : 'bg-gray-200'
              } relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
            >
              <span
                className={`${
                  filters.includeArchived ? 'translate-x-5' : 'translate-x-0'
                } pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200`}
              />
            </button>
          </div>

          {/* Clear Filters Button */}
          {hasActiveFilters() && (
            <button
              onClick={onClearAll}
              className="w-full mt-2 px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
            >
              Clear All Filters
            </button>
          )}
        </div>
      )}
    </div>
  );
}