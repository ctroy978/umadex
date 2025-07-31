import { apiRequest } from './api';
import { AdminDashboard, AdminUser, UserImpactAnalysis } from '../types/admin';

export const adminApi = {
  // Dashboard
  getDashboard: async (): Promise<AdminDashboard> => {
    return apiRequest('/v1/admin/dashboard');
  },

  // User Management
  getUsers: async (params?: {
    page?: number;
    per_page?: number;
    search?: string;
    role?: string;
    include_deleted?: boolean;
  }): Promise<{
    users: AdminUser[];
    total: number;
    page: number;
    per_page: number;
    pages: number;
  }> => {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.per_page) queryParams.append('per_page', params.per_page.toString());
    if (params?.search) queryParams.append('search', params.search);
    if (params?.role) queryParams.append('role', params.role);
    if (params?.include_deleted) queryParams.append('include_deleted', params.include_deleted.toString());

    return apiRequest(`/v1/admin/users?${queryParams.toString()}`);
  },

  // User Impact Analysis
  getUserImpact: async (userId: string): Promise<UserImpactAnalysis> => {
    return apiRequest(`/v1/admin/users/${userId}/impact`);
  },

  // User Actions
  promoteUser: async (userId: string, data: {
    new_role?: 'student' | 'teacher';
    make_admin?: boolean;
    reason?: string;
  }) => {
    return apiRequest(`/v1/admin/users/${userId}/promote`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  softDeleteUser: async (userId: string, data: {
    reason: 'graduation' | 'transfer' | 'disciplinary' | 'inactive' | 'other';
    custom_reason?: string;
    notify_affected_teachers?: boolean;
  }) => {
    return apiRequest(`/v1/admin/users/${userId}/soft`, {
      method: 'DELETE',
      body: JSON.stringify(data),
    });
  },

  hardDeleteUser: async (userId: string, data: {
    reason: 'graduation' | 'transfer' | 'disciplinary' | 'inactive' | 'other';
    custom_reason?: string;
    confirmation_phrase: string;
  }) => {
    return apiRequest(`/v1/admin/users/${userId}/hard`, {
      method: 'DELETE',
      body: JSON.stringify(data),
    });
  },

  restoreUser: async (userId: string) => {
    return apiRequest(`/v1/admin/users/${userId}/restore`, {
      method: 'POST',
    });
  },

  updateUserName: async (userId: string, data: {
    first_name: string;
    last_name: string;
  }) => {
    return apiRequest(`/v1/admin/users/${userId}/name`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  // Audit Log
  getAuditLog: async (params?: {
    page?: number;
    per_page?: number;
    action_type?: string;
    admin_id?: string;
  }) => {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.per_page) queryParams.append('per_page', params.per_page.toString());
    if (params?.action_type) queryParams.append('action_type', params.action_type);
    if (params?.admin_id) queryParams.append('admin_id', params.admin_id);

    return apiRequest(`/v1/admin/audit-log?${queryParams.toString()}`);
  },
};