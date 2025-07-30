'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { format } from 'date-fns';
import {
  FunnelIcon,
  ChevronUpDownIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ArrowDownTrayIcon,
  MagnifyingGlassIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import { api } from '@/lib/api';

interface ClassroomOption {
  id: string;
  name: string;
}

interface AssignmentOption {
  id: string;
  title: string;
  workTitle: string;
  type: string;
}

interface StudentGrade {
  id: string;
  student_id: string;
  student_name: string;
  assignment_id: string;
  assignment_title: string;
  assignment_type: string; // 'UMARead' or 'UMAVocab' or 'UMADebate' or 'UMAWrite' or 'UMATest' or 'UMALecture'
  work_title: string;
  date_assigned: string;
  date_completed: string | null;
  test_date: string | null;
  test_score: number | null | undefined;
  difficulty_reached: number | null;
  time_spent: number | null;
  status: 'completed' | 'in_progress' | 'not_started' | 'test_available';
}

interface FilterState {
  classrooms: string[];
  assignments: string[];
  assignmentTypes: string[];
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
  completionDateRange: {
    start: Date | null;
    end: Date | null;
  };
  studentSearch: string;
  completionStatus: 'all' | 'completed' | 'incomplete';
  scoreRange: {
    min: number | null;
    max: number | null;
  };
  difficultyLevel: number | null;
}

interface SortConfig {
  key: keyof StudentGrade | null;
  direction: 'asc' | 'desc';
}

interface SummaryStats {
  total_students: number;
  average_score: number;
  completion_rate: number;
  average_time: number;
  class_average_by_assignment: Record<string, number>;
}

export default function Gradebook() {
  const [grades, setGrades] = useState<StudentGrade[]>([]);
  const [classrooms, setClassrooms] = useState<ClassroomOption[]>([]);
  const [assignments, setAssignments] = useState<AssignmentOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(true);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: null, direction: 'asc' });
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  
  const [filters, setFilters] = useState<FilterState>({
    classrooms: [],
    assignments: [],
    assignmentTypes: [],
    dateRange: { start: null, end: null },
    completionDateRange: { start: null, end: null },
    studentSearch: '',
    completionStatus: 'all',
    scoreRange: { min: null, max: null },
    difficultyLevel: null
  });

  const [summaryStats, setSummaryStats] = useState<SummaryStats>({
    total_students: 0,
    average_score: 0,
    completion_rate: 0,
    average_time: 0,
    class_average_by_assignment: {}
  });

  // Helper function to safely format dates
  const formatDate = (dateString: string | null | undefined): string => {
    if (!dateString) return '-';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return '-';
      return format(date, 'MMM d, yyyy');
    } catch (error) {
      console.error('Date formatting error:', error);
      return '-';
    }
  };

  // Filter assignments based on selected assignment types
  const filteredAssignments = useMemo(() => {
    if (!filters.assignmentTypes || filters.assignmentTypes.length === 0) {
      return assignments; // Show all if no filter selected
    }
    return assignments.filter(assignment => 
      filters.assignmentTypes.includes(assignment.type)
    );
  }, [assignments, filters.assignmentTypes]);

  // Load initial data
  useEffect(() => {
    fetchClassrooms();
    fetchAssignments();
    fetchGrades();
  }, []);

  // Re-fetch grades when filters change
  useEffect(() => {
    fetchGrades();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, sortConfig, currentPage, pageSize]);

  const fetchClassrooms = async () => {
    try {
      const data = await api.get('/v1/teacher/classrooms');
      // Extract classrooms with id and name
      const classroomOptions = data.data.map((c: any) => ({
        id: c.id,
        name: c.name
      }));
      setClassrooms(classroomOptions);
    } catch (error) {
      console.error('Error fetching classrooms:', error);
    }
  };

  const fetchAssignments = async () => {
    try {
      const allAssignments: AssignmentOption[] = [];
      
      // Fetch UMARead assignments
      try {
        const response = await api.get('/v1/teacher/assignments/reading');
        const readingAssignments = response.data.assignments
          .filter((a: any) => a.assignment_type === 'UMARead')
          .map((a: any) => ({
            id: a.id,
            title: a.assignment_title,
            workTitle: a.work_title,
            type: 'UMARead'
          }));
        allAssignments.push(...readingAssignments);
      } catch (error) {
        console.error('Error fetching reading assignments:', error);
      }
      
      // Fetch UMAVocab assignments (published vocabulary lists)
      try {
        const response = await api.get('/v1/teacher/vocabulary?status=published&per_page=100');
        const vocabAssignments = response.data.items
          .map((v: any) => ({
            id: v.id,
            title: v.title,
            workTitle: `${v.grade_level} - ${v.subject_area}`,
            type: 'UMAVocab'
          }));
        allAssignments.push(...vocabAssignments);
      } catch (error) {
        console.error('Error fetching vocab assignments:', error);
      }
      
      // Fetch UMADebate assignments
      try {
        const response = await api.get('/v1/teacher/debate/assignments');
        const debateAssignments = response.data.assignments
          .filter((d: any) => !d.deleted_at)
          .map((d: any) => ({
            id: d.id,
            title: d.title,
            workTitle: `${d.grade_level} - ${d.subject}`,
            type: 'UMADebate'
          }));
        allAssignments.push(...debateAssignments);
      } catch (error) {
        console.error('Error fetching debate assignments:', error);
      }
      
      // Fetch UMAWrite assignments
      try {
        const response = await api.get('/v1/writing/assignments?per_page=100');
        const writeAssignments = response.data.assignments
          .filter((w: any) => !w.is_archived)
          .map((w: any) => ({
            id: w.id,
            title: w.title,
            workTitle: `${w.grade_level || 'All Grades'} - ${w.subject || 'Writing'}`,
            type: 'UMAWrite'
          }));
        allAssignments.push(...writeAssignments);
      } catch (error) {
        console.error('Error fetching write assignments:', error);
      }
      
      // Fetch UMATest assignments
      try {
        const response = await api.get('/v1/teacher/umatest/tests?status=published&page_size=100');
        const testAssignments = response.data.tests
          .filter((t: any) => t.status === 'published')
          .map((t: any) => ({
            id: t.id,
            title: t.test_title,
            workTitle: t.test_description || 'Comprehensive Test',
            type: 'UMATest'
          }));
        allAssignments.push(...testAssignments);
      } catch (error) {
        console.error('Error fetching UMATest assignments:', error);
      }
      
      // Fetch UMALecture assignments
      try {
        const response = await api.get('/v1/umalecture/lectures?status=published&limit=100');
        const lectureAssignments = response.data
          .filter((l: any) => l.status === 'published')
          .map((l: any) => ({
            id: l.id,
            title: l.title,
            workTitle: `${l.grade_level} - ${l.subject}`,
            type: 'UMALecture'
          }));
        allAssignments.push(...lectureAssignments);
      } catch (error) {
        console.error('Error fetching UMALecture assignments:', error);
      }
      
      setAssignments(allAssignments);
    } catch (error) {
      console.error('Error fetching assignments:', error);
    }
  };

  const fetchGrades = async () => {
    setLoading(true);
    
    try {
      const queryParams = new URLSearchParams();
      
      // Add filter parameters
      if (filters.classrooms.length > 0) {
        queryParams.append('classrooms', filters.classrooms.join(','));
      }
      if (filters.assignments.length > 0) {
        queryParams.append('assignments', filters.assignments.join(','));
      }
      if (filters.assignmentTypes.length > 0) {
        queryParams.append('assignment_types', filters.assignmentTypes.join(','));
      }
      if (filters.dateRange.start) {
        queryParams.append('assigned_after', filters.dateRange.start.toISOString());
      }
      if (filters.dateRange.end) {
        queryParams.append('assigned_before', filters.dateRange.end.toISOString());
      }
      if (filters.completionDateRange.start) {
        queryParams.append('completed_after', filters.completionDateRange.start.toISOString());
      }
      if (filters.completionDateRange.end) {
        queryParams.append('completed_before', filters.completionDateRange.end.toISOString());
      }
      if (filters.studentSearch) {
        queryParams.append('student_search', filters.studentSearch);
      }
      if (filters.completionStatus !== 'all') {
        queryParams.append('completion_status', filters.completionStatus);
      }
      if (filters.scoreRange.min !== null) {
        queryParams.append('min_score', filters.scoreRange.min.toString());
      }
      if (filters.scoreRange.max !== null) {
        queryParams.append('max_score', filters.scoreRange.max.toString());
      }
      if (filters.difficultyLevel !== null) {
        queryParams.append('difficulty_level', filters.difficultyLevel.toString());
      }
      
      // Add pagination
      queryParams.append('page', currentPage.toString());
      queryParams.append('page_size', pageSize.toString());
      
      // Add sorting
      if (sortConfig.key) {
        queryParams.append('sort_by', sortConfig.key);
        queryParams.append('sort_direction', sortConfig.direction);
      }
      
      const response = await api.get(`/v1/teacher/reports/gradebook?${queryParams}`);
      
      setGrades(response.data.grades || []);
      setSummaryStats(response.data.summary || {
        total_students: 0,
        average_score: 0,
        completion_rate: 0,
        average_time: 0,
        class_average_by_assignment: {}
      });
    } catch (error) {
      console.error('Error fetching grades:', error);
      setGrades([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (key: keyof StudentGrade) => {
    setSortConfig({
      key,
      direction: sortConfig.key === key && sortConfig.direction === 'asc' ? 'desc' : 'asc'
    });
  };

  const getScoreColor = (score: number | null | undefined) => {
    if (score === null || score === undefined) return 'text-gray-500 bg-gray-100';
    if (score >= 90) return 'text-green-700 bg-green-100';
    if (score >= 80) return 'text-green-600 bg-green-50';
    if (score >= 70) return 'text-yellow-700 bg-yellow-100';
    if (score >= 60) return 'text-orange-700 bg-orange-100';
    return 'text-red-700 bg-red-100';
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      completed: { color: 'bg-green-100 text-green-800', label: 'Completed' },
      in_progress: { color: 'bg-blue-100 text-blue-800', label: 'In Progress' },
      not_started: { color: 'bg-gray-100 text-gray-800', label: 'Not Started' },
      test_available: { color: 'bg-purple-100 text-purple-800', label: 'Test Available' }
    };
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.not_started;
    
    return (
      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${config.color}`}>
        {config.label}
      </span>
    );
  };

  const exportToCSV = async () => {
    try {
      const queryParams = new URLSearchParams();
      
      // Add all filter parameters
      if (filters.classrooms.length > 0) {
        queryParams.append('classrooms', filters.classrooms.join(','));
      }
      if (filters.assignments.length > 0) {
        queryParams.append('assignments', filters.assignments.join(','));
      }
      if (filters.assignmentTypes.length > 0) {
        queryParams.append('assignment_types', filters.assignmentTypes.join(','));
      }
      // ... add other filters ...
      
      queryParams.append('format', 'csv');
      
      const response = await api.get(`/v1/teacher/reports/gradebook/export?${queryParams}`, {
        responseType: 'blob'
      });
      
      const blob = response.data;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `gradebook_${format(new Date(), 'yyyy-MM-dd')}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting to CSV:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Gradebook</h2>
          <p className="mt-1 text-sm text-gray-600">
            View and analyze student test scores across all your UMARead, UMAVocab, UMADebate, UMAWrite, UMATest, and UMALecture assignments
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <FunnelIcon className="h-4 w-4 mr-2" />
            {showFilters ? 'Hide' : 'Show'} Filters
          </button>
          <button
            onClick={exportToCSV}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="bg-gray-50 p-6 rounded-lg space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Classroom Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Classrooms
              </label>
              <select
                multiple
                value={filters.classrooms}
                onChange={(e) => {
                  const selected = Array.from(e.target.selectedOptions, option => option.value);
                  setFilters({ ...filters, classrooms: selected });
                }}
                className="w-full border-gray-300 rounded-md shadow-sm"
                size={4}
              >
                {classrooms.map(classroom => (
                  <option key={classroom.id} value={classroom.id}>
                    {classroom.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Assignment Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Assignments
              </label>
              <select
                multiple
                value={filters.assignments}
                onChange={(e) => {
                  const selected = Array.from(e.target.selectedOptions, option => option.value);
                  setFilters({ ...filters, assignments: selected });
                }}
                className="w-full border-gray-300 rounded-md shadow-sm"
                size={4}
              >
                {filteredAssignments.map(assignment => (
                  <option key={assignment.id} value={assignment.id}>
                    {assignment.title} - {assignment.workTitle}
                  </option>
                ))}
              </select>
            </div>

            {/* Assignment Type Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Assignment Type
              </label>
              <select
                multiple
                value={filters.assignmentTypes}
                onChange={(e) => {
                  const selected = Array.from(e.target.selectedOptions, option => option.value);
                  // Clear assignments filter when assignment type changes
                  setFilters({ ...filters, assignmentTypes: selected, assignments: [] });
                }}
                className="w-full border-gray-300 rounded-md shadow-sm"
                size={5}
              >
                <option value="UMARead">UMARead</option>
                <option value="UMAVocab">UMAVocab</option>
                <option value="UMADebate">UMADebate</option>
                <option value="UMAWrite">UMAWrite</option>
                <option value="UMATest">UMATest</option>
                <option value="UMALecture">UMALecture</option>
              </select>
            </div>

            {/* Student Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Student Search
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={filters.studentSearch}
                  onChange={(e) => setFilters({ ...filters, studentSearch: e.target.value })}
                  placeholder="Search by student name..."
                  className="w-full border-gray-300 rounded-md shadow-sm pl-10"
                />
                <MagnifyingGlassIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
              </div>
            </div>

            {/* Completion Status */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Completion Status
              </label>
              <select
                value={filters.completionStatus}
                onChange={(e) => setFilters({ ...filters, completionStatus: e.target.value as any })}
                className="w-full border-gray-300 rounded-md shadow-sm"
              >
                <option value="all">All</option>
                <option value="completed">Completed Tests Only</option>
                <option value="incomplete">Incomplete</option>
              </select>
            </div>

            {/* Score Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Score Range
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  placeholder="Min"
                  value={filters.scoreRange.min || ''}
                  onChange={(e) => setFilters({
                    ...filters,
                    scoreRange: { ...filters.scoreRange, min: e.target.value ? Number(e.target.value) : null }
                  })}
                  className="w-1/2 border-gray-300 rounded-md shadow-sm"
                  min="0"
                  max="100"
                />
                <input
                  type="number"
                  placeholder="Max"
                  value={filters.scoreRange.max || ''}
                  onChange={(e) => setFilters({
                    ...filters,
                    scoreRange: { ...filters.scoreRange, max: e.target.value ? Number(e.target.value) : null }
                  })}
                  className="w-1/2 border-gray-300 rounded-md shadow-sm"
                  min="0"
                  max="100"
                />
              </div>
            </div>
          </div>

          {/* Clear Filters */}
          <div className="flex justify-end">
            <button
              onClick={() => {
                setFilters({
                  classrooms: [],
                  assignments: [],
                  assignmentTypes: [],
                  dateRange: { start: null, end: null },
                  completionDateRange: { start: null, end: null },
                  studentSearch: '',
                  completionStatus: 'all',
                  scoreRange: { min: null, max: null },
                  difficultyLevel: null
                });
              }}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              Clear all filters
            </button>
          </div>
        </div>
      )}

      {/* Summary Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-sm font-medium text-gray-600">Total Students</p>
          <p className="text-2xl font-bold text-gray-900">{summaryStats.total_students || 0}</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-sm font-medium text-gray-600">Average Score</p>
          <p className="text-2xl font-bold text-gray-900">
            {(summaryStats.average_score || 0).toFixed(1)}%
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-sm font-medium text-gray-600">Completion Rate</p>
          <p className="text-2xl font-bold text-gray-900">
            {(summaryStats.completion_rate || 0).toFixed(1)}%
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-sm font-medium text-gray-600">Average Time</p>
          <p className="text-2xl font-bold text-gray-900">
            {Math.round(summaryStats.average_time || 0)} min
          </p>
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('student_name')}
                    className="flex items-center gap-1 hover:text-gray-700"
                  >
                    Student Name
                    {sortConfig.key === 'student_name' ? (
                      sortConfig.direction === 'asc' ? <ChevronUpIcon className="h-3 w-3" /> : <ChevronDownIcon className="h-3 w-3" />
                    ) : <ChevronUpDownIcon className="h-3 w-3" />}
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('assignment_title')}
                    className="flex items-center gap-1 hover:text-gray-700"
                  >
                    Assignment
                    {sortConfig.key === 'assignment_title' ? (
                      sortConfig.direction === 'asc' ? <ChevronUpIcon className="h-3 w-3" /> : <ChevronDownIcon className="h-3 w-3" />
                    ) : <ChevronUpDownIcon className="h-3 w-3" />}
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Work Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('date_assigned')}
                    className="flex items-center gap-1 hover:text-gray-700"
                  >
                    Date Assigned
                    {sortConfig.key === 'date_assigned' ? (
                      sortConfig.direction === 'asc' ? <ChevronUpIcon className="h-3 w-3" /> : <ChevronDownIcon className="h-3 w-3" />
                    ) : <ChevronUpDownIcon className="h-3 w-3" />}
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('test_date')}
                    className="flex items-center gap-1 hover:text-gray-700"
                  >
                    Test Date
                    {sortConfig.key === 'test_date' ? (
                      sortConfig.direction === 'asc' ? <ChevronUpIcon className="h-3 w-3" /> : <ChevronDownIcon className="h-3 w-3" />
                    ) : <ChevronUpDownIcon className="h-3 w-3" />}
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('test_score')}
                    className="flex items-center gap-1 hover:text-gray-700"
                  >
                    Test Score
                    {sortConfig.key === 'test_score' ? (
                      sortConfig.direction === 'asc' ? <ChevronUpIcon className="h-3 w-3" /> : <ChevronDownIcon className="h-3 w-3" />
                    ) : <ChevronUpDownIcon className="h-3 w-3" />}
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : grades.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                    No grades found matching your filters
                  </td>
                </tr>
              ) : (
                grades.map((grade) => (
                  <tr key={grade.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {grade.student_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div className="flex items-center gap-2">
                        <div className="max-w-xs truncate" title={grade.assignment_title}>
                          {grade.assignment_title}
                        </div>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          grade.assignment_type === 'UMARead' 
                            ? 'bg-blue-100 text-blue-800' 
                            : grade.assignment_type === 'UMAVocab'
                            ? 'bg-purple-100 text-purple-800'
                            : grade.assignment_type === 'UMADebate'
                            ? 'bg-green-100 text-green-800'
                            : grade.assignment_type === 'UMAWrite'
                            ? 'bg-orange-100 text-orange-800'
                            : 'bg-teal-100 text-teal-800' // UMATest
                        }`}>
                          {grade.assignment_type}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="max-w-xs truncate" title={grade.work_title}>
                        {grade.work_title}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(grade.date_assigned)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(grade.test_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {grade.test_score !== null && grade.test_score !== undefined ? (
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getScoreColor(grade.test_score)}`}>
                          {grade.test_score.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {getStatusBadge(grade.status)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {grades.length > 0 && (
          <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage(currentPage + 1)}
                className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Showing page <span className="font-medium">{currentPage}</span>
                </p>
              </div>
              <div className="flex gap-2">
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="text-sm border-gray-300 rounded-md"
                >
                  <option value={10}>10 per page</option>
                  <option value={20}>20 per page</option>
                  <option value={50}>50 per page</option>
                  <option value={100}>100 per page</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}