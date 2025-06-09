export interface AdminUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  username: string;
  role: 'student' | 'teacher';
  is_admin: boolean;
  created_at: string;
  deleted_at?: string | null;
  deletion_reason?: string | null;
  classroom_count?: number;
  enrolled_classrooms?: number;
}

export interface AdminDashboard {
  total_users: number;
  total_students: number;
  total_teachers: number;
  total_admins: number;
  deleted_users: number;
  recent_registrations: AdminUser[];
  recent_admin_actions: AdminAction[];
}

export interface AdminAction {
  id: string;
  action_type: string;
  admin_email: string;
  created_at: string;
}

export interface UserImpactAnalysis {
  user_id: string;
  user_email: string;
  user_role: 'student' | 'teacher';
  is_admin: boolean;
  
  // Teacher impacts
  affected_classrooms?: number;
  affected_assignments?: number;
  affected_students?: number;
  classroom_names?: string[];
  
  // Student impacts
  enrolled_classrooms?: number;
  total_assignments?: number;
  test_attempts?: number;
  
  warnings?: string[];
}

export interface AuditLogEntry {
  id: string;
  admin_id: string;
  admin_email: string;
  action_type: string;
  target_id?: string;
  target_type?: string;
  action_data: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export type DeletionReason = 'graduation' | 'transfer' | 'disciplinary' | 'inactive' | 'other';