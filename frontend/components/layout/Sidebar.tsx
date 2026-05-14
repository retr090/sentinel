'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard, Shield, Globe, Newspaper, MapPin,
  User, MessageSquare, Monitor, Bell, ChevronLeft, ChevronRight,
  LogOut, X, Users, Search, Clock, Layers,
} from 'lucide-react'
import { useAuthStore } from '@/lib/store'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'

const THREAT_INTEL_ITEMS = [
  { href: '/threat-intel/lookup', label: 'IOC Lookup', icon: Search },
  { href: '/threat-intel/history', label: 'TI History', icon: Clock },
  { href: '/threat-intel/bulk', label: 'Bulk Lookup', icon: Layers },
]

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  // Threat Intel group rendered inline below
  { href: '/dark-web', label: 'Dark Web', icon: Globe },
  { href: '/news', label: 'News Intel', icon: Newspaper },
  { href: '/geoint', label: 'GEOINT', icon: MapPin },
  { href: '/profiles', label: 'Profiles', icon: User },
  { href: '/socmint', label: 'SOCMINT', icon: MessageSquare },
  { href: '/cyber-surface', label: 'Cyber Surface', icon: Monitor },
  { href: '/alerts', label: 'Alerts', icon: Bell },
]

export default function Sidebar({
  mobileOpen,
  onClose,
}: {
  mobileOpen?: boolean
  onClose?: () => void
}) {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()
  const { user, logout } = useAuthStore()
  const router = useRouter()

  const handleLogout = async () => {
    try { await api.post('/auth/logout') } catch {}
    logout()
    router.push('/login')
  }

  const tiActive = pathname.startsWith('/threat-intel')

  const linkClass = (active: boolean) => cn(
    'flex items-center gap-3 px-2 py-2 rounded text-sm transition-colors',
    'md:justify-center',
    collapsed ? 'lg:justify-center' : 'lg:justify-start',
    active
      ? 'bg-accent-green/10 text-accent-green border border-accent-green/20'
      : 'text-text-muted hover:text-text-primary hover:bg-background/50',
  )

  return (
    <aside
      className={cn(
        'flex flex-col bg-surface border-r border-border h-screen z-40',
        'fixed top-0 left-0',
        'transition-[width,transform] duration-300',
        mobileOpen ? 'translate-x-0' : '-translate-x-full',
        'md:sticky md:top-0 md:translate-x-0',
        'w-64 md:w-16',
        collapsed ? 'lg:w-16' : 'lg:w-56',
      )}
    >
      {/* Logo */}
      <div className="flex items-center border-b border-border h-14 px-3 gap-2 flex-shrink-0">
        <button
          className="md:hidden p-1 -ml-1 flex-shrink-0 text-text-muted hover:text-text-primary"
          onClick={onClose}
        >
          <X className="w-4 h-4" />
        </button>

        <div className={cn(
          'w-8 h-8 bg-background border border-accent-green/40 rounded flex items-center justify-center flex-shrink-0',
          'md:mx-auto',
          collapsed ? 'lg:mx-auto' : 'lg:mx-0',
        )}>
          <Shield className="w-4 h-4 text-accent-green" />
        </div>

        <div className={cn(
          'overflow-hidden',
          'md:hidden',
          collapsed ? 'lg:hidden' : 'lg:block',
        )}>
          <span className="font-mono font-bold text-accent-green text-sm block">SENTINEL</span>
          <div className="text-[10px] text-text-muted font-mono">OSINT PLATFORM</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-y-auto">
        {/* Dashboard */}
        {(() => {
          const { href, label, icon: Icon } = NAV_ITEMS[0]
          const active = pathname === href
          return (
            <Link key={href} href={href} onClick={onClose} className={linkClass(active)} title={label}>
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className={cn('font-medium truncate', 'md:hidden', collapsed ? 'lg:hidden' : 'lg:block')}>{label}</span>
            </Link>
          )
        })()}

        {/* ─── Threat Intelligence Group ─── */}
        <div className="space-y-0.5 pt-1">
          {/* Group label + collapsed icon */}
          <div className={cn(
            'flex items-center gap-2 px-2 py-1',
            'md:justify-center',
            collapsed ? 'lg:justify-center' : 'lg:justify-start',
          )}>
            {/* Icon (visible on tablet + desktop collapsed, acts as link) */}
            <Link
              href="/threat-intel/lookup"
              onClick={onClose}
              title="Threat Intel"
              className={cn(
                'hidden items-center justify-center w-4 h-4',
                'md:flex',
                collapsed ? 'lg:flex' : 'lg:hidden',
                tiActive ? 'text-accent-green' : 'text-text-muted hover:text-text-primary',
              )}
            >
              <Shield className="w-4 h-4 flex-shrink-0" />
            </Link>

            {/* Label (visible on mobile + desktop expanded) */}
            <span className={cn(
              'text-[9px] font-mono text-text-muted uppercase tracking-widest select-none',
              'md:hidden',
              collapsed ? 'lg:hidden' : 'lg:block',
            )}>
              Threat Intel
            </span>
          </div>

          {/* Sub-items — hidden on tablet, hidden when desktop collapsed */}
          {THREAT_INTEL_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                title={label}
                className={cn(
                  'flex items-center gap-3 px-2 py-1.5 rounded text-sm transition-colors',
                  'md:hidden',
                  collapsed ? 'lg:hidden' : 'lg:flex lg:justify-start',
                  active
                    ? 'bg-accent-green/10 text-accent-green border border-accent-green/20'
                    : 'text-text-muted hover:text-text-primary hover:bg-background/50',
                )}
              >
                <span className="w-4 flex-shrink-0" /> {/* indent */}
                <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="font-medium truncate text-xs">{label}</span>
              </Link>
            )
          })}
        </div>

        {/* Rest of nav items (dark-web onwards) */}
        {NAV_ITEMS.slice(1).map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              onClick={onClose}
              className={linkClass(active)}
              title={label}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className={cn('font-medium truncate', 'md:hidden', collapsed ? 'lg:hidden' : 'lg:block')}>
                {label}
              </span>
            </Link>
          )
        })}

        {/* Admin-only: User Management */}
        {user?.role === 'admin' && (() => {
          const active = pathname.startsWith('/admin/users')
          return (
            <Link
              href="/admin/users"
              onClick={onClose}
              className={cn(
                'flex items-center gap-3 px-2 py-2 rounded text-sm transition-colors mt-2 border-t border-border/50 pt-3',
                'md:justify-center',
                collapsed ? 'lg:justify-center' : 'lg:justify-start',
                active
                  ? 'bg-accent-green/10 text-accent-green border border-accent-green/20'
                  : 'text-text-muted hover:text-text-primary hover:bg-background/50',
              )}
              title="User Management"
            >
              <Users className="w-4 h-4 flex-shrink-0" />
              <span className={cn('font-medium truncate', 'md:hidden', collapsed ? 'lg:hidden' : 'lg:block')}>
                User Mgmt
              </span>
            </Link>
          )
        })()}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-border p-2 space-y-1 flex-shrink-0">
        {/* User info */}
        <div className={cn('px-2 py-1.5', 'md:hidden', collapsed ? 'lg:hidden' : 'lg:block')}>
          {user && (
            <>
              <div className="text-xs text-text-primary font-medium truncate">{user.username}</div>
              <div className="text-[10px] text-text-muted uppercase font-mono">{user.role}</div>
            </>
          )}
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className={cn(
            'flex items-center gap-3 px-2 py-2 rounded text-sm text-text-muted hover:text-danger hover:bg-danger/10 transition-colors w-full',
            'md:justify-center',
            collapsed ? 'lg:justify-center' : 'lg:justify-start',
          )}
          title="Logout"
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          <span className={cn('md:hidden', collapsed ? 'lg:hidden' : 'lg:block')}>Logout</span>
        </button>

        {/* Collapse toggle — desktop only */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            'hidden lg:flex items-center gap-3 px-2 py-2 rounded text-sm text-text-muted hover:text-text-primary hover:bg-background/50 transition-colors w-full',
            collapsed ? 'justify-center' : '',
          )}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}
