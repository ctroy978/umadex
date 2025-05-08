<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100 py-12 px-4">
    <div class="max-w-md w-full space-y-8 p-6 bg-white rounded-lg shadow-md">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          {{ otpSent ? 'Enter verification code' : 'Sign in to your account' }}
        </h2>
      </div>
      
      <!-- Error message -->
      <div v-if="errorMessage" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
        {{ errorMessage }}
      </div>
      
      <!-- OTP Request Form -->
      <div v-if="!otpSent">
        <form class="mt-8 space-y-6" @submit.prevent="sendOTP">
          <div>
            <label for="email" class="block text-sm font-medium text-gray-700">Email address</label>
            <input 
              v-model="email" 
              id="email" 
              name="email" 
              type="email" 
              autocomplete="email" 
              required 
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="Enter your email"
            >
          </div>
          
          <div>
            <button 
              type="submit" 
              :disabled="authStore.loading"
              class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {{ authStore.loading ? 'Sending...' : 'Send verification code' }}
            </button>
          </div>
        </form>
      </div>
      
      <!-- OTP Verification Form -->
      <div v-else>
        <form class="mt-8 space-y-6" @submit.prevent="verifyOTP">
          <div>
            <label for="otp" class="block text-sm font-medium text-gray-700">Verification code</label>
            <input 
              v-model="token" 
              id="otp" 
              name="otp" 
              type="text" 
              required 
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="Enter the code sent to your email"
            >
          </div>
          
          <div>
            <button 
              type="submit" 
              :disabled="authStore.loading"
              class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {{ authStore.loading ? 'Verifying...' : 'Verify code' }}
            </button>
          </div>
          
          <div class="text-sm text-center">
            <button 
              @click="otpSent = false" 
              class="font-medium text-indigo-600 hover:text-indigo-500"
            >
              Try a different email
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const token = ref('')
const otpSent = ref(false)
const errorMessage = ref('')

const sendOTP = async () => {
  errorMessage.value = ''
  const { success, error } = await authStore.signInWithOTP(email.value)
  
  if (success) {
    otpSent.value = true
  } else if (error) {
    errorMessage.value = error.message || 'Failed to send verification code'
  }
}

const verifyOTP = async () => {
  errorMessage.value = ''
  const { success, error } = await authStore.verifyOTP(email.value, token.value)
  
  if (success) {
    router.push('/')
  } else if (error) {
    errorMessage.value = error.message || 'Failed to verify code'
  }
}
</script>