'use client'

import StudentGuard from '@/components/StudentGuard'

/**
 * SECURITY LAYOUT: Student Route Protection
 * 
 * This layout provides authentication protection for ALL student routes.
 * It wraps every page under /student/* with the StudentGuard component.
 * 
 * SECURITY BENEFITS:
 * - Single point of auth control for all student functionality
 * - Prevents unauthorized access to any student page
 * - Consistent loading states and redirects
 * - Better performance than page-level guards
 * 
 * IMPORTANT: Do NOT add additional StudentGuard components to individual
 * student pages - they inherit protection from this layout.
 */

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  return (
    <StudentGuard>
      {children}
    </StudentGuard>
  )
}