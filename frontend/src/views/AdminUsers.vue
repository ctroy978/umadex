<!-- frontend/src/views/AdminUsers.vue -->
<template>
    <div class="min-h-screen bg-gray-100">
      <header class="bg-white shadow">
        <div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold text-gray-900">User Management</h1>
        </div>
      </header>
      
      <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <!-- Error alert -->
        <div v-if="errorMessage" class="mb-4 bg-red-100 border-l-4 border-red-500 text-red-700 p-4" role="alert">
          <p>{{ errorMessage }}</p>
        </div>
        
        <!-- Success alert -->
        <div v-if="successMessage" class="mb-4 bg-green-100 border-l-4 border-green-500 text-green-700 p-4" role="alert">
          <p>{{ successMessage }}</p>
        </div>
        
        <!-- Loading state -->
        <div v-if="loading" class="flex justify-center py-12">
          <p class="text-gray-500">Loading users...</p>
        </div>
        
        <!-- Users table -->
        <div v-else class="bg-white shadow overflow-hidden sm:rounded-md">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="user in users" :key="user.id">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div>
                      <div class="text-sm font-medium text-gray-900">{{ user.email }}</div>
                      <div class="text-sm text-gray-500">{{ user.username || 'No username' }}</div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span 
                    :class="[
                      'px-2 inline-flex text-xs leading-5 font-semibold rounded-full',
                      user.role_name === 'ADMIN' ? 'bg-purple-100 text-purple-800' : 
                      user.role_name === 'TEACHER' ? 'bg-green-100 text-green-800' : 
                      'bg-blue-100 text-blue-800'
                    ]"
                  >
                    {{ user.role_name }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {{ new Date(user.created_at).toLocaleDateString() }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div class="flex justify-end space-x-2">
                    <button 
                      v-if="user.role_name !== 'TEACHER' && user.id !== authStore.user?.id"
                      @click="promoteUser(user.id, 'TEACHER')" 
                      class="text-indigo-600 hover:text-indigo-900"
                    >
                      Make Teacher
                    </button>
                    <button 
                      v-if="user.role_name !== 'ADMIN' && user.id !== authStore.user?.id"
                      @click="promoteUser(user.id, 'ADMIN')" 
                      class="text-purple-600 hover:text-purple-900"
                    >
                      Make Admin
                    </button>
                    <button 
                      v-if="user.role_name !== 'STUDENT' && user.id !== authStore.user?.id"
                      @click="promoteUser(user.id, 'STUDENT')" 
                      class="text-blue-600 hover:text-blue-900"
                    >
                      Make Student
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </main>
    </div>
  </template>
  
  <script setup lang="ts">
  import { ref, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { useAuthStore } from '../stores/auth'
  
  const router = useRouter()
  const authStore = useAuthStore()
  
  // UI state
  const loading = ref(false)
  const errorMessage = ref('')
  const successMessage = ref('')
  const users = ref([])
  
  // Load users on component mount
  onMounted(async () => {
    if (!authStore.isAdmin) {
      router.push('/')
      return
    }
    
    await loadUsers()
  })
  
  async function loadUsers() {
    loading.value = true
    errorMessage.value = ''
    
    try {
      const result = await authStore.fetchAllUsers()
      
      if (result.success) {
        users.value = result.data
      } else {
        errorMessage.value = result.error || 'Failed to load users'
      }
    } catch (err) {
      console.error('Error loading users:', err)
      errorMessage.value = 'An unexpected error occurred'
    } finally {
      loading.value = false
    }
  }
  
  async function promoteUser(userId, newRole) {
    loading.value = true
    errorMessage.value = ''
    successMessage.value = ''
    
    try {
      const result = await authStore.promoteUser(userId, newRole)
      
      if (result.success) {
        successMessage.value = `User successfully updated to ${newRole}`
        // Reload users to show updated role
        await loadUsers()
      } else {
        errorMessage.value = result.error || 'Failed to update user role'
      }
    } catch (err) {
      console.error('Error promoting user:', err)
      errorMessage.value = 'An unexpected error occurred'
    } finally {
      loading.value = false
    }
  }
  </script>