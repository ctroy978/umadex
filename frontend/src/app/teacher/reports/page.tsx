'use client';

import { useState } from 'react';
import { ChartBarIcon, KeyIcon, UserGroupIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import BypassCodeUsageReport from '@/components/teacher/reports/BypassCodeUsageReport';
import Gradebook from '@/components/teacher/reports/Gradebook';
import StudentAnalysis from '@/components/teacher/reports/StudentAnalysis';
import AssignmentAnalytics from '@/components/teacher/reports/AssignmentAnalytics';

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
      name: 'Lecture Progress Tracking',
      icon: DocumentTextIcon,
      description: 'Monitor student progress through UMALecture content with visual difficulty badges'
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
              onClick={() => !(section as any).comingSoon && setActiveReport(section.id)}
              disabled={(section as any).comingSoon}
              className={`p-4 rounded-lg border-2 transition-all text-left ${
                activeReport === section.id
                  ? 'border-primary-500 bg-primary-50'
                  : (section as any).comingSoon
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
              {(section as any).comingSoon && (
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

        {activeReport === 'assignment-stats' && <AssignmentAnalytics />}
      </div>
    </div>
  );
}