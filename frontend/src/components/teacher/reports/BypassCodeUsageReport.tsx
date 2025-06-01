'use client';

import { useState, useEffect } from 'react';
import { teacherApi, BypassCodeReport } from '@/lib/teacherApi';
import { 
  CheckCircleIcon, 
  XCircleIcon, 
  ChartBarIcon,
  CalendarIcon,
  UserGroupIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';

export default function BypassCodeUsageReport() {
  const [report, setReport] = useState<BypassCodeReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadReport();
  }, [days]);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await teacherApi.getBypassCodeUsageReport(days);
      setReport(data);
    } catch (err) {
      setError('Failed to load bypass code usage report');
      console.error('Error loading report:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
        <p className="text-gray-500 mt-4">Loading report...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <XCircleIcon className="h-12 w-12 mx-auto mb-4 text-red-500" />
        <p className="text-red-600">{error}</p>
        <button onClick={loadReport} className="mt-4 text-primary-600 hover:text-primary-700">
          Try Again
        </button>
      </div>
    );
  }

  if (!report) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-gray-900">Bypass Code Usage Report</h2>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={60}>Last 60 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Uses</p>
              <p className="text-2xl font-semibold text-gray-900">{report.summary.total_uses}</p>
            </div>
            <ChartBarIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Success Rate</p>
              <p className="text-2xl font-semibold text-gray-900">{report.summary.success_rate}%</p>
            </div>
            <CheckCircleIcon className="h-8 w-8 text-green-500" />
          </div>
        </div>

        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Unique Students</p>
              <p className="text-2xl font-semibold text-gray-900">{report.summary.unique_students}</p>
            </div>
            <UserGroupIcon className="h-8 w-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Assignments Affected</p>
              <p className="text-2xl font-semibold text-gray-900">{report.summary.unique_assignments}</p>
            </div>
            <DocumentTextIcon className="h-8 w-8 text-purple-500" />
          </div>
        </div>
      </div>

      {/* Most Bypassed Assignments */}
      {report.summary.most_bypassed_assignments.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-lg font-medium text-gray-900 mb-3">Most Bypassed Assignments</h3>
          <div className="space-y-2">
            {report.summary.most_bypassed_assignments.map((assignment) => (
              <div key={assignment.assignment_id} className="flex justify-between items-center py-2 border-b last:border-b-0">
                <span className="text-sm text-gray-700">{assignment.assignment_title}</span>
                <span className="text-sm font-medium text-gray-900">{assignment.count} bypasses</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Daily Usage Chart */}
      {report.usage_by_day.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-lg font-medium text-gray-900 mb-3">Daily Usage</h3>
          <div className="space-y-2">
            {report.usage_by_day.slice(-7).map((day) => {
              const total = day.successful + day.failed;
              const successPercent = total > 0 ? (day.successful / total) * 100 : 0;
              
              return (
                <div key={day.date} className="flex items-center space-x-3">
                  <span className="text-sm text-gray-600 w-20">
                    {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                  <div className="flex-1">
                    <div className="flex h-6 bg-gray-200 rounded overflow-hidden">
                      {successPercent > 0 && (
                        <div 
                          className="bg-green-500" 
                          style={{ width: `${successPercent}%` }}
                          title={`${day.successful} successful`}
                        />
                      )}
                      {day.failed > 0 && (
                        <div 
                          className="bg-red-500" 
                          style={{ width: `${100 - successPercent}%` }}
                          title={`${day.failed} failed`}
                        />
                      )}
                    </div>
                  </div>
                  <span className="text-sm text-gray-600 w-16 text-right">{total} uses</span>
                </div>
              );
            })}
          </div>
          <div className="mt-4 flex items-center justify-center space-x-4 text-xs text-gray-600">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded mr-1"></div>
              Successful
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-red-500 rounded mr-1"></div>
              Failed
            </div>
          </div>
        </div>
      )}

      {/* Recent Usage */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Recent Usage</h3>
        </div>
        
        {report.recent_usage.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No bypass code usage in the selected time period
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Student
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Classroom
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Assignment
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Question
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {report.recent_usage.map((usage, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{usage.student_name}</div>
                      <div className="text-xs text-gray-500">{usage.student_email}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {usage.classroom_name}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {usage.assignment_title}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      <span className="capitalize">{usage.question_type}</span>
                      <span className="text-gray-500"> (Chunk {usage.chunk_number})</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(usage.timestamp)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {usage.success ? (
                        <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                          <CheckCircleIcon className="h-3 w-3 mr-1" />
                          Success
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">
                          <XCircleIcon className="h-3 w-3 mr-1" />
                          Failed
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info Note */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> This report shows bypass code usage across all your classrooms. 
          Failed attempts may indicate students forgetting the code or potential misuse. 
          Consider changing your bypass code if you see suspicious activity.
        </p>
      </div>
    </div>
  );
}