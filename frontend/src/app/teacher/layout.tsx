'use client'

import TeacherGuard from '@/components/TeacherGuard'
import TeacherLayout from '@/components/TeacherLayout'

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <TeacherGuard>
      <TeacherLayout>{children}</TeacherLayout>
    </TeacherGuard>
  )
}