'use client'

import TeacherGuard from '@/components/TeacherGuard'
import TeacherLayout from '@/components/TeacherLayout'

/**
 * SECURITY LAYOUT: Teacher Route Protection
 * 
 * This layout provides authentication protection for ALL teacher routes.
 * It combines the TeacherGuard (security) with TeacherLayout (UI structure).
 * 
 * SECURITY ARCHITECTURE:
 * TeacherGuard → TeacherLayout → Page Content
 * 
 * SECURITY BENEFITS:
 * - Unified auth protection for entire teacher section
 * - Consistent navigation and UI for teachers
 * - Single point of failure/security control
 * 
 * IMPORTANT: Individual teacher pages should NOT include additional
 * TeacherGuard wrappers - they inherit protection from this layout.
 */

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <TeacherGuard>
      <TeacherLayout>{children}</TeacherLayout>
    </TeacherGuard>
  )
}