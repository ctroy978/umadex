import api from './api'

export interface VocabularyChainCreate {
  name: string
  description?: string
  total_review_words?: number
}

export interface VocabularyChainUpdate {
  name?: string
  description?: string
  total_review_words?: number
  is_active?: boolean
}

export interface VocabularyChainMemberAdd {
  vocabulary_list_ids: string[]
  position_start?: number
}

export interface VocabularyChainMemberReorder {
  vocabulary_list_id: string
  new_position: number
}

export interface VocabularyListSummary {
  id: string
  title: string
  grade_level: string
  subject_area: string
  status: string
  word_count: number
}

export interface VocabularyChainMember {
  id: string
  vocabulary_list_id: string
  position: number
  added_at: string
  vocabulary_list?: VocabularyListSummary
}

export interface VocabularyChain {
  id: string
  teacher_id: string
  name: string
  description?: string
  total_review_words: number
  is_active: boolean
  created_at: string
  updated_at: string
  member_count?: number
  members?: VocabularyChainMember[]
}

export interface VocabularyChainSummary {
  id: string
  name: string
  description?: string
  total_review_words: number
  is_active: boolean
  member_count: number
  created_at: string
  updated_at: string
}

export interface VocabularyChainList {
  items: VocabularyChainSummary[]
  total: number
  page: number
  per_page: number
  pages: number
}

export const vocabularyChainApi = {
  // Create a new chain
  async createChain(data: VocabularyChainCreate): Promise<VocabularyChain> {
    const response = await api.post('/v1/teacher/vocabulary/chains', data)
    return response.data
  },

  // Get paginated list of chains
  async listChains(params?: {
    page?: number
    per_page?: number
    include_inactive?: boolean
  }): Promise<VocabularyChainList> {
    const response = await api.get('/v1/teacher/vocabulary/chains', { params })
    return response.data
  },

  // Get a specific chain
  async getChain(chainId: string, includeMembers: boolean = true): Promise<VocabularyChain> {
    const response = await api.get(`/v1/teacher/vocabulary/chains/${chainId}`, {
      params: { include_members: includeMembers }
    })
    return response.data
  },

  // Update a chain
  async updateChain(chainId: string, data: VocabularyChainUpdate): Promise<VocabularyChain> {
    const response = await api.put(`/v1/teacher/vocabulary/chains/${chainId}`, data)
    return response.data
  },

  // Delete (deactivate) a chain
  async deleteChain(chainId: string): Promise<void> {
    await api.delete(`/v1/teacher/vocabulary/chains/${chainId}`)
  },

  // Add vocabulary lists to a chain
  async addMembers(chainId: string, data: VocabularyChainMemberAdd): Promise<VocabularyChainMember[]> {
    const response = await api.post(`/v1/teacher/vocabulary/chains/${chainId}/members`, data)
    return response.data
  },

  // Remove a vocabulary list from a chain
  async removeMember(chainId: string, vocabularyListId: string): Promise<void> {
    await api.delete(`/v1/teacher/vocabulary/chains/${chainId}/members/${vocabularyListId}`)
  },

  // Reorder a vocabulary list within a chain
  async reorderMember(chainId: string, data: VocabularyChainMemberReorder): Promise<void> {
    await api.put(`/v1/teacher/vocabulary/chains/${chainId}/members/reorder`, data)
  }
}