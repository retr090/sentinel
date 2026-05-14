'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Bell, Search, User, Menu } from 'lucide-react'
import { useAuthStore, useAlertStore } from '@/lib/store'
import api from '@/lib/api'

export default function Topbar({
  title,
  onMenuClick,
}: {
  title?: string
  onMenuClick?: () => void
}) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const { user } = useAuthStore()
  const { unreadCount } = useAlertStore()
  const router = useRouter()

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setSearching(true)
    try {
      const { data } = await api.get(`/dashboard/search?q=${encodeURIComponent(searchQuery)}`)
      if (data.redirect) {
        router.push(data.redirect)
      }
    } catch {}
    setSearching(false)
  }

  return (
    <header className="h-14 border-b border-border bg-surface/80 backdrop-blur-sm flex items-center px-3 gap-3 sticky top-0 z-10 flex-shrink-0">
      {/* Hamburger — mobile only */}
      <button
        className="md:hidden p-1.5 rounded hover:bg-background/50 transition-colors flex-shrink-0"
        onClick={onMenuClick}
      >
        <Menu className="w-5 h-5 text-text-muted" />
      </button>

      {/* Title */}
      {title && (
        <div className="text-sm font-mono text-text-muted hidden lg:block flex-shrink-0">
          {title}
        </div>
      )}

      {/* Search */}
      <form onSubmit={handleSearch} className="flex-1 max-w-lg">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search IP, domain, hash..."
            className="w-full bg-background border border-border rounded pl-9 pr-4 py-1.5 text-sm font-mono
                       focus:outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/30
                       placeholder:text-text-muted/60"
          />
        </div>
      </form>

      <div className="flex items-center gap-2 ml-auto flex-shrink-0">
        {/* Live indicator — hidden on mobile */}
        <div className="hidden sm:flex items-center gap-1.5">
          <div className="live-dot" />
          <span className="text-[10px] font-mono text-text-muted hidden md:block">LIVE</span>
        </div>

        {/* Alerts bell */}
        <button
          onClick={() => router.push('/alerts')}
          className="relative p-1.5 rounded hover:bg-background/50 transition-colors"
        >
          <Bell className="w-4 h-4 text-text-muted" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-danger text-white text-[9px] font-bold rounded-full flex items-center justify-center">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>

        {/* User — hidden on mobile */}
        <div className="hidden sm:flex items-center gap-2 text-sm">
          <div className="w-7 h-7 bg-accent-green/20 border border-accent-green/30 rounded-full flex items-center justify-center">
            <User className="w-3.5 h-3.5 text-accent-green" />
          </div>
          <div className="hidden md:block">
            <div className="text-xs font-medium text-text-primary">{user?.username}</div>
            <div className="text-[10px] text-text-muted font-mono uppercase">{user?.role}</div>
          </div>
        </div>
      </div>
    </header>
  )
}
