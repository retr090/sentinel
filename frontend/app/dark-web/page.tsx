'use client'
import { useState, useEffect, useRef } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'

// ── Stat Card ────────────────────────────────────────────────────────────────

const StatCard = ({
  label,
  value,
  sub,
  valueClass = 'text-accent-green',
}: {
  label: string
  value: number | string
  sub?: string
  valueClass?: string
}) => (
  <div className="bg-surface border border-border rounded-lg p-4">
    <div className="text-xs font-mono text-text-muted uppercase tracking-widest mb-1">{label}</div>
    <div className={`text-2xl font-bold font-mono ${valueClass}`}>{value}</div>
    {sub && <div className="text-xs text-text-muted mt-1">{sub}</div>}
  </div>
)

// ── Priority Badge ────────────────────────────────────────────────────────────

const PriorityBadge = ({ priority }: { priority: string }) => {
  const cls: Record<string, string> = {
    CRITICAL: 'bg-red-950 text-red-400 border-red-900',
    HIGH: 'bg-orange-950 text-orange-400 border-orange-900',
    MEDIUM: 'bg-yellow-950 text-yellow-400 border-yellow-900',
    LOW: 'bg-gray-900 text-gray-400 border-gray-700',
  }
  return (
    <span className={`text-xs font-mono px-2 py-0.5 rounded border ${cls[priority] || cls.LOW}`}>
      {priority}
    </span>
  )
}

// ── Category Badge ────────────────────────────────────────────────────────────

const CategoryBadge = ({ category }: { category: string }) => {
  const cls: Record<string, string> = {
    Military: 'text-red-400 border-red-900',
    Government: 'text-blue-400 border-blue-900',
    Finance: 'text-green-400 border-green-900',
    Infrastructure: 'text-orange-400 border-orange-900',
    Healthcare: 'text-pink-400 border-pink-900',
    Education: 'text-purple-400 border-purple-900',
    General: 'text-gray-400 border-gray-700',
  }
  return (
    <span className={`text-xs font-mono px-2 py-0.5 rounded border bg-background ${cls[category] || cls.General}`}>
      {category}
    </span>
  )
}

// ── Add Keyword Modal ─────────────────────────────────────────────────────────

const CATEGORIES = ['Military', 'Government', 'Finance', 'Infrastructure', 'Healthcare', 'Education', 'General', 'Custom']

const AddKeywordModal = ({
  onClose,
  onSave,
}: {
  onClose: () => void
  onSave: () => void
}) => {
  const [form, setForm] = useState({
    keyword: '',
    aliases: '',
    category: 'General',
    priority: 'MEDIUM',
    alert_mode: 'immediate',
    notes: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async () => {
    if (!form.keyword.trim()) { setError('Keyword is required'); return }
    setSaving(true)
    setError('')
    try {
      await api.post('/darkweb/keywords', {
        keyword: form.keyword.trim(),
        aliases: form.aliases
          ? form.aliases.split(',').map((a) => a.trim()).filter(Boolean)
          : [],
        category: form.category,
        priority: form.priority,
        alert_mode: form.alert_mode,
        notes: form.notes || null,
      })
      onSave()
      onClose()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div className="bg-surface border border-border rounded-lg w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-mono font-bold tracking-widest text-accent-green">ADD KEYWORD</h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">✕</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-mono text-text-muted uppercase tracking-widest block mb-1.5">
              Keyword *
            </label>
            <input
              type="text"
              value={form.keyword}
              onChange={(e) => setForm((p) => ({ ...p, keyword: e.target.value }))}
              placeholder="e.g. Sri Lanka Navy"
              autoComplete="off"
              data-1p-ignore
              data-lpignore="true"
              data-bwignore="true"
              className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
            />
          </div>

          <div>
            <label className="text-xs font-mono text-text-muted uppercase tracking-widest block mb-1.5">
              Aliases <span className="normal-case">(comma separated)</span>
            </label>
            <input
              type="text"
              value={form.aliases}
              onChange={(e) => setForm((p) => ({ ...p, aliases: e.target.value }))}
              placeholder="SLN, navy.lk, Sri Lanka Navy"
              autoComplete="off"
              data-1p-ignore
              data-lpignore="true"
              data-bwignore="true"
              className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-mono text-text-muted uppercase tracking-widest block mb-1.5">Category</label>
              <select
                value={form.category}
                onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}
                className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
              >
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-mono text-text-muted uppercase tracking-widest block mb-1.5">Priority</label>
              <select
                value={form.priority}
                onChange={(e) => setForm((p) => ({ ...p, priority: e.target.value }))}
                className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
              >
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-mono text-text-muted uppercase tracking-widest block mb-1.5">Alert Mode</label>
            <select
              value={form.alert_mode}
              onChange={(e) => setForm((p) => ({ ...p, alert_mode: e.target.value }))}
              className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
            >
              <option value="immediate">Immediate — alert as soon as found</option>
              <option value="daily">Daily — morning digest</option>
              <option value="weekly">Weekly — summary report</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-mono text-text-muted uppercase tracking-widest block mb-1.5">Notes</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
              placeholder="Why this keyword is being monitored..."
              rows={2}
              className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-text-primary font-mono resize-none focus:border-accent-green focus:outline-none"
            />
          </div>

          {error && <p className="text-xs text-red-400 font-mono">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 py-2 rounded bg-accent-green text-black font-mono text-sm font-bold hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {saving ? 'Saving...' : 'Add Keyword'}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 rounded border border-border text-text-muted font-mono text-sm hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Analyst Note Editor ───────────────────────────────────────────────────────

const AnalystNoteEditor = ({
  mentionId,
  existingNote,
  onSave,
}: {
  mentionId: string
  existingNote: string | null
  onSave: () => void
}) => {
  const [note, setNote] = useState(existingNote || '')
  const [saving, setSaving] = useState(false)

  const saveNote = async () => {
    setSaving(true)
    try {
      await api.patch(`/darkweb/mentions/${mentionId}`, { analyst_notes: note })
      onSave()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-2">
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Add analyst notes..."
        rows={3}
        className="w-full bg-surface border border-border rounded px-3 py-2 text-sm font-mono text-text-primary focus:border-accent-green focus:outline-none resize-none"
      />
      <button
        onClick={saveNote}
        disabled={saving}
        className="px-3 py-1.5 rounded bg-accent-green text-black font-mono text-xs font-bold disabled:opacity-50"
      >
        {saving ? 'Saving...' : 'Save Note'}
      </button>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type Tab = 'overview' | 'watchlist' | 'ransomware' | 'search' | 'scans' | 'forums'

export default function DarkWebMonitor() {
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [stats, setStats] = useState<any>(null)
  const [keywords, setKeywords] = useState<any[]>([])
  const [scans, setScans] = useState<any[]>([])
  const [ransomware, setRansomware] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [searchKw, setSearchKw] = useState('')
  const [filterCat, setFilterCat] = useState('')
  const [filterPri, setFilterPri] = useState('')
  const [seeding, setSeeding] = useState(false)
  const [scanning, setScanning] = useState<string | null>(null)
  const [rwDays, setRwDays] = useState(30)
  const [historicalRunning, setHistoricalRunning] = useState(false)
  const [historicalStatus, setHistoricalStatus] = useState('')
  // Search tab state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchSources, setSearchSources] = useState(['ahmia', 'darksearch', 'pastebin'])
  const [searchResults, setSearchResults] = useState<any>(null)
  const [searching, setSearching] = useState(false)

  // Forum Intel tab state
  const [forumData, setForumData] = useState<any>(null)
  const [forumFilter, setForumFilter] = useState({ severity: '', keyword: '', days: 30 })
  const [selectedMention, setSelectedMention] = useState<any>(null)
  const [forumScanning, setForumScanning] = useState(false)

  // Live countdown tick
  const [now, setNow] = useState(Date.now())
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    tickRef.current = setInterval(() => setNow(Date.now()), 30000)
    return () => { if (tickRef.current) clearInterval(tickRef.current) }
  }, [])

  useEffect(() => { loadAll() }, [])

  const loadAll = async () => {
    setLoading(true)
    await Promise.all([loadStats(), loadKeywords(), loadScans(), loadRansomware(), loadForumData()])
    setLoading(false)
  }

  const loadForumData = async (filter?: { severity: string; keyword: string; days: number }) => {
    const f = filter ?? forumFilter
    try {
      const params: Record<string, string> = { days: String(f.days), limit: '50' }
      if (f.severity) params.severity = f.severity
      if (f.keyword) params.keyword = f.keyword
      const r = await api.get('/darkweb/forum-mentions', { params })
      setForumData(r.data)
    } catch {}
  }

  const triggerForumScan = async () => {
    setForumScanning(true)
    try {
      await api.post('/darkweb/scan/trigger', null, { params: { scan_type: 'forums' } })
      // Poll once after 45s
      setTimeout(() => {
        loadForumData()
        loadStats()
        setForumScanning(false)
      }, 45000)
    } catch {
      setForumScanning(false)
    }
  }

  const loadStats = async () => {
    try {
      const r = await api.get('/darkweb/stats')
      setStats(r.data)
    } catch {}
  }

  const loadKeywords = async () => {
    try {
      const params: Record<string, string> = { limit: '100' }
      if (searchKw) params.search = searchKw
      if (filterCat) params.category = filterCat
      if (filterPri) params.priority = filterPri
      const r = await api.get('/darkweb/keywords', { params })
      setKeywords(r.data)
    } catch {}
  }

  const loadScans = async () => {
    try {
      const r = await api.get('/darkweb/scans', { params: { limit: 10 } })
      setScans(r.data)
    } catch {}
  }

  const loadRansomware = async (days = rwDays) => {
    try {
      const [victimsRes, statsRes] = await Promise.all([
        api.get('/darkweb/ransomware/victims', { params: { days: String(days), limit: '100' } }),
        api.get('/darkweb/ransomware/stats'),
      ])
      setRansomware({ victims: victimsRes.data, stats: statsRes.data })
    } catch {}
  }

  const handleSeed = async () => {
    setSeeding(true)
    try {
      await api.post('/darkweb/keywords/seed')
      await Promise.all([loadKeywords(), loadStats()])
    } finally {
      setSeeding(false)
    }
  }

  const handleDeleteKeyword = async (id: string) => {
    if (!confirm('Delete this keyword from watchlist?')) return
    try {
      await api.delete(`/darkweb/keywords/${id}`)
      await Promise.all([loadKeywords(), loadStats()])
    } catch {}
  }

  const handleToggleKeyword = async (id: string, is_active: boolean) => {
    try {
      await api.put(`/darkweb/keywords/${id}`, { is_active })
      await loadKeywords()
    } catch {}
  }

  const handleTriggerScan = async (scanType: string) => {
    setScanning(scanType)
    try {
      await api.post('/darkweb/scan/trigger', null, { params: { scan_type: scanType } })
      setTimeout(async () => {
        await Promise.all([loadRansomware(), loadStats(), loadScans()])
        setScanning(null)
      }, 15000)
    } catch {
      setScanning(null)
    }
  }

  const runHistoricalScan = async () => {
    if (historicalRunning) return
    setHistoricalRunning(true)
    setHistoricalStatus('Scanning all years (2021–2026) for Sri Lanka victims. This takes 1–2 minutes...')
    try {
      await api.post('/darkweb/scan/trigger', null, { params: { scan_type: 'historical' } })
      // Poll every 20s until we detect new victims or timeout at 4 minutes
      let elapsed = 0
      const poll = setInterval(async () => {
        elapsed += 20
        try {
          const r = await api.get('/darkweb/ransomware/stats')
          const total = r.data?.total_sl_victims ?? 0
          setHistoricalStatus(`Scan running... ${total} Sri Lanka victims found so far.`)
          await loadRansomware()
        } catch {}
        if (elapsed >= 240) {
          clearInterval(poll)
          setHistoricalRunning(false)
          setHistoricalStatus('')
          await Promise.all([loadRansomware(), loadStats(), loadScans()])
        }
      }, 20000)
    } catch {
      setHistoricalRunning(false)
      setHistoricalStatus('Failed to start historical scan.')
    }
  }

  const runSearch = async () => {
    if (!searchQuery.trim()) return
    setSearching(true)
    setSearchResults(null)
    try {
      const r = await api.post('/darkweb/search', {
        query: searchQuery,
        sources: searchSources,
      })
      setSearchResults(r.data)
    } catch {
      setSearchResults({ error: true, total_results: 0, results: [] })
    } finally {
      setSearching(false)
    }
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'watchlist', label: 'Watchlist' },
    { id: 'ransomware', label: 'Ransomware' },
    { id: 'search', label: 'Dark Web Search' },
    { id: 'forums', label: 'Forum Intel' },
    { id: 'scans', label: 'Scan History' },
  ]

  return (
    <AppLayout title="SENTINEL / Dark Web Monitor">
      <div className="space-y-6">

        {/* Page header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-mono font-bold tracking-widest text-accent-green">
              DARK WEB MONITOR
            </h1>
            <p className="text-xs text-text-muted mt-1">
              Continuous monitoring of dark web, paste sites, and breach databases for Sri Lanka intelligence
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded border border-border bg-surface">
              <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
              <span className="text-xs font-mono text-text-muted">5 sources active</span>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 rounded bg-accent-green text-black font-mono text-xs font-bold hover:opacity-90 transition-opacity"
            >
              + Add Keyword
            </button>
          </div>
        </div>

        {/* Tab navigation */}
        <div className="flex gap-1 border-b border-border">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-xs font-mono uppercase tracking-widest border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-accent-green text-accent-green'
                  : 'border-transparent text-text-muted hover:text-text-primary'
              }`}
            >
              {tab.label}
              {tab.id === 'ransomware' && (ransomware?.stats?.total_sl_victims ?? 0) > 0 && (
                <span className="ml-2 px-1.5 py-0.5 rounded text-xs bg-red-900 text-red-400">
                  {ransomware.stats.total_sl_victims} LK
                </span>
              )}
              {tab.id === 'forums' && (forumData?.stats?.unreviewed ?? 0) > 0 && (
                <span className="ml-2 px-1.5 py-0.5 rounded text-xs bg-orange-900 text-orange-400">
                  {forumData.stats.unreviewed}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* ── OVERVIEW ──────────────────────────────────────────────────────── */}
        {activeTab === 'overview' && (() => {
          const lastForumScan = scans.find(s => s.scan_type === 'forums')
          const nextForumMs = lastForumScan?.completed_at
            ? new Date(lastForumScan.completed_at).getTime() + 1800 * 1000
            : null
          const remainingSec = nextForumMs ? Math.floor((nextForumMs - now) / 1000) : null
          const nextLabel = remainingSec === null ? '—'
            : remainingSec <= 0 ? 'any moment'
            : remainingSec < 60 ? `${remainingSec}s`
            : `~${Math.floor(remainingSec / 60)}m`
          const lastRanLabel = lastForumScan?.completed_at
            ? (() => {
                const diff = Math.floor((now - new Date(lastForumScan.completed_at).getTime()) / 1000)
                if (diff < 60) return `${diff}s ago`
                if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
                return `${Math.floor(diff / 3600)}h ago`
              })()
            : 'never'

          return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Active Keywords" value={stats?.active_keywords ?? '—'} sub="being monitored" />
              <StatCard
                label="Unreviewed"
                value={stats?.unreviewed_mentions ?? '—'}
                sub="need analyst review"
                valueClass={(stats?.unreviewed_mentions ?? 0) > 0 ? 'text-warning' : 'text-accent-green'}
              />
              <StatCard
                label="Last 24 Hours"
                value={stats?.mentions_24h ?? '—'}
                sub="new mentions"
                valueClass={(stats?.mentions_24h ?? 0) > 0 ? 'text-yellow-400' : 'text-accent-green'}
              />
              <StatCard label="Last 7 Days" value={stats?.mentions_7d ?? '—'} sub="total mentions" />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <StatCard label="Critical Mentions" value={stats?.critical_mentions ?? '—'} sub="all time" valueClass="text-danger" />
              <StatCard label="High Mentions" value={stats?.high_mentions ?? '—'} sub="all time" valueClass="text-warning" />
              <div
                className="bg-surface border border-border rounded-lg p-4 cursor-pointer hover:border-accent-green/50 transition-colors"
                onClick={() => setActiveTab('forums')}
                title="Go to Forum Intelligence"
              >
                <div className="text-xs font-mono text-text-muted uppercase tracking-widest mb-1">Next Forum Scan</div>
                <div className={`text-2xl font-bold font-mono ${remainingSec !== null && remainingSec <= 300 ? 'text-yellow-400' : 'text-accent-green'}`}>
                  {nextLabel}
                </div>
                <div className="text-xs text-text-muted mt-1">last ran {lastRanLabel} · every 30 min</div>
              </div>
            </div>

            {/* Sources status */}
            <div className="bg-surface border border-border rounded-lg p-4">
              <h3 className="text-xs font-mono text-text-muted uppercase tracking-widest mb-4">Source Status</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {[
                  { id: 'ransomware_live', label: 'Ransomware.live', active: true },
                  { id: 'ahmia', label: 'Ahmia Search', active: true },
                  { id: 'darksearch', label: 'DarkSearch.io', active: true },
                  { id: 'pastebin', label: 'Paste Sites', active: true },
                  { id: 'rss_feeds', label: 'RSS Intel Feeds', active: true, rssPrefix: true },
                  { id: 'tor_search', label: 'Tor Gateway', active: false, coming: 'Phase 4' },
                  { id: 'telegram', label: 'Telegram', active: false, coming: 'Phase 5' },
                ].map((source) => {
                  const sourceCounts = stats?.sources_status ?? {}
                  const count = source.rssPrefix
                    ? Object.entries(sourceCounts)
                        .filter(([k]) => k.startsWith('rss_'))
                        .reduce((s, [, v]) => s + (v as number), 0)
                    : sourceCounts[source.id] ?? 0
                  const isActive = source.active && (count > 0 || !source.coming)
                  return (
                    <div key={source.id} className="flex items-center justify-between p-2 rounded bg-background border border-border">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-accent-green' : 'bg-gray-600'}`} />
                        <span className="text-xs font-mono text-text-muted">{source.label}</span>
                      </div>
                      <span className="text-xs font-mono text-text-muted">
                        {count > 0 ? `${count} hits` : source.coming ? source.coming : 'Active'}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Last scan + scan triggers */}
            <div className="bg-surface border border-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="text-xs font-mono text-text-muted uppercase tracking-widest">Last Scan</div>
                  <div className="text-sm text-text-primary font-mono mt-1">
                    {stats?.last_scan
                      ? new Date(stats.last_scan).toLocaleString()
                      : 'No scans yet'}
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {[
                  { type: 'ransomware', label: 'Ransomware.live' },
                  { type: 'rss', label: 'RSS Feeds' },
                  { type: 'paste', label: 'Paste Sites' },
                  { type: 'search', label: 'Dark Web Search' },
                ].map((s) => (
                  <button
                    key={s.type}
                    onClick={() => handleTriggerScan(s.type)}
                    disabled={scanning !== null}
                    className="px-3 py-1.5 rounded border border-border text-xs font-mono text-text-muted hover:text-accent-green hover:border-accent-green disabled:opacity-50 transition-colors"
                  >
                    {scanning === s.type ? '⟳ Running...' : `⟳ ${s.label}`}
                  </button>
                ))}
              </div>
            </div>
          </div>
          )
        })()}

        {/* ── WATCHLIST ─────────────────────────────────────────────────────── */}
        {activeTab === 'watchlist' && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <input
                type="text"
                value={searchKw}
                onChange={(e) => { setSearchKw(e.target.value); loadKeywords() }}
                placeholder="Search keywords..."
                autoComplete="off"
                data-1p-ignore
                data-lpignore="true"
                data-bwignore="true"
                className="flex-1 min-w-48 bg-surface border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
              />
              <select
                value={filterCat}
                onChange={(e) => { setFilterCat(e.target.value); loadKeywords() }}
                className="bg-surface border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
              >
                <option value="">All Categories</option>
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <select
                value={filterPri}
                onChange={(e) => { setFilterPri(e.target.value); loadKeywords() }}
                className="bg-surface border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
              >
                <option value="">All Priorities</option>
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
              <span className="text-xs text-text-muted font-mono">{keywords.length} keywords</span>
            </div>

            {keywords.length === 0 && !loading && (
              <div className="text-center py-12 border border-dashed border-border rounded-lg">
                <p className="text-text-muted font-mono text-sm mb-4">No keywords yet</p>
                <button
                  onClick={handleSeed}
                  disabled={seeding}
                  className="px-6 py-2 rounded bg-accent-green text-black font-mono text-sm font-bold hover:opacity-90 disabled:opacity-50"
                >
                  {seeding ? 'Loading...' : 'Load Default Sri Lanka Keywords'}
                </button>
              </div>
            )}

            {keywords.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      {['Keyword', 'Category', 'Priority', 'Alert Mode', 'Hits', 'Last Hit', 'Status', 'Actions'].map((h) => (
                        <th key={h} className="text-left text-xs font-mono text-text-muted uppercase tracking-widest pb-3 pr-4">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {keywords.map((kw) => (
                      <tr key={kw.id} className="border-b border-border hover:bg-surface transition-colors">
                        <td className="py-3 pr-4">
                          <div className="font-mono text-xs text-text-primary font-medium">{kw.keyword}</div>
                          {kw.aliases?.length > 0 && (
                            <div className="text-xs text-text-muted mt-0.5">{kw.aliases.slice(0, 3).join(', ')}</div>
                          )}
                        </td>
                        <td className="py-3 pr-4"><CategoryBadge category={kw.category} /></td>
                        <td className="py-3 pr-4"><PriorityBadge priority={kw.priority} /></td>
                        <td className="py-3 pr-4">
                          <span className="text-xs font-mono text-text-muted">{kw.alert_mode}</span>
                        </td>
                        <td className="py-3 pr-4">
                          <span className="text-xs font-mono text-accent-green">{kw.hit_count}</span>
                        </td>
                        <td className="py-3 pr-4">
                          <span className="text-xs font-mono text-text-muted">
                            {kw.last_hit ? new Date(kw.last_hit).toLocaleDateString() : 'Never'}
                          </span>
                        </td>
                        <td className="py-3 pr-4">
                          <button
                            onClick={() => handleToggleKeyword(kw.id, !kw.is_active)}
                            className={`text-xs font-mono px-2 py-0.5 rounded border transition-colors ${
                              kw.is_active
                                ? 'text-accent-green border-green-900 bg-green-950'
                                : 'text-gray-500 border-gray-800 bg-gray-900'
                            }`}
                          >
                            {kw.is_active ? 'Active' : 'Paused'}
                          </button>
                        </td>
                        <td className="py-3">
                          <button
                            onClick={() => handleDeleteKeyword(kw.id)}
                            className="text-xs font-mono text-text-muted hover:text-danger transition-colors"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ── RANSOMWARE ────────────────────────────────────────────────────── */}
        {activeTab === 'ransomware' && (
          <div className="space-y-6">

            {/* Stats */}
            {ransomware?.stats && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard
                    label="Total SL Victims"
                    value={ransomware.stats.total_sl_victims ?? 0}
                    sub="all time tracked"
                    valueClass={(ransomware.stats.total_sl_victims ?? 0) > 0 ? 'text-red-400' : 'text-accent-green'}
                  />
                  <StatCard
                    label="Last 7 Days"
                    value={ransomware.stats.victims_last_7d ?? 0}
                    sub="new SL victims"
                    valueClass={(ransomware.stats.victims_last_7d ?? 0) > 0 ? 'text-red-400' : 'text-accent-green'}
                  />
                  <StatCard
                    label="Last 30 Days"
                    value={ransomware.stats.victims_last_30d ?? 0}
                    sub="SL victims"
                  />
                  <StatCard
                    label="Critical / High"
                    value={ransomware.stats.critical_high_hits ?? 0}
                    sub="severity alerts"
                    valueClass={(ransomware.stats.critical_high_hits ?? 0) > 0 ? 'text-orange-400' : 'text-accent-green'}
                  />
                </div>

                {ransomware.stats.latest_victim && (
                  <div className="bg-red-950/30 border border-red-900 rounded-lg p-4 flex items-center gap-4">
                    <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse shrink-0" />
                    <div>
                      <div className="text-xs font-mono text-red-400 uppercase tracking-widest mb-0.5">
                        Latest Sri Lanka Hit
                      </div>
                      <div className="text-sm font-mono text-text-primary font-medium">
                        {ransomware.stats.latest_victim.org}{' '}
                        <span className="text-red-400">— {ransomware.stats.latest_victim.group}</span>
                      </div>
                      <div className="text-xs text-text-muted mt-0.5">
                        {new Date(ransomware.stats.latest_victim.date).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Controls */}
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={rwDays}
                onChange={(e) => setRwDays(Number(e.target.value))}
                className="bg-surface border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
              >
                <option value={1}>Last 24 hours</option>
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
              </select>

              <button
                onClick={() => loadRansomware(rwDays)}
                className="px-3 py-2 rounded border border-border text-xs font-mono text-text-muted hover:text-text-primary hover:border-accent-green transition-colors"
              >
                Apply Filter
              </button>

              <div className="ml-auto flex items-center gap-2">
                <button
                  onClick={runHistoricalScan}
                  disabled={historicalRunning || scanning !== null}
                  className="px-3 py-2 rounded border border-yellow-700 text-xs font-mono text-yellow-400 hover:bg-yellow-950 disabled:opacity-50 transition-all"
                  title="Scan ALL historical ransomware data (2021–2026) for Sri Lanka victims"
                >
                  {historicalRunning ? '⟳ Scanning History...' : '↓ Load Historical Data'}
                </button>
                <button
                  onClick={() => handleTriggerScan('ransomware')}
                  disabled={scanning !== null || historicalRunning}
                  className="px-4 py-2 rounded border border-accent-green text-xs font-mono text-accent-green hover:bg-accent-green hover:text-black disabled:opacity-50 transition-all"
                >
                  {scanning === 'ransomware' ? '⟳ Scanning...' : '⟳ Scan Now'}
                </button>
              </div>
            </div>

            {historicalStatus && (
              <div className="px-3 py-2 rounded border border-yellow-900 bg-yellow-950/30 text-xs font-mono text-yellow-400">
                {historicalStatus}
              </div>
            )}

            {/* Top groups */}
            {(ransomware?.stats?.top_groups?.length ?? 0) > 0 && (
              <div className="bg-surface border border-border rounded-lg p-4">
                <h3 className="text-xs font-mono text-text-muted uppercase tracking-widest mb-3">
                  Most Active Groups (Last 30 Days)
                </h3>
                <div className="flex flex-wrap gap-2">
                  {ransomware.stats.top_groups.map((g: any) => (
                    <div key={g.group} className="flex items-center gap-2 px-3 py-1.5 rounded border border-border bg-background">
                      <span className="text-xs font-mono text-red-400 font-bold">{g.group || 'Unknown'}</span>
                      <span className="text-xs font-mono text-text-muted">{g.count} victims</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Victims table */}
            <div className="bg-surface border border-border rounded-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                <h3 className="text-xs font-mono text-text-muted uppercase tracking-widest">
                  Sri Lanka Ransomware Victims
                </h3>
                <span className="text-xs font-mono text-text-muted">
                  {ransomware?.victims?.victims?.length ?? 0} results
                </span>
              </div>

              {!(ransomware?.victims?.victims?.length) ? (
                <div className="text-center py-12">
                  <p className="text-text-muted font-mono text-sm">No Sri Lanka ransomware victims found</p>
                  <p className="text-xs text-text-muted mt-2">
                    This is good news. Click &quot;Scan Now&quot; to check for latest hits.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-background">
                        {['', 'Organisation', 'Group', 'Matched By', 'Discovered', 'Link'].map((h) => (
                          <th key={h} className="text-left text-xs font-mono text-text-muted uppercase tracking-widest px-4 py-3">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {ransomware.victims.victims.map((v: any) => (
                        <tr
                          key={v.id}
                          className="border-b border-border transition-colors hover:bg-background bg-red-950/10"
                        >
                          <td className="px-4 py-3 w-6">
                            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" title="Sri Lanka related" />
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-xs font-mono font-medium text-text-primary">
                              {v.victim_org || 'Unknown'}
                            </div>
                            {v.victim_country && (
                              <div className="text-xs text-text-muted mt-0.5">{v.victim_country}</div>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-xs font-mono font-bold text-red-400">
                              {v.threat_actor || 'Unknown'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-xs font-mono text-accent-green">
                              {v.keyword_matched.replace('country:', '')}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-xs font-mono text-text-muted">
                              {new Date(v.discovered_at).toLocaleDateString()}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {v.source_url && (
                              <a
                                href={v.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs font-mono text-accent-blue hover:text-blue-300"
                              >
                                View ↗
                              </a>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

          </div>
        )}

        {/* ── DARK WEB SEARCH ───────────────────────────────────────────────── */}
        {activeTab === 'search' && (
          <div className="space-y-6">

            {/* Search bar */}
            <div className="bg-surface border border-border rounded-lg p-4">
              <div className="flex gap-3 mb-4">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') runSearch() }}
                  placeholder="Search the dark web..."
                  autoComplete="off"
                  data-1p-ignore
                  data-lpignore="true"
                  data-bwignore="true"
                  className="flex-1 bg-background border border-border rounded px-4 py-2.5 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
                />
                <button
                  onClick={runSearch}
                  disabled={searching || !searchQuery.trim()}
                  className="px-6 py-2.5 rounded bg-accent-green text-black font-mono text-sm font-bold hover:opacity-90 disabled:opacity-50 transition-opacity"
                >
                  {searching ? 'Searching...' : 'Search'}
                </button>
              </div>

              {/* Source toggles */}
              <div className="flex flex-wrap gap-2">
                <span className="text-xs font-mono text-text-muted self-center">Sources:</span>
                {[
                  { id: 'ahmia', label: 'Ahmia (Tor Search)' },
                  { id: 'darksearch', label: 'DarkSearch.io' },
                  { id: 'pastebin', label: 'Paste Sites' },
                ].map((s) => (
                  <button
                    key={s.id}
                    onClick={() =>
                      setSearchSources((prev) =>
                        prev.includes(s.id) ? prev.filter((x) => x !== s.id) : [...prev, s.id]
                      )
                    }
                    className={`text-xs font-mono px-3 py-1 rounded border transition-colors ${
                      searchSources.includes(s.id)
                        ? 'border-accent-green text-accent-green bg-background'
                        : 'border-border text-text-muted'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Loading skeletons */}
            {searching && (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-20 rounded-lg bg-surface border border-border animate-pulse" />
                ))}
              </div>
            )}

            {/* Results */}
            {searchResults && !searching && (
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <span className="text-xs font-mono text-text-muted">
                    {searchResults.total_results} results for &quot;{searchResults.query}&quot;
                  </span>
                  {(searchResults.saved_to_db ?? 0) > 0 && (
                    <span className="text-xs font-mono text-accent-green">
                      {searchResults.saved_to_db} new saved to database
                    </span>
                  )}
                </div>

                {/* Source status */}
                <div className="flex gap-2 flex-wrap">
                  {Object.entries(searchResults.source_status ?? {}).map(([src, status]: any) => (
                    <div key={src} className="flex items-center gap-1.5 px-2 py-1 rounded border border-border bg-surface">
                      <div className={`w-1.5 h-1.5 rounded-full ${status === 'ok' ? 'bg-accent-green' : 'bg-danger'}`} />
                      <span className="text-xs font-mono text-text-muted">{src}</span>
                    </div>
                  ))}
                </div>

                {searchResults.results?.length === 0 ? (
                  <div className="text-center py-12 border border-dashed border-border rounded-lg">
                    <p className="text-text-muted font-mono text-sm">
                      No results found for &quot;{searchResults.query}&quot;
                    </p>
                    <p className="text-xs text-text-muted mt-2">
                      Try a different query or enable more sources
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {searchResults.results?.map((r: any, i: number) => (
                      <div
                        key={i}
                        className="p-4 rounded-lg bg-surface border border-border hover:border-accent-green/30 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1.5">
                              <span className="text-xs font-mono px-2 py-0.5 rounded bg-background border border-border text-accent-green">
                                {r.source}
                              </span>
                              {r.keyword_matched && (
                                <span className="text-xs font-mono text-text-muted">
                                  &quot;{r.keyword_matched}&quot;
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-text-primary font-medium mb-1 truncate">
                              {r.title || 'No title'}
                            </p>
                            {r.snippet && (
                              <p className="text-xs text-text-muted leading-relaxed line-clamp-2">
                                {r.snippet}
                              </p>
                            )}
                          </div>
                          {r.url && (
                            <a
                              href={r.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="shrink-0 text-xs font-mono text-blue-400 hover:text-blue-300 transition-colors"
                            >
                              View ↗
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── FORUM INTEL ───────────────────────────────────────────────────── */}
        {activeTab === 'forums' && (
          <div className="space-y-4">

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <StatCard
                label="Total Forum Hits"
                value={forumData?.stats?.total ?? 0}
                sub="all time"
              />
              <StatCard
                label="Critical / High"
                value={forumData?.stats?.critical_high ?? 0}
                sub="need attention"
                valueClass={(forumData?.stats?.critical_high ?? 0) > 0 ? 'text-red-400' : 'text-accent-green'}
              />
              <StatCard
                label="Unreviewed"
                value={forumData?.stats?.unreviewed ?? 0}
                sub="pending review"
                valueClass={(forumData?.stats?.unreviewed ?? 0) > 0 ? 'text-orange-400' : 'text-accent-green'}
              />
            </div>

            {/* Controls */}
            <div className="flex flex-wrap items-center gap-3">
              <input
                type="text"
                value={forumFilter.keyword}
                onChange={(e) => setForumFilter((p) => ({ ...p, keyword: e.target.value }))}
                placeholder="Filter by keyword..."
                className="flex-1 min-w-48 bg-surface border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
              />
              <select
                value={forumFilter.severity}
                onChange={(e) => setForumFilter((p) => ({ ...p, severity: e.target.value }))}
                className="bg-surface border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
              >
                <option value="">All Severities</option>
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
              <select
                value={forumFilter.days}
                onChange={(e) => setForumFilter((p) => ({ ...p, days: parseInt(e.target.value) }))}
                className="bg-surface border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:border-accent-green focus:outline-none"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={365}>Last year</option>
              </select>
              <button
                onClick={() => loadForumData(forumFilter)}
                className="px-3 py-2 rounded border border-border text-xs font-mono text-text-muted hover:border-accent-green hover:text-accent-green transition-colors"
              >
                Apply
              </button>
              <a href="/dark-web/forums" className="px-3 py-2 rounded border border-border text-xs font-mono text-text-muted hover:border-accent-green hover:text-accent-green transition-colors">
                Manage Sources
              </a>
              <button
                onClick={triggerForumScan}
                disabled={forumScanning}
                className="ml-auto px-4 py-2 rounded border border-accent-green text-xs font-mono text-accent-green hover:bg-accent-green hover:text-black disabled:opacity-50 transition-all"
              >
                {forumScanning ? '⟳ Scanning...' : '⟳ Scan Forums Now'}
              </button>
            </div>

            {/* Results */}
            {!forumData?.mentions?.length ? (
              <div className="text-center py-16 border border-dashed border-border rounded-lg space-y-2">
                <p className="text-text-muted font-mono text-sm">No forum intelligence yet</p>
                <p className="text-xs text-text-muted">
                  {forumData === null
                    ? 'Loading...'
                    : 'Add forum credentials and run a scan to collect intelligence'}
                </p>
                <div className="flex items-center justify-center gap-4 pt-2">
                  <a href="/dark-web/forums" className="text-xs font-mono text-accent-green hover:underline">
                    Configure credentials →
                  </a>
                  <button
                    onClick={triggerForumScan}
                    disabled={forumScanning}
                    className="text-xs font-mono text-accent-green hover:underline disabled:opacity-50"
                  >
                    {forumScanning ? 'Scanning...' : 'Scan now →'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {forumData.mentions.map((m: any) => {
                  const sevCls =
                    m.severity === 'CRITICAL' ? 'border-red-900 bg-red-950/10' :
                    m.severity === 'HIGH'     ? 'border-orange-900 bg-orange-950/10' :
                    m.severity === 'MEDIUM'   ? 'border-yellow-900/50' :
                    'border-border'
                  const badgeCls =
                    m.severity === 'CRITICAL' ? 'bg-red-950 text-red-400 border-red-900' :
                    m.severity === 'HIGH'     ? 'bg-orange-950 text-orange-400 border-orange-900' :
                    m.severity === 'MEDIUM'   ? 'bg-yellow-950 text-yellow-400 border-yellow-900' :
                    'bg-gray-900 text-gray-400 border-gray-700'

                  return (
                    <div
                      key={m.id}
                      onClick={() => setSelectedMention(m)}
                      className={`p-4 rounded-lg border bg-surface cursor-pointer hover:brightness-110 transition-all ${sevCls}`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center flex-wrap gap-2 mb-2">
                            <span className={`text-xs font-mono px-2 py-0.5 rounded border shrink-0 ${badgeCls}`}>
                              {m.severity}
                            </span>
                            <span className="text-xs font-mono px-2 py-0.5 rounded border bg-background border-border text-accent-green shrink-0">
                              {m.source.replace(/_/g, '.').toUpperCase()}
                            </span>
                            <span className="text-xs font-mono text-text-muted">
                              matched: &ldquo;{m.keyword_matched}&rdquo;
                            </span>
                            {!m.is_reviewed && (
                              <span className="text-xs font-mono text-orange-400 ml-auto shrink-0">● New</span>
                            )}
                          </div>
                          <p className="text-sm font-mono font-medium text-text-primary mb-1 truncate">
                            {m.title || '(no title)'}
                          </p>
                          {m.snippet && (
                            <p className="text-xs text-text-muted leading-relaxed line-clamp-2">{m.snippet}</p>
                          )}
                          {m.threat_actor && (
                            <p className="text-xs font-mono text-text-muted mt-1">
                              Posted by: <span className="text-red-400">{m.threat_actor}</span>
                            </p>
                          )}
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="text-xs font-mono text-text-muted mb-2">
                            {new Date(m.discovered_at).toLocaleString()}
                          </div>
                          {m.source_url && (
                            <a
                              href={m.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="text-xs font-mono text-blue-400 hover:text-blue-300"
                            >
                              View Post ↗
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Detail panel */}
            {selectedMention && (
              <div
                className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
                onClick={() => setSelectedMention(null)}
              >
                <div
                  className="bg-surface border border-border rounded-lg w-full max-w-2xl max-h-[80vh] overflow-y-auto p-6"
                  onClick={(e) => e.stopPropagation()}
                >
                  {/* Detail header */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
                        selectedMention.severity === 'CRITICAL' ? 'bg-red-950 text-red-400 border-red-900' :
                        selectedMention.severity === 'HIGH'     ? 'bg-orange-950 text-orange-400 border-orange-900' :
                        'bg-yellow-950 text-yellow-400 border-yellow-900'
                      }`}>
                        {selectedMention.severity}
                      </span>
                      <span className="text-xs font-mono text-accent-green">
                        {selectedMention.source.replace(/_/g, '.').toUpperCase()}
                      </span>
                    </div>
                    <button onClick={() => setSelectedMention(null)} className="text-text-muted hover:text-text-primary text-xl">✕</button>
                  </div>

                  <h2 className="text-base font-mono font-bold text-text-primary mb-4">{selectedMention.title}</h2>

                  {/* Metadata grid */}
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    {[
                      { label: 'Keyword Matched', value: selectedMention.keyword_matched },
                      { label: 'Posted By',        value: selectedMention.threat_actor || '—' },
                      { label: 'Discovered',       value: new Date(selectedMention.discovered_at).toLocaleString() },
                      { label: 'Source',           value: selectedMention.source },
                    ].map((item) => (
                      <div key={item.label} className="bg-background rounded p-3 border border-border">
                        <div className="text-xs text-text-muted font-mono uppercase tracking-widest mb-1">{item.label}</div>
                        <div className="text-sm font-mono text-text-primary">{item.value}</div>
                      </div>
                    ))}
                  </div>

                  {/* Snippet */}
                  {selectedMention.snippet && (
                    <div className="mb-4">
                      <div className="text-xs font-mono text-text-muted uppercase tracking-widest mb-2">Content Preview</div>
                      <div className="bg-background rounded p-3 border border-border text-sm text-text-muted leading-relaxed font-mono">
                        {selectedMention.snippet}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-3 pt-4 border-t border-border mb-4">
                    {selectedMention.source_url && (
                      <a
                        href={selectedMention.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-4 py-2 rounded border border-accent-green text-xs font-mono text-accent-green hover:bg-accent-green hover:text-black transition-all"
                      >
                        Open Forum Post ↗
                      </a>
                    )}
                    <button
                      onClick={async () => {
                        await api.patch(`/darkweb/mentions/${selectedMention.id}`, { is_reviewed: true })
                        setSelectedMention(null)
                        loadForumData()
                      }}
                      className="px-4 py-2 rounded border border-green-700 text-xs font-mono text-green-400 hover:bg-green-950 transition-all"
                    >
                      ✓ Mark Reviewed
                    </button>
                    <button
                      onClick={async () => {
                        await api.patch(`/darkweb/mentions/${selectedMention.id}`, { is_false_positive: true })
                        setSelectedMention(null)
                        loadForumData()
                      }}
                      className="px-4 py-2 rounded border border-border text-xs font-mono text-text-muted hover:text-text-primary transition-all"
                    >
                      False Positive
                    </button>
                  </div>

                  {/* Analyst notes */}
                  <div>
                    <div className="text-xs font-mono text-text-muted uppercase tracking-widest mb-2">Analyst Notes</div>
                    <AnalystNoteEditor
                      mentionId={selectedMention.id}
                      existingNote={selectedMention.analyst_notes}
                      onSave={() => loadForumData()}
                    />
                  </div>
                </div>
              </div>
            )}

          </div>
        )}

        {/* ── SCANS ─────────────────────────────────────────────────────────── */}
        {activeTab === 'scans' && (
          <div className="space-y-3">
            {scans.length === 0 ? (
              <div className="text-center py-16 border border-dashed border-border rounded-lg">
                <p className="text-text-muted font-mono text-sm">No scans yet</p>
                <p className="text-xs text-text-muted mt-2">Trigger a scan from the Ransomware tab</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      {['Type', 'Source', 'Status', 'Keywords', 'Found', 'New', 'Duration', 'Started'].map((h) => (
                        <th key={h} className="text-left text-xs font-mono text-text-muted uppercase tracking-widest pb-3 pr-4">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {scans.map((s) => (
                      <tr key={s.id} className="border-b border-border">
                        <td className="py-3 pr-4"><span className="text-xs font-mono text-text-primary">{s.scan_type}</span></td>
                        <td className="py-3 pr-4"><span className="text-xs font-mono text-text-muted">{s.source || 'all'}</span></td>
                        <td className="py-3 pr-4">
                          <span className={`text-xs font-mono ${
                            s.status === 'completed' ? 'text-accent-green'
                            : s.status === 'running' ? 'text-yellow-400'
                            : s.status === 'failed' ? 'text-danger'
                            : 'text-gray-400'
                          }`}>{s.status}</span>
                        </td>
                        <td className="py-3 pr-4"><span className="text-xs font-mono text-text-muted">{s.keywords_scanned}</span></td>
                        <td className="py-3 pr-4"><span className="text-xs font-mono text-accent-green">{s.mentions_found}</span></td>
                        <td className="py-3 pr-4"><span className="text-xs font-mono text-green-400">{s.new_mentions}</span></td>
                        <td className="py-3 pr-4">
                          <span className="text-xs font-mono text-text-muted">
                            {s.duration_seconds ? `${s.duration_seconds.toFixed(1)}s` : '—'}
                          </span>
                        </td>
                        <td className="py-3">
                          <span className="text-xs font-mono text-text-muted">
                            {s.started_at ? new Date(s.started_at).toLocaleString() : '—'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

      </div>

      {showAddModal && (
        <AddKeywordModal
          onClose={() => setShowAddModal(false)}
          onSave={() => { loadKeywords(); loadStats() }}
        />
      )}
    </AppLayout>
  )
}
