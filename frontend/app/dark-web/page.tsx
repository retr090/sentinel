'use client'

import { useEffect, useState, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import SeverityBadge from '@/components/ui/SeverityBadge'
import { Globe, Plus, Search, RefreshCw, Eye } from 'lucide-react'
import { formatRelativeTime } from '@/lib/utils'

interface Keyword { id: number; keyword: string; category: string; severity: string; is_active: boolean; last_scanned: string }
interface Mention { id: number; keyword: string; source: string; source_url: string; title: string; snippet: string; severity: string; is_acknowledged: boolean; found_at: string }

export default function DarkWebPage() {
  const [keywords, setKeywords] = useState<Keyword[]>([])
  const [mentions, setMentions] = useState<Mention[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [newKeyword, setNewKeyword] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)
  const [breachQuery, setBreachQuery] = useState('')
  const [breachResult, setBreachResult] = useState<any>(null)
  const [searchingBreach, setSearchingBreach] = useState(false)
  const [tab, setTab] = useState<'mentions' | 'keywords' | 'breach'>('mentions')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [kwRes, mentionRes, statsRes] = await Promise.all([
        api.get('/dark-web/keywords'),
        api.get('/dark-web/mentions?page_size=30'),
        api.get('/dark-web/stats'),
      ])
      setKeywords(kwRes.data)
      setMentions(mentionRes.data.items)
      setStats(statsRes.data)
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const addKeyword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKeyword.trim()) return
    try {
      await api.post('/dark-web/keywords', { keyword: newKeyword, category: 'general', severity: 'HIGH' })
      setNewKeyword('')
      setShowAddForm(false)
      fetchData()
    } catch {}
  }

  const breachLookup = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!breachQuery.trim()) return
    setSearchingBreach(true)
    setBreachResult(null)
    try {
      const qtype = breachQuery.includes('@') ? 'email' : 'domain'
      const { data } = await api.post('/dark-web/breach-lookup', { query: breachQuery, query_type: qtype })
      setBreachResult(data)
    } catch {}
    setSearchingBreach(false)
  }

  const acknowledgeMention = async (id: number) => {
    try {
      await api.post(`/dark-web/mentions/${id}/acknowledge`)
      setMentions(m => m.map(x => x.id === id ? { ...x, is_acknowledged: true } : x))
    } catch {}
  }

  const triggerScan = async () => {
    try { await api.post('/dark-web/scan-now') } catch {}
  }

  return (
    <AppLayout title="SENTINEL / Dark Web Monitor">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              <Globe className="w-5 h-5 text-danger" /> Dark Web Monitor
            </h1>
            <p className="text-xs text-text-muted mt-0.5">Watchlist monitoring, breach lookup, and paste site scanning</p>
          </div>
          <div className="flex gap-2">
            <button onClick={triggerScan} className="flex items-center gap-1.5 text-xs border border-border rounded px-3 py-1.5 hover:bg-surface transition-colors text-text-muted hover:text-text-primary">
              <RefreshCw className="w-3.5 h-3.5" /> Scan Now
            </button>
            <button onClick={() => setShowAddForm(true)} className="flex items-center gap-1.5 text-xs bg-danger/20 border border-danger/30 rounded px-3 py-1.5 text-danger hover:bg-danger/30 transition-colors">
              <Plus className="w-3.5 h-3.5" /> Add Keyword
            </button>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Total Mentions', value: stats.total_mentions },
              { label: 'Mentions (24h)', value: stats.mentions_24h },
              { label: 'Active Keywords', value: stats.keywords_active },
              { label: 'Breach Results', value: stats.breaches_total },
            ].map((s) => (
              <div key={s.label} className="sentinel-card text-center">
                <div className="text-xl font-bold font-mono text-danger">{s.value}</div>
                <div className="text-xs text-text-muted mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Add keyword modal */}
        {showAddForm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="sentinel-card w-full max-w-md mx-4">
              <h3 className="text-sm font-semibold mb-3 font-mono">ADD WATCHLIST KEYWORD</h3>
              <div className="space-y-3">
                <input type="text" value={newKeyword} onChange={e => setNewKeyword(e.target.value)}
                  className="sentinel-input" placeholder="e.g. airforce.lk, SLAF, admin.af.mil" autoFocus
                  autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
                  data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other"
                  onKeyDown={(e) => { if (e.key === 'Enter') addKeyword({ preventDefault: () => {} } as React.FormEvent) }} />
                <div className="flex gap-2 justify-end">
                  <button type="button" onClick={() => setShowAddForm(false)} className="text-xs border border-border rounded px-3 py-1.5 hover:bg-surface">Cancel</button>
                  <button type="button" onClick={() => addKeyword({ preventDefault: () => {} } as React.FormEvent)} className="text-xs bg-danger text-white rounded px-3 py-1.5 hover:bg-danger/80">Add</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border">
          {(['mentions', 'keywords', 'breach'] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 text-xs font-mono uppercase tracking-wider transition-colors ${tab === t ? 'text-accent-green border-b-2 border-accent-green' : 'text-text-muted hover:text-text-primary'}`}>
              {t}
            </button>
          ))}
        </div>

        {/* Mentions */}
        {tab === 'mentions' && (
          <div className="sentinel-card">
            <h2 className="text-sm font-semibold mb-3 font-mono">DARK WEB MENTIONS ({mentions.length})</h2>
            <div className="overflow-x-auto">
            <table className="sentinel-table min-w-full">
              <thead><tr><th>Keyword</th><th>Source</th><th>Title</th><th>Severity</th><th>Found</th><th></th></tr></thead>
              <tbody>
                {loading && <tr><td colSpan={6} className="text-center py-8 text-text-muted font-mono text-xs">LOADING...</td></tr>}
                {!loading && mentions.length === 0 && <tr><td colSpan={6} className="text-center py-8 text-text-muted font-mono text-xs">NO MENTIONS FOUND</td></tr>}
                {mentions.map((m) => (
                  <tr key={m.id} className={m.is_acknowledged ? 'opacity-50' : ''}>
                    <td><code className="text-xs font-mono text-accent-green">{m.keyword}</code></td>
                    <td><span className="text-xs text-text-muted font-mono">{m.source}</span></td>
                    <td><span className="text-xs">{m.title || '—'}</span></td>
                    <td><SeverityBadge severity={m.severity} /></td>
                    <td><span className="text-xs text-text-muted font-mono">{formatRelativeTime(m.found_at)}</span></td>
                    <td>
                      {!m.is_acknowledged && (
                        <button onClick={() => acknowledgeMention(m.id)} className="text-xs text-text-muted hover:text-accent-blue font-mono">ACK</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        )}

        {/* Keywords */}
        {tab === 'keywords' && (
          <div className="sentinel-card">
            <h2 className="text-sm font-semibold mb-3 font-mono">WATCHLIST KEYWORDS</h2>
            <div className="overflow-x-auto">
            <table className="sentinel-table min-w-full">
              <thead><tr><th>Keyword</th><th>Category</th><th>Severity</th><th>Status</th><th>Last Scan</th></tr></thead>
              <tbody>
                {keywords.map((kw) => (
                  <tr key={kw.id}>
                    <td><code className="text-xs font-mono text-accent-green">{kw.keyword}</code></td>
                    <td><span className="text-xs text-text-muted">{kw.category}</span></td>
                    <td><SeverityBadge severity={kw.severity} /></td>
                    <td><span className={`text-xs font-mono ${kw.is_active ? 'text-accent-green' : 'text-danger'}`}>{kw.is_active ? 'ACTIVE' : 'INACTIVE'}</span></td>
                    <td><span className="text-xs text-text-muted font-mono">{formatRelativeTime(kw.last_scanned)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        )}

        {/* Breach lookup */}
        {tab === 'breach' && (
          <div className="sentinel-card">
            <h2 className="text-sm font-semibold mb-3 font-mono">BREACH DATABASE LOOKUP</h2>
            <div className="flex gap-2 mb-4">
              <input type="text" value={breachQuery} onChange={e => setBreachQuery(e.target.value)}
                className="sentinel-input font-mono" placeholder="email@domain.com or domain.com"
                autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
                data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other"
                onKeyDown={(e) => { if (e.key === 'Enter') breachLookup({ preventDefault: () => {} } as React.FormEvent) }} />
              <button type="button" onClick={() => breachLookup({ preventDefault: () => {} } as React.FormEvent)} disabled={searchingBreach}
                className="flex items-center gap-2 bg-danger text-white px-4 py-2 rounded text-sm hover:bg-danger/90 disabled:opacity-50">
                <Search className="w-4 h-4" /> {searchingBreach ? 'Searching...' : 'Lookup'}
              </button>
            </div>
            {breachResult && (
              <div className="mt-4 space-y-3">
                {breachResult.hibp && breachResult.hibp.length === 0 && (
                  <div className="text-accent-green text-sm font-mono p-3 bg-accent-green/10 rounded border border-accent-green/20">
                    ✓ Not found in known breaches (HIBP)
                  </div>
                )}
                {breachResult.hibp && breachResult.hibp.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-xs font-mono text-danger">FOUND IN {breachResult.hibp.length} BREACH(ES)</h3>
                    {breachResult.hibp.map((b: any, i: number) => (
                      <div key={i} className="bg-danger/10 border border-danger/20 rounded p-3">
                        <div className="font-mono text-sm text-danger font-bold">{b.Name}</div>
                        <div className="text-xs text-text-muted mt-1">Date: {b.BreachDate} · Domain: {b.Domain}</div>
                        <div className="text-xs text-text-muted mt-0.5">Exposed: {(b.DataClasses || []).join(', ')}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
