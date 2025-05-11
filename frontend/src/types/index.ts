export interface UserProfile {
  id: string;
  username: string | null;
  full_name: string | null;
  role_name: string;
  email: string;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}