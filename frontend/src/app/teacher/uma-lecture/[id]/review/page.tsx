'use client'

import { useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'

export default function ReviewPage() {
  const router = useRouter()
  const params = useParams()
  const lectureId = params.id as string

  useEffect(() => {
    // Redirect to edit page (review and edit are combined)
    router.replace(`/teacher/uma-lecture/${lectureId}/edit`)
  }, [lectureId, router])

  return null
}