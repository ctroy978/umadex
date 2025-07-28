'use client'

import { useAuthSupabase } from '@/hooks/useAuthSupabase'
import Link from 'next/link'
import { 
  BookOpenIcon,
  ChatBubbleLeftRightIcon,
  LanguageIcon,
  PencilSquareIcon,
  AcademicCapIcon,
  DocumentCheckIcon,
  UserGroupIcon,
  UsersIcon,
  ChartBarIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline'

const modules = [
  {
    name: 'uMaRead',
    description: 'Create reading comprehension activities',
    icon: BookOpenIcon,
    href: '/teacher/uma-read',
    color: 'bg-blue-500',
  },
  {
    name: 'uMaDebate',
    description: 'Set up debate activities for students',
    icon: ChatBubbleLeftRightIcon,
    href: '/teacher/uma-debate',
    color: 'bg-green-500',
  },
  {
    name: 'uMaVocab',
    description: 'Build vocabulary exercises',
    icon: LanguageIcon,
    href: '/teacher/uma-vocab',
    color: 'bg-purple-500',
  },
  {
    name: 'uMaWrite',
    description: 'Create writing assignments',
    icon: PencilSquareIcon,
    href: '/teacher/uma-write',
    color: 'bg-orange-500',
  },
  {
    name: 'uMaLecture',
    description: 'Develop interactive lectures',
    icon: AcademicCapIcon,
    href: '/teacher/uma-lecture',
    color: 'bg-red-500',
  },
  {
    name: 'uMaTest',
    description: 'Create comprehensive tests from lectures',
    icon: DocumentCheckIcon,
    href: '/teacher/uma-test',
    color: 'bg-yellow-500',
  },
]

const utilities = [
  {
    name: 'Manage Classrooms',
    description: 'Create and organize your classrooms',
    icon: UserGroupIcon,
    href: '/teacher/classrooms',
    color: 'bg-indigo-500',
  },
  {
    name: 'Manage Students',
    description: 'View and manage student enrollments',
    icon: UsersIcon,
    href: '/teacher/students',
    color: 'bg-pink-500',
  },
  {
    name: 'View Reports',
    description: 'Track student progress and scores',
    icon: ChartBarIcon,
    href: '/teacher/reports',
    color: 'bg-teal-500',
  },
  {
    name: 'Settings',
    description: 'Configure your preferences',
    icon: Cog6ToothIcon,
    href: '/teacher/settings',
    color: 'bg-gray-500',
  },
]

export default function TeacherDashboard() {
  const { user } = useAuthSupabase()

  return (
    <div className="p-8">
      {/* Welcome Section */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.first_name}!
        </h1>
        <p className="mt-2 text-gray-600">
          Select a module to create engaging content for your students.
        </p>
      </div>

      {/* UMA Modules Section */}
      <div className="mb-12">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">UMA Modules</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((module) => (
            <Link
              key={module.name}
              href={module.href}
              className="group relative rounded-lg p-6 bg-white hover:shadow-lg transition-shadow duration-200 border border-gray-200"
            >
              <div>
                <span className={`
                  inline-flex p-3 rounded-lg
                  ${module.color} text-white
                  group-hover:scale-110 transition-transform duration-200
                `}>
                  <module.icon className="h-6 w-6" aria-hidden="true" />
                </span>
              </div>
              <div className="mt-4">
                <h3 className="text-lg font-medium text-gray-900 group-hover:text-primary-600">
                  {module.name}
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  {module.description}
                </p>
              </div>
              <span className="absolute top-6 right-6 text-gray-300 group-hover:text-gray-400">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </span>
            </Link>
          ))}
        </div>
      </div>

      {/* Utilities Section */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Utilities</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {utilities.map((utility) => (
            <Link
              key={utility.name}
              href={utility.href}
              className="group relative rounded-lg p-6 bg-white hover:shadow-lg transition-shadow duration-200 border border-gray-200"
            >
              <div>
                <span className={`
                  inline-flex p-3 rounded-lg
                  ${utility.color} text-white
                  group-hover:scale-110 transition-transform duration-200
                `}>
                  <utility.icon className="h-6 w-6" aria-hidden="true" />
                </span>
              </div>
              <div className="mt-4">
                <h3 className="text-base font-medium text-gray-900 group-hover:text-primary-600">
                  {utility.name}
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  {utility.description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}