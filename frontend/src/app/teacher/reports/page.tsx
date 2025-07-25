'use client';

import { useState } from 'react';
import { ChartBarIcon, KeyIcon, UserGroupIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import BypassCodeUsageReport from '@/components/teacher/reports/BypassCodeUsageReport';
import Gradebook from '@/components/teacher/reports/Gradebook';
import StudentAnalysis from '@/components/teacher/reports/StudentAnalysis';

type ReportType = 'overview' | 'bypass-code' | 'student-progress' | 'assignment-stats';

export default function ReportsPage() {
  const [activeReport, setActiveReport] = useState<ReportType>('overview');

  const reportSections = [
    {
      id: 'overview' as ReportType,
      name: 'Gradebook',
      icon: ChartBarIcon,
      description: 'View and analyze student test scores for UMARead assignments'
    },
    {
      id: 'student-progress' as ReportType,
      name: 'Student Analysis',
      icon: UserGroupIcon,
      description: 'Export comprehensive student performance data for AI analysis'
    },
    {
      id: 'assignment-stats' as ReportType,
      name: 'Assignment Analytics',
      icon: DocumentTextIcon,
      description: 'Detailed statistics on assignment completion and scores',
      comingSoon: true
    },
    {
      id: 'bypass-code' as ReportType,
      name: 'Bypass Code Usage',
      icon: KeyIcon,
      description: 'Monitor bypass code usage to identify problematic questions'
    }
  ];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Reports & Analytics</h1>
        <p className="text-gray-600">Monitor student progress and classroom performance</p>
      </div>

      {/* Report Navigation */}
      <div className="mb-8">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {reportSections.map((section) => (
            <button
              key={section.id}
              onClick={() => !section.comingSoon && setActiveReport(section.id)}
              disabled={section.comingSoon}
              className={`p-4 rounded-lg border-2 transition-all text-left ${
                activeReport === section.id
                  ? 'border-primary-500 bg-primary-50'
                  : section.comingSoon
                  ? 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'
                  : 'border-gray-200 hover:border-gray-300 bg-white'
              }`}
            >
              <div className="flex items-center mb-2">
                <section.icon className={`h-5 w-5 mr-2 ${
                  activeReport === section.id ? 'text-primary-600' : 'text-gray-500'
                }`} />
                <h3 className="font-medium text-gray-900">{section.name}</h3>
              </div>
              <p className="text-sm text-gray-600">{section.description}</p>
              {section.comingSoon && (
                <span className="inline-block mt-2 text-xs bg-gray-200 text-gray-600 px-2 py-1 rounded">
                  Coming Soon
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Report Content */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        {activeReport === 'overview' && <Gradebook />}

        {activeReport === 'bypass-code' && (
          <BypassCodeUsageReport />
        )}

        {activeReport === 'student-progress' && <StudentAnalysis />}

        {activeReport === 'assignment-stats' && (
          <div className="text-center py-12">
            <DocumentTextIcon className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Assignment Analytics</h2>
            <p className="text-gray-600">
              Assignment analytics are coming soon. You'll be able to see completion rates, average scores,
              time spent on assignments, and identify which questions are most challenging for students.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}