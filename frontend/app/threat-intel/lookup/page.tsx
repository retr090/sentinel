'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense } from 'react'

function Redirect() {
  const router = useRouter()
  const searchParams = useSearchParams()
  useEffect(() => {
    const v = searchParams.get('v')
    router.replace(v ? `/threat-intel?tab=lookup&v=${encodeURIComponent(v)}` : '/threat-intel?tab=lookup')
  }, [router, searchParams])
  return null
}

export default function LookupRedirect() {
  return <Suspense><Redirect /></Suspense>
}
