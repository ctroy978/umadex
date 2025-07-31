'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { authSupabase } from '@/lib/authSupabase'
import { useAuthSupabase } from '@/hooks/useAuthSupabase'

interface LoginForm {
  email: string
  first_name?: string
  last_name?: string
}

interface VerifyForm {
  otp_code: string
}

export default function LoginPage() {
  const router = useRouter()
  const { setUser } = useAuthSupabase()
  const [step, setStep] = useState<'email' | 'otp'>('email')
  const [email, setEmail] = useState('')
  const [isNewUser, setIsNewUser] = useState(false)
  const [showRegistrationFields, setShowRegistrationFields] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { register: registerEmail, handleSubmit: handleSubmitEmail, formState: { errors: emailErrors }, watch: watchEmail } = useForm<LoginForm>()
  const { register: registerOTP, handleSubmit: handleSubmitOTP, formState: { errors: otpErrors } } = useForm<VerifyForm>()
  
  // Watch form fields for validation
  const watchedEmail = watchEmail('email')
  const watchedFirstName = watchEmail('first_name')
  const watchedLastName = watchEmail('last_name')
  
  // Determine if form is valid
  const isFormValid = () => {
    if (!watchedEmail) return false
    if (showRegistrationFields) {
      return !!(watchedFirstName?.trim() && watchedLastName?.trim())
    }
    return true
  }

  const onSubmitEmail = async (data: LoginForm) => {
    setLoading(true)
    setError('')
    
    try {
      // Always include role, defaulting to 'student'
      const requestData = {
        ...data,
        role: 'student' as const
      }
      const response = await authSupabase.requestOTP(requestData)
      setEmail(data.email)
      setIsNewUser(response.is_new_user)
      setStep('otp')
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to send OTP'
      setError(errorMessage)
      
      // If the error is about missing user data, show the registration fields
      if (errorMessage.includes('User data required')) {
        setShowRegistrationFields(true)
      }
    } finally {
      setLoading(false)
    }
  }

  const onSubmitOTP = async (data: VerifyForm) => {
    setLoading(true)
    setError('')
    
    try {
      const response = await authSupabase.verifyOTP({
        email,
        otp: data.otp_code
      })
      setUser(response.user)
      
      // Small delay to ensure token is saved
      setTimeout(() => {
        // Smart redirect based on user role and admin status
        if (response.user.is_admin) {
          router.push('/admin/dashboard')
        } else if (response.user.role === 'teacher') {
          router.push('/teacher/dashboard')
        } else {
          router.push('/dashboard')
        }
      }, 100)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid OTP')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">uMaDex</h1>
          <p className="mt-2 text-sm text-gray-600">
            Educational Assignment Management
          </p>
        </div>

        <div className="bg-white py-8 px-4 shadow-xl rounded-lg sm:px-10">
          {step === 'email' ? (
            <form onSubmit={handleSubmitEmail(onSubmitEmail)} className="space-y-6">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  Email address
                </label>
                <div className="mt-1">
                  <input
                    {...registerEmail('email', {
                      required: 'Email is required',
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: 'Invalid email address'
                      }
                    })}
                    type="email"
                    autoComplete="email"
                    className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                    placeholder="you@example.com"
                  />
                  {emailErrors.email && (
                    <p className="mt-1 text-sm text-red-600">{emailErrors.email.message}</p>
                  )}
                </div>
              </div>

              {showRegistrationFields && (
                <>
                  <div className="text-sm text-gray-600 mb-4">
                    <p>Looks like you're new! Please provide your name to complete registration.</p>
                  </div>
                  <div>
                    <label htmlFor="first_name" className="block text-sm font-medium text-gray-700">
                      First name <span className="text-red-500">*</span>
                    </label>
                    <div className="mt-1">
                      <input
                        {...registerEmail('first_name', {
                          required: showRegistrationFields ? 'First name is required' : false
                        })}
                        type="text"
                        autoComplete="given-name"
                        placeholder="Enter your first name"
                        className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                      />
                      {emailErrors.first_name && (
                        <p className="mt-1 text-sm text-red-600">{emailErrors.first_name.message}</p>
                      )}
                    </div>
                  </div>

                  <div>
                    <label htmlFor="last_name" className="block text-sm font-medium text-gray-700">
                      Last name <span className="text-red-500">*</span>
                    </label>
                    <div className="mt-1">
                      <input
                        {...registerEmail('last_name', {
                          required: showRegistrationFields ? 'Last name is required' : false
                        })}
                        type="text"
                        autoComplete="family-name"
                        placeholder="Enter your last name"
                        className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                      />
                      {emailErrors.last_name && (
                        <p className="mt-1 text-sm text-red-600">{emailErrors.last_name.message}</p>
                      )}
                    </div>
                  </div>
                </>
              )}

              {error && (
                <div className="rounded-md bg-red-50 p-4">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || !isFormValid()}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Sending...' : showRegistrationFields ? 'Register & Send Code' : 'Send Login Code'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleSubmitOTP(onSubmitOTP)} className="space-y-6">
              <div className="text-center">
                <p className="text-sm text-gray-600">
                  We sent a 6-digit code to {email}
                </p>
              </div>

              <div>
                <label htmlFor="otp_code" className="block text-sm font-medium text-gray-700">
                  Login Code
                </label>
                <div className="mt-1">
                  <input
                    {...registerOTP('otp_code', {
                      required: 'Login code is required',
                      pattern: {
                        value: /^[0-9]{6}$/,
                        message: 'Code must be 6 digits'
                      }
                    })}
                    type="text"
                    maxLength={6}
                    autoComplete="one-time-code"
                    className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 text-center text-lg tracking-widest"
                    placeholder="000000"
                  />
                  {otpErrors.otp_code && (
                    <p className="mt-1 text-sm text-red-600">{otpErrors.otp_code.message}</p>
                  )}
                </div>
              </div>

              {error && (
                <div className="rounded-md bg-red-50 p-4">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
              >
                {loading ? 'Verifying...' : 'Verify Code'}
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep('email')
                  setError('')
                }}
                className="w-full text-sm text-primary-600 hover:text-primary-500"
              >
                Use a different email
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}