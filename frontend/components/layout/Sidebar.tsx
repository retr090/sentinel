'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard, Shield, Globe, Newspaper, MapPin,
  User, MessageSquare, Monitor, Bell, ChevronLeft, ChevronRight,
  LogOut, Settings
} from 'lucide-react'
import { useAuthStore } from '@/lib/store'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/threat-intel', label: 'Threat Intel', icon: Shield },
  { href: '/dark-web', label: 'Dark Web', icon: Globe },
  { href: '/news', label: 'News Intel', icon: Newspaper },
  { href: '/geoint', label: 'GEOINT', icon: MapPin },
  { href: '/profiles', label: 'Profiles', icon: User },
  { href: '/socmint', label: 'SOCMINT', icon: MessageSquare },
  { href: '/cyber-surface', label: 'Cyber Surface', icon: Monitor },
  { href: '/alerts', label: 'Alerts', icon: Bell },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()
  const { user, logout } = useAuthStore()
  const router = useRouter()

  const handleLogout = async () => {
    try { await api.post('/auth/logout') } catch {}
    logout()
    router.push('/login')
  }

  return (
    <aside
      className={cn(
        'flex flex-col bg-surface border-r border-border transition-all duration-300 min-h-screen sticky top-0',
        collapsed ? 'w-16' : 'w-56'
      )}
    >
      {/* Logo */}
      <div className={cn('flex items-center border-b border-border h-14', collapsed ? 'px-4 justify-center' : 'px-4 gap-3')}>
        <div className="w-8 h-8 bg-background border border-accent-green/40 rounded flex items-center justify-center flex-shrink-0">
          <Shield className="w-4 h-4 text-accent-green" />
        </div>
        {!collapsed && (
          <div>
            <span className="font-mono font-bold text-accent-green text-sm">SENTINEL</span>
            <div className="text-[10px] text-text-muted font-mono">OSINT PLATFORM</div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 space-y-0.5 px-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 px-2 py-2 rounded text-sm transition-all',
                collapsed ? 'justify-center' : '',
                active
                  ? 'bg-accent-green/10 text-accent-green border border-accent-green/20'
                  : 'text-text-muted hover:text-text-primary hover:bg-background/50'
              )}
              title={collapsed ? label : undefined}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span className="font-medium truncate">{label}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-border p-2 space-y-1">
        {!collapsed && user && (
          <div className="px-2 py-2 mb-1">
            <div className="text-xs text-text-primary font-medium truncate">{user.username}</div>
            <div className="text-[10px] text-text-muted uppercase font-mono">{user.role}</div>
          </div>
        )}

        <button
          onClick={handleLogout}
          className={cn(
            'flex items-center gap-3 px-2 py-2 rounded text-sm text-text-muted hover:text-danger hover:bg-danger/10 transition-all w-full',
            collapsed ? 'justify-center' : ''
          )}
          title={collapsed ? 'Logout' : undefined}
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {!collapsed && <span>Logout</span>}
        </button>

        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            'flex items-center gap-3 px-2 py-2 rounded text-sm text-text-muted hover:text-text-primary hover:bg-background/50 transition-all w-full',
            collapsed ? 'justify-center' : ''
          )}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}
