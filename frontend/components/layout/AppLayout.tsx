'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function AppLayout({
  children,
  title,
}: {
  children: React.ReactNode
  title?: string
}) {
  const { isAuthenticated, user } = useAuthStore()
  const router = useRouter()
  const pathname = usePathname()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    if (!isAuthenticated && !localStorage.getItem('access_token')) {
      router.push('/login')
      return
    }
    // Redirect to password change if admin has flagged the account
    if (user?.force_password_change && pathname !== '/settings/password') {
      router.push('/settings/password')
    }
  }, [isAuthenticated, user, pathname, router])

  return (
    <div className="flex min-h-screen bg-background">
      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <Sidebar mobileOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        <Topbar title={title} onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 p-3 md:p-4 lg:p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
