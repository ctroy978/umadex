// User profile interface for strong typing with Supabase
export interface UserProfile {
    id: string;
    username: string;
    full_name?: string;
    role_name: string;
    email: string;
    is_deleted: boolean;
    created_at: string;
    updated_at: string;
  }