'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Bell, Search, Menu, LogOut, UserCog, KeyRound } from 'lucide-react'
import { useAuthStore, useAlertStore } from '@/lib/store'
import api from '@/lib/api'

function Avatar({ username, avatarUrl, size = 7 }: { username?: string; avatarUrl?: string; size?: number }) {
  const initials = username?.slice(0, 2).toUpperCase() ?? '??'
  const sz = `w-${size} h-${size}`
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt="avatar"
        className={`${sz} rounded-full object-cover border border-accent-green/30 flex-shrink-0`}
      />
    )
  }
  return (
    <div className={`${sz} bg-accent-green/20 border border-accent-green/30 rounded-full flex items-center justify-center flex-shrink-0`}>
      <span className="text-[10px] font-bold font-mono text-accent-green leading-none">{initials}</span>
    </div>
  )
}

export default function Topbar({
  title,
  onMenuClick,
}: {
  title?: string
  onMenuClick?: () => void
}) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const { user, logout } = useAuthStore()
  const { unreadCount } = useAlertStore()
  const router = useRouter()

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setSearching(true)
    try {
      const { data } = await api.get(`/dashboard/search?q=${encodeURIComponent(searchQuery)}`)
      if (data.redirect) router.push(data.redirect)
    } catch {}
    setSearching(false)
  }

  const handleLogout = async () => {
    try { await api.post('/auth/logout') } catch {}
    logout()
    router.push('/login')
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
      <div className="flex-1 max-w-lg">
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
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
            data-1p-ignore
            data-lpignore="true"
            data-bwignore="true"
            data-form-type="other"
            onKeyDown={(e) => { if (e.key === 'Enter') handleSearch({ preventDefault: () => {} } as React.FormEvent) }}
          />
        </div>
      </div>

      <div className="flex items-center gap-2 ml-auto flex-shrink-0">
        {/* Live indicator */}
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

        {/* User avatar + dropdown */}
        <div ref={dropdownRef} className="relative">
          <button
            onClick={() => setDropdownOpen((o) => !o)}
            className="flex items-center gap-2 rounded px-1.5 py-1 hover:bg-background/50 transition-colors"
          >
            <Avatar username={user?.username} avatarUrl={user?.avatar_url} size={7} />
            <div className="hidden md:block text-left">
              <div className="text-xs font-medium text-text-primary leading-tight">{user?.username}</div>
              <div className="text-[10px] text-text-muted font-mono uppercase leading-tight">{user?.role}</div>
            </div>
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-surface border border-border rounded-lg shadow-2xl z-50 py-1 animate-fade-in">
              <Link
                href="/settings/profile"
                onClick={() => setDropdownOpen(false)}
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-text-muted hover:text-text-primary hover:bg-background/50 transition-colors"
              >
                <UserCog className="w-4 h-4 flex-shrink-0" />
                Edit Profile
              </Link>
              <Link
                href="/settings/password"
                onClick={() => setDropdownOpen(false)}
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-text-muted hover:text-text-primary hover:bg-background/50 transition-colors"
              >
                <KeyRound className="w-4 h-4 flex-shrink-0" />
                Change Password
              </Link>
              <div className="border-t border-border my-1" />
              <button
                onClick={handleLogout}
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-danger hover:bg-danger/10 transition-colors w-full"
              >
                <LogOut className="w-4 h-4 flex-shrink-0" />
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
