'use client';

import { useState, useEffect } from 'react';
import { UserIcon, ArrowDownTrayIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import { api } from '@/lib/api';

interface Student {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
}

interface StudentInput {
  module: string;
  assignment: string;
  question: string;
  content: string;
  date: string;
}

interface StudentInputData {
  student: Student;
  input_count: number;
  inputs: StudentInput[];
}

export default function AllStudentInput() {
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<string>('');
  const [inputData, setInputData] = useState<StudentInputData | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Fetch all students
  useEffect(() => {
    const fetchStudents = async () => {
      try {
        const response = await api.get('/v1/teacher/students');
        setStudents(response.data);
      } catch (error) {
        console.error('Error fetching students:', error);
      }
    };

    fetchStudents();
  }, []);

  // Fetch student input data
  const fetchStudentInput = async () => {
    if (!selectedStudent) return;
    
    setLoading(true);
    try {
      const response = await api.get(`/v1/teacher/student-input/${selectedStudent}`);
      setInputData(response.data);
    } catch (error) {
      console.error('Error fetching student input:', error);
    } finally {
      setLoading(false);
    }
  };

  // Export data as plain text
  const exportData = () => {
    if (!inputData) return;
    
    setExporting(true);
    
    // Create plain text output
    let textContent = `STUDENT INPUT COMPILATION
========================================
Student: ${inputData.student.first_name} ${inputData.student.last_name}
Email: ${inputData.student.email}
Total Entries: ${inputData.input_count}
Generated: ${new Date().toLocaleString()}
========================================

`;

    if (inputData.inputs.length === 0) {
      textContent += "No written input found for this student.\n";
    } else {
      // Group inputs by module for better organization
      const groupedInputs: { [key: string]: StudentInput[] } = {};
      inputData.inputs.forEach(input => {
        if (!groupedInputs[input.module]) {
          groupedInputs[input.module] = [];
        }
        groupedInputs[input.module].push(input);
      });

      // Add each module's content
      Object.keys(groupedInputs).forEach(module => {
        textContent += `\n\n${module} RESPONSES\n`;
        textContent += '='.repeat(40) + '\n\n';
        
        groupedInputs[module].forEach((input, index) => {
          const date = new Date(input.date).toLocaleDateString();
          textContent += `Entry ${index + 1} - ${date}\n`;
          textContent += `Assignment: ${input.assignment}\n`;
          textContent += `Question/Prompt: ${input.question}\n`;
          textContent += '-'.repeat(40) + '\n';
          textContent += `${input.content}\n`;
          textContent += '\n' + '='.repeat(40) + '\n\n';
        });
      });
    }

    // Add footer note
    textContent += `

========================================
END OF STUDENT INPUT COMPILATION

Note: This document contains all written responses from the student
across all UMADex modules. No performance metrics or grades are included.
This compilation is intended for qualitative analysis of student writing.
========================================`;

    // Create blob and download
    const blob = new Blob([textContent], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `student_input_${inputData.student.last_name}_${inputData.student.first_name}_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    setExporting(false);
  };

  return (
    <div className="mt-8 pt-8 border-t border-gray-200">
      <h2 className="text-2xl font-bold text-gray-900 mb-2">All Student Input</h2>
      <p className="text-sm text-gray-600 mb-6">
        Download all written responses from a student across all modules for qualitative analysis.
        No grades or performance metrics included - just the student's writing.
      </p>
      
      {/* Student Selection */}
      <div className="mb-8">
        <label htmlFor="input-student-select" className="block text-sm font-medium text-gray-700 mb-2">
          Select a Student
        </label>
        <div className="flex gap-4">
          <select
            id="input-student-select"
            value={selectedStudent}
            onChange={(e) => setSelectedStudent(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">Choose a student...</option>
            {students.map((student) => (
              <option key={student.id} value={student.id}>
                {student.last_name}, {student.first_name} - {student.email}
              </option>
            ))}
          </select>
          <button
            onClick={fetchStudentInput}
            disabled={!selectedStudent || loading}
            className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Loading...' : 'Load Input'}
          </button>
        </div>
      </div>

      {/* Input Data Display */}
      {inputData && (
        <div className="space-y-6">
          {/* Student Info Card */}
          <div className="bg-gray-50 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <DocumentTextIcon className="h-12 w-12 text-gray-400 mr-4" />
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {inputData.student.first_name} {inputData.student.last_name}
                  </h3>
                  <p className="text-sm text-gray-600">{inputData.student.email}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    {inputData.input_count} total written responses found
                  </p>
                </div>
              </div>
              <button
                onClick={exportData}
                disabled={exporting || inputData.input_count === 0}
                className="flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
                {exporting ? 'Exporting...' : 'Download All Input'}
              </button>
            </div>
          </div>

          {/* Content Preview */}
          {inputData.input_count > 0 ? (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h4 className="font-semibold text-gray-900 mb-4">Content Summary</h4>
              
              {/* Show breakdown by module */}
              <div className="space-y-3">
                {Object.entries(
                  inputData.inputs.reduce((acc, input) => {
                    acc[input.module] = (acc[input.module] || 0) + 1;
                    return acc;
                  }, {} as { [key: string]: number })
                ).map(([module, count]) => (
                  <div key={module} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <span className="text-sm font-medium text-gray-700">{module}</span>
                    <span className="text-sm text-gray-500">{count} responses</span>
                  </div>
                ))}
              </div>

              {/* Sample of recent entries */}
              <div className="mt-6">
                <h5 className="text-sm font-medium text-gray-700 mb-3">Recent Entries (Preview)</h5>
                <div className="space-y-2">
                  {inputData.inputs.slice(0, 3).map((input, index) => (
                    <div key={index} className="bg-gray-50 rounded p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-gray-600">{input.module} - {input.assignment}</span>
                        <span className="text-xs text-gray-500">{new Date(input.date).toLocaleDateString()}</span>
                      </div>
                      <p className="text-xs text-gray-600 italic mb-1">"{input.question}"</p>
                      <p className="text-sm text-gray-700 line-clamp-2">{input.content}</p>
                    </div>
                  ))}
                </div>
                {inputData.input_count > 3 && (
                  <p className="text-xs text-gray-500 mt-3 text-center">
                    ... and {inputData.input_count - 3} more entries
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
              <div className="flex items-center">
                <DocumentTextIcon className="h-8 w-8 text-yellow-600 mr-3" />
                <div>
                  <h4 className="text-sm font-semibold text-gray-900">No Written Input Found</h4>
                  <p className="text-sm text-gray-600 mt-1">
                    This student hasn't submitted any written responses yet.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Export Instructions */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>About This Tool:</strong> This feature compiles all written responses from a student
              without any grades or performance metrics. The downloaded file contains only the student's
              writing organized by module and date. Use this for qualitative analysis of student writing
              patterns, vocabulary development, or argument construction skills.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}