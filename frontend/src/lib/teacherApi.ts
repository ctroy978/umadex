import api from './api';

export interface TeacherSettings {
  email: string;
  full_name: string;
  bypass_code_status: {
    has_code: boolean;
    last_updated: string | null;
  };
}

export interface BypassUsageItem {
  student_id: string;
  student_name: string;
  student_email: string;
  classroom_id: string;
  classroom_name: string;
  assignment_id: string;
  assignment_title: string;
  chunk_number: number;
  question_type: string;
  timestamp: string;
  success: boolean;
}

export interface MostBypassedAssignment {
  assignment_id: string;
  assignment_title: string;
  count: number;
}

export interface BypassUsageSummary {
  total_uses: number;
  unique_students: number;
  unique_assignments: number;
  success_rate: number;
  most_bypassed_assignments: MostBypassedAssignment[];
}

export interface BypassCodeReport {
  summary: BypassUsageSummary;
  recent_usage: BypassUsageItem[];
  usage_by_day: Array<{
    date: string;
    successful: number;
    failed: number;
  }>;
}

export const teacherApi = {
  // Settings
  async getSettings(): Promise<TeacherSettings> {
    const response = await api.get('/v1/teacher/settings');
    return response.data;
  },

  // Bypass code management
  async setBypassCode(code: string): Promise<{ message: string }> {
    const response = await api.put('/v1/teacher/settings/bypass-code', { code });
    return response.data;
  },

  async removeBypassCode(): Promise<{ message: string }> {
    const response = await api.delete('/v1/teacher/settings/bypass-code');
    return response.data;
  },

  async getBypassCodeStatus(): Promise<{ has_code: boolean; last_updated: string | null }> {
    const response = await api.get('/v1/teacher/settings/bypass-code/status');
    return response.data;
  },

  async generateOneTimeBypassCode(
    contextType: string = 'general',
    studentEmail?: string
  ): Promise<{
    bypass_code: string;
    expires_at: string;
    context_type: string;
    student_email?: string;
  }> {
    const response = await api.post('/v1/teacher/settings/one-time-bypass', {
      context_type: contextType,
      student_email: studentEmail
    });
    return response.data;
  },

  async getActiveOneTimeCodes(): Promise<Array<{
    id: string;
    bypass_code: string;
    context_type: string;
    student_email?: string;
    created_at: string;
    expires_at: string;
    used: boolean;
  }>> {
    const response = await api.get('/v1/teacher/settings/one-time-bypass/active');
    return response.data;
  },

  async revokeOneTimeCode(codeId: string): Promise<{ message: string }> {
    const response = await api.delete(`/v1/teacher/settings/one-time-bypass/${codeId}`);
    return response.data;
  },

  // Reports
  async getBypassCodeUsageReport(days: number = 30): Promise<BypassCodeReport> {
    const response = await api.get('/v1/teacher/reports/bypass-code-usage', {
      params: { days }
    });
    return response.data;
  },

  // Test Security - Bypass codes for locked tests
  async generateBypassCode(testAttemptId: string): Promise<{
    bypass_code: string;
    expires_at: string;
    test_attempt_id: string;
  }> {
    const response = await api.post(`/v1/teacher/tests/${testAttemptId}/generate-bypass`);
    return response.data;
  },

  async unlockTestWithBypass(testAttemptId: string, bypassCode: string): Promise<{
    success: boolean;
    message: string;
    test_attempt_id: string;
  }> {
    const formData = new FormData();
    formData.append('bypass_code', bypassCode);
    const response = await api.post(`/v1/teacher/tests/${testAttemptId}/unlock`, formData);
    return response.data;
  },

  async getClassroomSecurityIncidents(classroomId: string): Promise<{
    classroom_id: string;
    incidents: Array<{
      id: string;
      student_name: string;
      student_id: string;
      assignment_title: string;
      incident_type: string;
      incident_data: any;
      resulted_in_lock: boolean;
      created_at: string;
      test_locked: boolean;
      test_attempt_id: string;
    }>;
    total_incidents: number;
  }> {
    const response = await api.get(`/v1/teacher/classroom/${classroomId}/security-incidents`);
    return response.data;
  },

  async deleteSecurityIncident(classroomId: string, incidentId: string): Promise<{ message: string }> {
    const response = await api.delete(`/v1/teacher/classroom/${classroomId}/security-incidents/${incidentId}`);
    return response.data;
  }
};