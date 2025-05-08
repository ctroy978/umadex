// frontend/src/services/api.ts
import { supabase } from './supabase';

class ApiService {
  // Helper to get auth headers
  private async getHeaders() {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
  }

  async get(endpoint: string) {
    const headers = await this.getHeaders();
    const response = await fetch(`/api${endpoint}`, { headers });
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return response.json();
  }

  async post(endpoint: string, data: any) {
    const headers = await this.getHeaders();
    const response = await fetch(`/api${endpoint}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return response.json();
  }
}

export const apiService = new ApiService();