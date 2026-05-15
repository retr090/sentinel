'use client'

import { useEffect, useState, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import ThreatScoreRing from '@/components/ui/ThreatScoreRing'
import { User, Plus, Search } from 'lucide-react'
import { formatRelativeTime } from '@/lib/utils'

interface Profile {
  id: number; name: string; profile_type: string; query_value: string;
  risk_score: number; summary?: string; last_updated: string; created_at: string
}

const TYPES = ['', 'person', 'org', 'domain', 'ip', 'email']

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [profileType, setProfileType] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', profile_type: 'domain', query_value: '' })

  const fetchProfiles = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '20' })
      if (search) params.set('search', search)
      if (profileType) params.set('profile_type', profileType)
      const [pRes, sRes] = await Promise.all([
        api.get(`/profiles?${params}`),
        api.get('/profiles/stats/summary'),
      ])
      setProfiles(pRes.data.items)
      setTotal(pRes.data.total)
      setStats(sRes.data)
    } catch {}
    setLoading(false)
  }, [page, search, profileType])

  useEffect(() => { fetchProfiles() }, [fetchProfiles])

  const createProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.post('/profiles', form)
      setShowCreate(false)
      setForm({ name: '', profile_type: 'domain', query_value: '' })
      fetchProfiles()
    } catch {}
  }

  return (
    <AppLayout title="SENTINEL / Entity Profiles">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              <User className="w-5 h-5 text-accent-green" /> Entity Profiling
            </h1>
            <p className="text-xs text-text-muted mt-0.5">OSINT profiles for persons, organisations, domains, and IPs</p>
          </div>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 text-xs bg-accent-green/20 border border-accent-green/30 rounded px-3 py-1.5 text-accent-green hover:bg-accent-green/30 transition-colors">
            <Plus className="w-3.5 h-3.5" /> New Profile
          </button>
        </div>

        {stats && (
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
            {[
              { label: 'Total', value: stats.total, color: 'text-text-primary' },
              { label: 'Person', value: stats.by_type?.person || 0, color: 'text-accent-green' },
              { label: 'Org', value: stats.by_type?.org || 0, color: 'text-accent-blue' },
              { label: 'Domain', value: stats.by_type?.domain || 0, color: 'text-warning' },
              { label: 'IP', value: stats.by_type?.ip || 0, color: 'text-danger' },
              { label: 'Email', value: stats.by_type?.email || 0, color: 'text-accent-green' },
            ].map((s) => (
              <div key={s.label} className="sentinel-card text-center py-2">
                <div className={`text-lg font-bold font-mono ${s.color}`}>{s.value}</div>
                <div className="text-[10px] text-text-muted mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Create modal */}
        {showCreate && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="sentinel-card w-full max-w-md mx-4">
              <h3 className="text-sm font-semibold mb-4 font-mono">CREATE INTEL PROFILE</h3>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-text-muted mb-1 block">Profile Name</label>
                  <input type="text" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    className="sentinel-input" placeholder="e.g. example.com, John Doe" required
                    autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
                    data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other"
                    onKeyDown={(e) => { if (e.key === 'Enter') createProfile({ preventDefault: () => {} } as React.FormEvent) }} />
                </div>
                <div>
                  <label className="text-xs text-text-muted mb-1 block">Type</label>
                  <select value={form.profile_type} onChange={e => setForm(f => ({ ...f, profile_type: e.target.value }))}
                    className="sentinel-input">
                    {['person', 'org', 'domain', 'ip', 'email'].map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-text-muted mb-1 block">Query Value</label>
                  <input type="text" value={form.query_value} onChange={e => setForm(f => ({ ...f, query_value: e.target.value }))}
                    className="sentinel-input font-mono" placeholder="Domain, IP, email, or name" required
                    autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
                    data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other"
                    onKeyDown={(e) => { if (e.key === 'Enter') createProfile({ preventDefault: () => {} } as React.FormEvent) }} />
                </div>
                <div className="flex gap-2 justify-end pt-2">
                  <button type="button" onClick={() => setShowCreate(false)} className="text-xs border border-border rounded px-3 py-1.5 hover:bg-surface">Cancel</button>
                  <button type="button" onClick={() => createProfile({ preventDefault: () => {} } as React.FormEvent)} className="text-xs bg-accent-green text-background rounded px-3 py-1.5 hover:bg-accent-green/90 font-bold">Create & Enrich</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
            <input type="text" value={search} onChange={e => { setSearch(e.target.value); setPage(1) }}
              placeholder="Search profiles..." className="sentinel-input pl-8 max-w-xs"
              autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
              data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other" />
          </div>
          <div className="flex gap-1">
            {TYPES.map((t) => (
              <button key={t} onClick={() => { setProfileType(t); setPage(1) }}
                className={`text-xs px-3 py-1.5 rounded font-mono border transition-colors ${profileType === t ? 'bg-accent-green/20 text-accent-green border-accent-green/30' : 'border-border text-text-muted hover:text-text-primary'}`}>
                {t || 'ALL'}
              </button>
            ))}
          </div>
        </div>

        {/* Profile grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {loading && <div className="col-span-full text-center py-8 text-text-muted font-mono text-xs">LOADING...</div>}
          {!loading && profiles.length === 0 && (
            <div className="col-span-full text-center py-8 text-text-muted font-mono text-xs">NO PROFILES FOUND — CREATE ONE TO START ENRICHMENT</div>
          )}
          {profiles.map((p) => (
            <div key={p.id} className="sentinel-card hover:bg-background/60 transition-colors cursor-pointer">
              <div className="flex items-start gap-3">
                <ThreatScoreRing score={Math.round(p.risk_score)} size={60} strokeWidth={5} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 bg-accent-green/10 text-accent-green rounded border border-accent-green/20 uppercase">
                      {p.profile_type}
                    </span>
                  </div>
                  <div className="font-medium text-sm text-text-primary truncate">{p.name}</div>
                  <code className="text-[10px] text-text-muted font-mono block truncate">{p.query_value}</code>
                  <div className="text-[10px] text-text-muted mt-1.5 font-mono">Updated {formatRelativeTime(p.last_updated)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {total > 20 && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-muted font-mono">Showing {(page-1)*20+1}–{Math.min(page*20,total)} of {total}</span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1} className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30">Prev</button>
              <button onClick={() => setPage(p => p+1)} disabled={page*20>=total} className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30">Next</button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
