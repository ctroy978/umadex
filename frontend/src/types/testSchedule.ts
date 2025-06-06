export type DayOfWeek = 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday'

export interface ScheduleWindow {
  id: string
  name: string
  days: DayOfWeek[]
  start_time: string // HH:MM format
  end_time: string   // HH:MM format
  color?: string
}

export interface ScheduleSettings {
  pre_test_buffer_minutes: number
  allow_weekend_testing: boolean
  emergency_override_enabled: boolean
}

export interface ScheduleData {
  windows: ScheduleWindow[]
  settings: ScheduleSettings
  templates_used: string[]
}

export interface ClassroomTestSchedule {
  id: string
  classroom_id: string
  created_by_teacher_id: string
  is_active: boolean
  timezone: string
  grace_period_minutes: number
  schedule_data: ScheduleData
  created_at: string
  updated_at: string
}

export interface ClassroomTestScheduleCreate {
  classroom_id: string
  is_active?: boolean
  timezone?: string
  grace_period_minutes?: number
  schedule_data: ScheduleData
}

export interface TestAvailabilityStatus {
  allowed: boolean
  next_window?: string | null
  current_window_end?: string | null
  schedule_active: boolean
  message: string
  time_until_next?: string | null
}

export interface OverrideCode {
  id: string
  classroom_id: string
  override_code: string
  reason: string
  expires_at: string
  max_uses: number
  current_uses: number
  created_at: string
}

export interface OverrideCodeCreate {
  classroom_id: string
  reason: string
  expires_in_hours: number
  max_uses: number
}

export interface ValidateOverrideRequest {
  override_code: string
  student_id: string
  test_attempt_id?: string
}

export interface ValidateOverrideResponse {
  valid: boolean
  override_id?: string
  message: string
}

export interface ScheduleTemplate {
  id: string
  name: string
  description: string
  schedule_data: ScheduleData
  category: string
}

export interface StudentScheduleView {
  classroom_id: string
  classroom_name: string
  schedule_active: boolean
  current_status: TestAvailabilityStatus
  upcoming_windows: Array<{
    start: string
    end: string
    days: DayOfWeek[]
  }>
}

export interface ScheduleStatusDashboard {
  testing_currently_allowed: boolean
  active_test_sessions: number
  next_window?: {
    start: string
  } | null
  schedule_overview: ScheduleWindow[]
  recent_overrides: OverrideCode[]
}