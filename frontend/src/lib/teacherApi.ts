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

  // Reports
  async getBypassCodeUsageReport(days: number = 30): Promise<BypassCodeReport> {
    const response = await api.get('/v1/teacher/reports/bypass-code-usage', {
      params: { days }
    });
    return response.data;
  }
};