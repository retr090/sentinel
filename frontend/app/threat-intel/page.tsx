'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function ThreatIntelRoot() {
  const router = useRouter()
  useEffect(() => { router.replace('/threat-intel/lookup') }, [router])
  return null
}
