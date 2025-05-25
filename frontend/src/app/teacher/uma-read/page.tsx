'use client'

import ComingSoon from '@/components/ComingSoon'
import { BookOpenIcon, PlusIcon } from '@heroicons/react/24/outline'

export default function UmaReadPage() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">uMaRead</h1>
        <p className="text-gray-600">Create engaging reading comprehension activities for your students</p>
      </div>

      {/* Future Assignment List */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Reading Assignments</h2>
          <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50" disabled>
            <PlusIcon className="h-5 w-5 mr-2" />
            Create New Reading Assignment
          </button>
        </div>
        <div className="text-center py-12 text-gray-500">
          <BookOpenIcon className="h-12 w-12 mx-auto mb-3 text-gray-400" />
          <p>No reading assignments yet. Create your first one!</p>
        </div>
      </div>

      <ComingSoon 
        title="uMaRead Module"
        description="Soon you'll be able to create interactive reading comprehension activities with questions, vocabulary highlights, and progress tracking."
        icon={BookOpenIcon}
        color="bg-blue-500"
      />
    </div>
  )
}