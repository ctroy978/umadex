'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { 
  AcademicCapIcon, 
  ChartBarIcon,
  ClockIcon,
  UserGroupIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline';
import { format } from 'date-fns';
import type { 
  LectureProgressBadge, 
  StudentLectureProgress, 
  LectureReport,
  LectureProgressResponse 
} from '@/types/lecture-progress';

// Badge component for difficulty levels
function DifficultyBadge({ level, completed, questionsCorrect, totalQuestions }: {
  level: string;
  completed: boolean;
  questionsCorrect?: number;
  totalQuestions?: number;
}) {
  const badgeConfig = {
    basic: { 
      emoji: '🟢', 
      label: 'Basic',
      bgColor: completed ? 'bg-green-100' : 'bg-gray-100',
      textColor: completed ? 'text-green-800' : 'text-gray-400'
    },
    intermediate: { 
      emoji: '🔵', 
      label: 'Intermediate',
      bgColor: completed ? 'bg-blue-100' : 'bg-gray-100',
      textColor: completed ? 'text-blue-800' : 'text-gray-400'
    },
    advanced: { 
      emoji: '🟣', 
      label: 'Advanced',
      bgColor: completed ? 'bg-purple-100' : 'bg-gray-100',
      textColor: completed ? 'text-purple-800' : 'text-gray-400'
    },
    expert: { 
      emoji: '⭐', 
      label: 'Expert',
      bgColor: completed ? 'bg-yellow-100' : 'bg-gray-100',
      textColor: completed ? 'text-yellow-800' : 'text-gray-400'
    }
  };

  const config = badgeConfig[level as keyof typeof badgeConfig];

  return (
    <div className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${config.bgColor} ${config.textColor}`}>
      <span className="mr-1">{completed ? config.emoji : '⚪'}</span>
      <span>{config.label}</span>
      {totalQuestions > 0 && (
        <span className="ml-1 text-xs">({questionsCorrect}/{totalQuestions})</span>
      )}
    </div>
  );
}

// Progress bar component
function ProgressBar({ value, className = "" }: { value: number; className?: string }) {
  return (
    <div className={`w-full bg-gray-200 rounded-full h-2 ${className}`}>
      <div 
        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
        style={{ width: `${value}%` }}
      />
    </div>
  );
}

interface ClassroomOption {
  id: string;
  name: string;
}

export default function AssignmentAnalytics() {
  const [selectedClassroom, setSelectedClassroom] = useState<string>('');
  const [classrooms, setClassrooms] = useState<ClassroomOption[]>([]);
  const [lectures, setLectures] = useState<LectureReport[]>([]);
  const [expandedLecture, setExpandedLecture] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'progress' | 'status'>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  useEffect(() => {
    fetchClassrooms();
  }, []);

  useEffect(() => {
    if (selectedClassroom) {
      fetchLectureProgress();
    }
  }, [selectedClassroom]);

  const fetchClassrooms = async () => {
    try {
      const response = await api.get('/v1/teacher/classrooms');
      setClassrooms(response.data);
      if (response.data.length > 0) {
        setSelectedClassroom(response.data[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch classrooms:', error);
    }
  };

  const fetchLectureProgress = async () => {
    setLoading(true);
    try {
      const response = await api.get<LectureProgressResponse>(`/v1/teacher/reports/lecture-progress/${selectedClassroom}`);
      setLectures(response.data.lectures || []);
    } catch (error) {
      console.error('Failed to fetch lecture progress:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleLecture = (lectureId: string) => {
    setExpandedLecture(expandedLecture === lectureId ? null : lectureId);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'in_progress': return 'text-yellow-600';
      default: return 'text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'in_progress': return '🟡';
      default: return '⚪';
    }
  };

  const sortStudents = (students: StudentLectureProgress[]) => {
    const sorted = [...students];
    sorted.sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'name':
          comparison = a.student_name.localeCompare(b.student_name);
          break;
        case 'progress':
          comparison = a.overall_progress - b.overall_progress;
          break;
        case 'status':
          const statusOrder = { completed: 3, in_progress: 2, not_started: 1 };
          comparison = statusOrder[a.status] - statusOrder[b.status];
          break;
      }
      
      return sortDirection === 'asc' ? comparison : -comparison;
    });
    
    return sorted;
  };

  const filterStudents = (students: StudentLectureProgress[]) => {
    if (!searchTerm) return students;
    
    return students.filter(student => 
      student.student_name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  if (!selectedClassroom && classrooms.length === 0) {
    return (
      <div className="text-center py-12">
        <UserGroupIcon className="h-12 w-12 mx-auto mb-4 text-gray-400" />
        <p className="text-gray-600">No classrooms found. Create a classroom first.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Classroom Selector */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <label className="text-sm font-medium text-gray-700">Classroom:</label>
          <select
            value={selectedClassroom}
            onChange={(e) => setSelectedClassroom(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {classrooms.map((classroom) => (
              <option key={classroom.id} value={classroom.id}>
                {classroom.name}
              </option>
            ))}
          </select>
        </div>

        {/* Search */}
        <div className="relative">
          <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search students..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading lecture progress...</p>
        </div>
      ) : lectures.length === 0 ? (
        <div className="text-center py-12">
          <AcademicCapIcon className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <p className="text-gray-600">No lectures assigned to this classroom yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {lectures.map((lecture) => (
            <div key={lecture.lecture_id} className="bg-white rounded-lg shadow-sm border border-gray-200">
              {/* Lecture Header */}
              <div 
                className="p-4 cursor-pointer hover:bg-gray-50"
                onClick={() => toggleLecture(lecture.lecture_id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {expandedLecture === lecture.lecture_id ? (
                      <ChevronUpIcon className="h-5 w-5 text-gray-400" />
                    ) : (
                      <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                    )}
                    <h3 className="font-medium text-gray-900">{lecture.lecture_title}</h3>
                  </div>
                  
                  <div className="flex items-center space-x-6 text-sm">
                    <div className="flex items-center space-x-2">
                      <UserGroupIcon className="h-4 w-4 text-gray-400" />
                      <span className="text-gray-600">
                        {lecture.summary.students_started}/{lecture.summary.total_students} started
                      </span>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <ChartBarIcon className="h-4 w-4 text-gray-400" />
                      <span className="text-gray-600">
                        {lecture.summary.average_progress.toFixed(0)}% avg progress
                      </span>
                    </div>

                    <div className="flex space-x-2">
                      {Object.entries(lecture.summary.badge_distribution).map(([level, count]) => (
                        count > 0 && (
                          <div key={level} className="text-xs">
                            <DifficultyBadge level={level} completed={true} />
                            <span className="ml-1 text-gray-600">×{count}</span>
                          </div>
                        )
                      ))}
                    </div>
                  </div>
                </div>
                
                <ProgressBar value={lecture.summary.average_progress} className="mt-3" />
              </div>

              {/* Expanded Student List */}
              {expandedLecture === lecture.lecture_id && (
                <div className="border-t border-gray-200">
                  {/* Sort Controls */}
                  <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                    <div className="flex items-center space-x-4 text-sm">
                      <span className="text-gray-600">Sort by:</span>
                      <button
                        onClick={() => setSortBy('name')}
                        className={`px-2 py-1 rounded ${sortBy === 'name' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'}`}
                      >
                        Name
                      </button>
                      <button
                        onClick={() => setSortBy('progress')}
                        className={`px-2 py-1 rounded ${sortBy === 'progress' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'}`}
                      >
                        Progress
                      </button>
                      <button
                        onClick={() => setSortBy('status')}
                        className={`px-2 py-1 rounded ${sortBy === 'status' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'}`}
                      >
                        Status
                      </button>
                    </div>
                    
                    <button
                      onClick={() => setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')}
                      className="text-gray-600 hover:text-gray-900"
                    >
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </button>
                  </div>

                  {/* Student List */}
                  <div className="max-h-96 overflow-y-auto">
                    {filterStudents(sortStudents(lecture.students)).map((student) => (
                      <div key={student.student_id} className="px-4 py-3 border-b border-gray-100 hover:bg-gray-50">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-2">
                              <span className="font-medium text-gray-900">{student.student_name}</span>
                              <span className={`text-sm ${getStatusColor(student.status)}`}>
                                {getStatusIcon(student.status)} {student.status.replace('_', ' ')}
                              </span>
                            </div>
                            
                            <div className="mt-1 text-sm text-gray-600">
                              {student.topics_completed}/{student.total_topics} topics • 
                              {student.last_activity_at && (
                                <span className="ml-2">
                                  <ClockIcon className="inline h-3 w-3 mr-1" />
                                  Last active: {format(new Date(student.last_activity_at), 'MMM d, h:mm a')}
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center space-x-4">
                            <div className="flex space-x-1">
                              {student.badges.map((badge) => (
                                <DifficultyBadge
                                  key={badge.level}
                                  level={badge.level}
                                  completed={badge.completed}
                                  questionsCorrect={badge.questions_correct}
                                  totalQuestions={badge.total_questions}
                                />
                              ))}
                            </div>
                            
                            <div className="w-32">
                              <div className="text-right text-sm text-gray-600 mb-1">
                                {student.overall_progress.toFixed(0)}%
                              </div>
                              <ProgressBar value={student.overall_progress} />
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}