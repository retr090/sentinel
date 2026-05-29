'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function BulkRedirect() {
  const router = useRouter()
  useEffect(() => { router.replace('/threat-intel?tab=bulk') }, [router])
  return null
}
