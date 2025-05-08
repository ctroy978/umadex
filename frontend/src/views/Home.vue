<template>
  <div class="min-h-screen bg-gray-100">
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 flex justify-between items-center">
        <h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
        <button 
          @click="logout" 
          class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
        >
          Log Out
        </button>
      </div>
    </header>
    
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <div class="border-4 border-dashed border-gray-200 rounded-lg h-96 p-4">
          <div v-if="authStore.loading" class="flex justify-center items-center h-full">
            <p class="text-gray-500">Loading...</p>
          </div>
          
          <div v-else-if="authStore.user" class="h-full flex flex-col">
            <h2 class="text-2xl font-semibold text-gray-800 mb-4">Welcome!</h2>
            
            <div class="bg-white p-4 rounded-lg shadow mb-4">
              <h3 class="font-medium text-gray-700 mb-2">Your Profile</h3>
              <p><span class="font-medium">Email:</span> {{ authStore.user.email }}</p>
              <p><span class="font-medium">ID:</span> {{ authStore.user.id }}</p>
            </div>
            
            <p class="text-gray-600">You're authenticated with Supabase using OTP!</p>
          </div>
          
          <div v-else class="flex justify-center items-center h-full">
            <div class="text-center">
              <p class="text-gray-500 mb-4">You're not authenticated. Redirecting to login...</p>
              <button 
                @click="router.push('/login')" 
                class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
              >
                Go to Login
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  // Initialize authentication
  await authStore.initialize()
  
  // If not authenticated, redirect to login
  if (!authStore.isAuthenticated) {
    router.push('/login')
  }
})

const logout = async () => {
  const { success } = await authStore.logout()
  if (success) {
    router.push('/login')
  }
}
</script>