import api from './api'
import type {
  VocabularyList,
  VocabularyListCreate,
  VocabularyListUpdate,
  VocabularyListPagination,
  VocabularyWord,
  VocabularyWordReviewRequest,
  VocabularyWordManualUpdate,
  VocabularyProgress,
  VocabularyStatus
} from '@/types/vocabulary'

export const vocabularyApi = {
  // Create a new vocabulary list
  async createList(data: VocabularyListCreate): Promise<VocabularyList> {
    const response = await api.post('/v1/teacher/vocabulary', data)
    return response.data
  },

  // Get paginated vocabulary lists
  async getLists(params?: {
    status?: VocabularyStatus
    search?: string
    page?: number
    per_page?: number
    include_archived?: boolean
  }): Promise<VocabularyListPagination> {
    const response = await api.get('/v1/teacher/vocabulary', { params })
    return response.data
  },

  // Get a specific vocabulary list with all words
  async getList(listId: string): Promise<VocabularyList> {
    const response = await api.get(`/v1/teacher/vocabulary/${listId}`)
    return response.data
  },

  // Update vocabulary list metadata
  async updateList(listId: string, data: VocabularyListUpdate): Promise<VocabularyList> {
    const response = await api.put(`/v1/teacher/vocabulary/${listId}`, data)
    return response.data
  },

  // Delete (archive) a vocabulary list
  async deleteList(listId: string): Promise<void> {
    await api.delete(`/v1/teacher/vocabulary/${listId}`)
  },

  // Restore an archived vocabulary list
  async restoreList(listId: string): Promise<{ message: string }> {
    const response = await api.post(`/v1/teacher/vocabulary/${listId}/restore`)
    return response.data
  },

  // Trigger AI generation for a list
  async generateAIDefinitions(listId: string): Promise<VocabularyList> {
    const response = await api.post(`/v1/teacher/vocabulary/${listId}/generate-ai`)
    return response.data
  },

  // Review a word (accept or reject)
  async reviewWord(wordId: string, data: VocabularyWordReviewRequest): Promise<void> {
    await api.post(`/v1/teacher/vocabulary/words/${wordId}/review`, data)
  },

  // Manually update a word
  async updateWordManually(wordId: string, data: VocabularyWordManualUpdate): Promise<VocabularyWord> {
    const response = await api.put(`/v1/teacher/vocabulary/words/${wordId}/manual`, data)
    return response.data
  },

  // Regenerate AI definition for a word
  async regenerateWordDefinition(wordId: string): Promise<VocabularyWord> {
    const response = await api.post(`/v1/teacher/vocabulary/words/${wordId}/regenerate`)
    return response.data
  },

  // Publish a vocabulary list
  async publishList(listId: string): Promise<VocabularyList> {
    const response = await api.post(`/v1/teacher/vocabulary/${listId}/publish`)
    return response.data
  },

  // Get review progress for a list
  async getProgress(listId: string): Promise<VocabularyProgress> {
    const response = await api.get(`/v1/teacher/vocabulary/${listId}/progress`)
    return response.data
  },

  // Batch accept all pending words
  async acceptAllPending(listId: string): Promise<void> {
    const list = await this.getList(listId)
    const pendingWords = list.words?.filter(
      word => word.review?.review_status === 'pending'
    ) || []
    
    // Accept each pending word
    await Promise.all(
      pendingWords.map(word =>
        this.reviewWord(word.id, { action: 'accept' })
      )
    )
  },

  // Export vocabulary list as HTML presentation
  async exportPresentation(listId: string): Promise<Blob> {
    const response = await api.get(`/v1/teacher/vocabulary/${listId}/export-presentation`, {
      responseType: 'blob'
    })
    return response.data
  },

  // Export vocabulary list as PDF
  async exportPDF(listId: string): Promise<VocabularyList> {
    const response = await api.get(`/v1/teacher/vocabulary/${listId}`)
    return response.data
  },

  // Test Configuration Methods
  async getTestConfig(listId: string): Promise<VocabularyTestConfig> {
    const response = await api.get(`/v1/teacher/vocabulary/${listId}/test/config`)
    return response.data
  },

  async updateTestConfig(listId: string, config: VocabularyTestConfig): Promise<VocabularyTestConfig> {
    const response = await api.put(`/v1/teacher/vocabulary/${listId}/test/config`, config)
    return response.data
  },

  async getTestAttempts(listId: string): Promise<any> {
    const response = await api.get(`/v1/teacher/vocabulary/${listId}/test/attempts`)
    return response.data
  }
}

// Test Configuration Types
export interface VocabularyTestConfig {
  chain_enabled: boolean
  chain_type?: 'weeks' | 'specific_lists' | 'named_chain'
  weeks_to_include: number
  questions_per_week: number
  chained_list_ids?: string[]
  chain_id?: string
  total_review_words?: number
  current_week_questions: number
  max_attempts: number
  time_limit_minutes: number
}