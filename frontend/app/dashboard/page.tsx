'use client'

import { useEffect, useState } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import TimelineChart from '@/components/ui/TimelineChart'
import AlertCard from '@/components/ui/AlertCard'
import SeverityBadge from '@/components/ui/SeverityBadge'
import { Shield, Globe, Newspaper, Monitor, User, MessageSquare, AlertCircle, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'

interface DashboardData {
  alerts: { by_severity: Record<string, number>; total_open: number }
  modules: {
    threat_intel: { iocs_24h: number }
    dark_web: { mentions_24h: number }
    news: { articles_24h: number }
    socmint: { posts_24h: number }
    cyber_surface: { assets: number; critical_vulns: number }
    profiles: { total: number }
  }
  news_timeline: { date: string; count: number }[]
  recent_alerts: any[]
  recent_geo: any[]
}

function StatCard({ title, value, subtitle, icon: Icon, color = 'accent-green', trend }: any) {
  return (
    <div className="sentinel-card flex items-start gap-3">
      <div className={cn('w-10 h-10 rounded flex items-center justify-center flex-shrink-0', `bg-${color}/10`)}>
        <Icon className={cn('w-5 h-5', `text-${color}`)} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-2xl font-bold font-mono text-text-primary">{value ?? '—'}</div>
        <div className="text-xs text-text-muted mt-0.5">{title}</div>
        {subtitle && <div className="text-[11px] text-text-muted/70 mt-0.5 font-mono">{subtitle}</div>}
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      const { data } = await api.get('/dashboard/summary')
      setData(data)
    } catch (err) {
      console.error('Dashboard fetch failed', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [])

  const SEV_COLORS: Record<string, string> = {
    CRITICAL: 'danger',
    HIGH: 'warning',
    MEDIUM: 'accent-blue',
    LOW: '[#10b981]',
    INFO: 'text-muted',
  }

  return (
    <AppLayout title="SENTINEL / Dashboard">
      <div className="space-y-6">
        {/* Alert severity bar */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as const).map((sev) => (
            <div key={sev} className={cn(
              'sentinel-card text-center cursor-pointer hover:bg-background/60 transition-colors',
              sev === 'CRITICAL' && data?.alerts.by_severity[sev] ? 'glow-red' : ''
            )}>
              <div className={cn('text-2xl font-bold font-mono', sev === 'CRITICAL' ? 'text-danger' : sev === 'HIGH' ? 'text-warning' : sev === 'MEDIUM' ? 'text-accent-blue' : 'text-text-muted')}>
                {data?.alerts.by_severity[sev] ?? 0}
              </div>
              <SeverityBadge severity={sev} className="mt-1" />
            </div>
          ))}
        </div>

        {/* Module stats */}
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <StatCard title="IOCs Last 24h" value={data?.modules.threat_intel.iocs_24h} icon={Shield} color="accent-blue" />
          <StatCard title="Dark Web Intel Mentions" value={data?.modules.dark_web.mentions_24h} subtitle="last 24h" icon={Globe} color="danger" />
          <StatCard title="News Articles" value={data?.modules.news.articles_24h} subtitle="last 24h" icon={Newspaper} color="accent-green" />
          <StatCard title="Social Posts" value={data?.modules.socmint.posts_24h} subtitle="last 24h" icon={MessageSquare} color="warning" />
          <StatCard title="Assets Monitored" value={data?.modules.cyber_surface.assets} icon={Monitor} color="accent-blue" />
          <StatCard title="Critical Vulns" value={data?.modules.cyber_surface.critical_vulns} subtitle="unresolved" icon={AlertCircle} color="danger" />
          <StatCard title="Intel Profiles" value={data?.modules.profiles.total} icon={User} color="accent-green" />
          <StatCard title="Open Alerts" value={data?.alerts.total_open} icon={Activity} color="warning" />
        </div>

        {/* Charts and feeds */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* News timeline */}
          <div className="lg:col-span-2 sentinel-card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Newspaper className="w-4 h-4 text-accent-green" />
                <h2 className="text-sm font-semibold">News Volume — 7 Days</h2>
              </div>
              <span className="text-[10px] font-mono text-text-muted">ARTICLES / DAY</span>
            </div>
            {data?.news_timeline && (
              <TimelineChart data={data.news_timeline} color="#00ff88" label="Articles" />
            )}
          </div>

          {/* Recent alerts */}
          <div className="sentinel-card">
            <div className="flex items-center gap-2 mb-4">
              <AlertCircle className="w-4 h-4 text-warning" />
              <h2 className="text-sm font-semibold">Recent Alerts</h2>
            </div>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {loading && <div className="text-text-muted text-sm text-center py-4 font-mono">LOADING...</div>}
              {!loading && (!data?.recent_alerts || data.recent_alerts.length === 0) && (
                <div className="text-text-muted text-sm text-center py-4 font-mono">NO ACTIVE ALERTS</div>
              )}
              {data?.recent_alerts?.map((alert: any) => (
                <AlertCard key={alert.id} alert={alert} compact />
              ))}
            </div>
          </div>
        </div>

        {/* Module health */}
        <div className="sentinel-card">
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-accent-green" />
            Module Status
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { name: 'Threat Intel', active: true },
              { name: 'Dark Web Intel', active: true },
              { name: 'News Intel', active: true },
              { name: 'GEOINT', active: true },
              { name: 'Profiles', active: true },
              { name: 'SOCMINT', active: true },
              { name: 'Cyber Surface', active: true },
              { name: 'Alerts', active: true },
            ].map((mod) => (
              <div key={mod.name} className="flex items-center gap-2 bg-background/50 rounded px-3 py-2">
                <div className={cn('w-2 h-2 rounded-full', mod.active ? 'bg-accent-green' : 'bg-danger')} />
                <span className="text-xs text-text-muted">{mod.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
