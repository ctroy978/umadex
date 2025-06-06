import api from './api'
import type { 
  ClassroomTestSchedule,
  ClassroomTestScheduleCreate,
  TestAvailabilityStatus,
  ScheduleTemplate,
  OverrideCode,
  OverrideCodeCreate,
  ValidateOverrideRequest,
  ValidateOverrideResponse,
  StudentScheduleView,
  ScheduleStatusDashboard
} from '@/types/testSchedule'

export const testScheduleApi = {
  // Get schedule templates
  async getScheduleTemplates(): Promise<ScheduleTemplate[]> {
    const response = await api.get('/v1/test-schedule/templates')
    return response.data
  },

  // Get classroom schedule
  async getClassroomSchedule(classroomId: string): Promise<ClassroomTestSchedule | null> {
    try {
      const response = await api.get(`/v1/test-schedule/classrooms/${classroomId}`)
      return response.data
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  // Create or update schedule
  async createOrUpdateSchedule(
    classroomId: string, 
    data: ClassroomTestScheduleCreate
  ): Promise<ClassroomTestSchedule> {
    const response = await api.post(`/v1/test-schedule/classrooms/${classroomId}`, data)
    return response.data
  },

  // Toggle schedule active status
  async toggleSchedule(classroomId: string, isActive: boolean): Promise<void> {
    await api.put(`/v1/test-schedule/classrooms/${classroomId}/toggle`, { is_active: isActive })
  },

  // Delete schedule
  async deleteSchedule(classroomId: string): Promise<void> {
    await api.delete(`/v1/test-schedule/classrooms/${classroomId}`)
  },

  // Check test availability
  async checkAvailability(classroomId: string, checkTime?: Date): Promise<TestAvailabilityStatus> {
    const params = checkTime ? { check_time: checkTime.toISOString() } : {}
    const response = await api.get(`/v1/test-schedule/classrooms/${classroomId}/availability`, { params })
    return response.data
  },

  // Get next testing window
  async getNextWindow(classroomId: string): Promise<any> {
    const response = await api.get(`/v1/test-schedule/classrooms/${classroomId}/next-window`)
    return response.data
  },

  // Validate test access
  async validateTestAccess(classroomId: string, overrideCode?: string): Promise<any> {
    const response = await api.post(`/v1/test-schedule/classrooms/${classroomId}/validate-access`, {
      override_code: overrideCode
    })
    return response.data
  },

  // Get schedule status (teacher dashboard)
  async getScheduleStatus(classroomId: string): Promise<ScheduleStatusDashboard> {
    const response = await api.get(`/v1/test-schedule/classrooms/${classroomId}/status`)
    return response.data
  },

  // Generate override code
  async generateOverrideCode(data: OverrideCodeCreate): Promise<OverrideCode> {
    const response = await api.post('/v1/test-schedule/overrides/generate', data)
    return response.data
  },

  // Validate override code
  async validateOverrideCode(data: ValidateOverrideRequest): Promise<ValidateOverrideResponse> {
    const response = await api.post('/v1/test-schedule/overrides/validate', data)
    return response.data
  },

  // Get active overrides
  async getActiveOverrides(classroomId?: string): Promise<OverrideCode[]> {
    const params = classroomId ? { classroom_id: classroomId } : {}
    const response = await api.get('/v1/test-schedule/overrides/active', { params })
    return response.data
  },

  // Revoke override code
  async revokeOverride(overrideId: string): Promise<void> {
    await api.delete(`/v1/test-schedule/overrides/${overrideId}`)
  },

  // Get student test availability across all classrooms
  async getStudentAvailability(): Promise<StudentScheduleView[]> {
    const response = await api.get('/v1/test-schedule/student/availability')
    return response.data
  }
}