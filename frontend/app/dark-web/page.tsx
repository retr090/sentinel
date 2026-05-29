'use client'

import { useCallback, useEffect, useState, useRef } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'

type Scan = {
  id: string
  scan_type: string
  source?: string
  status: string
  mentions_found: number
  new_mentions: number
  created_at?: string
}

type RansomwareVictim = {
  id: string
  threat_actor?: string
  victim_org?: string
  victim_country?: string
  severity?: string
  sector?: string
  data_status?: string
  triage_status?: string
  title?: string
  snippet?: string
  source_url?: string
  keyword_matched?: string
  posted_at?: string
  feed_posted_at?: string
  collected_at?: string
  raw_data?: Record<string, any>
  analyst_seen_at?: string | null
  analyst_notes?: string | null
}

type ForumMention = {
  id: string
  title: string
  source: string
  severity: string
  keyword_matched: string
  discovered_at: string
  feed_posted_at: string | null
  is_reviewed: boolean
  source_url: string | null
  snippet: string | null
  threat_actor: string | null
  analyst_notes: string | null
  triage_status: string
  is_false_positive: boolean
  category: string | null
  raw_data?: Record<string, any>
}

interface MentionStats {
  total: number
  critical_high: number
  unreviewed: number
  by_source: Record<string, number>
}

type Tab = 'ransomware' | 'forums'

const StatCard = ({ label, value, sub }: { label: string; value: number | string; sub?: string }) => (
  <div className="bg-surface border border-border rounded-lg p-4">
    <div className="text-xs font-mono text-text-muted uppercase tracking-widest mb-1">{label}</div>
    <div className="text-2xl font-bold font-mono text-accent-green">{value}</div>
    {sub && <div className="text-xs text-text-muted mt-1">{sub}</div>}
  </div>
)

const Severity = ({ value }: { value?: string }) => {
  const cls: Record<string, string> = {
    CRITICAL: 'text-red-400 border-red-900 bg-red-950',
    HIGH: 'text-orange-400 border-orange-900 bg-orange-950',
    MEDIUM: 'text-yellow-400 border-yellow-900 bg-yellow-950',
    LOW: 'text-gray-400 border-gray-700 bg-gray-900',
  }
  return <span className={`text-xs font-mono px-2 py-0.5 rounded border ${cls[value || 'LOW'] || cls.LOW}`}>{value || 'LOW'}</span>
}

const SevBadge = ({ s }: { s: string }) => {
  const SEV: Record<string, string> = {
    CRITICAL: 'bg-red-950 text-red-400 border-red-900',
    HIGH: 'bg-orange-950 text-orange-400 border-orange-900',
    MEDIUM: 'bg-yellow-950 text-yellow-400 border-yellow-900',
    LOW: 'bg-gray-900 text-gray-400 border-gray-700',
  }
  return <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${SEV[s] || SEV.LOW}`}>{s}</span>
}

const parseBackendTime = (value: string) => (
  /(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`
)

const formatColomboTime = (value?: string) => (
  value
    ? new Date(parseBackendTime(value)).toLocaleString('en-GB', { timeZone: 'Asia/Colombo', hour12: false }) + ' GMT+05:30'
    : '-'
)

// ── Mention row + expanded detail ─────────────────────────────────────────────

interface MentionRowProps {
  m: ForumMention
  isExpanded: boolean
  onToggle: () => void
  onReview: (id: string, updates: Partial<ForumMention>) => void
  reviewing: boolean
}

const MentionRow = ({ m, isExpanded, onToggle, onReview, reviewing }: MentionRowProps) => {
  const [notes, setNotes] = useState(m.analyst_notes || '')

  const domain = m.source_url ? (() => { try { return new URL(m.source_url!).hostname } catch { return m.source_url } })() : null

  return (
    <>
      <tr
        className={`border-b border-border cursor-pointer transition-colors ${isExpanded ? 'bg-surface/80' : 'hover:bg-surface/50'} ${!m.is_reviewed ? 'border-l-2 border-l-accent-green' : ''}`}
        onClick={onToggle}
      >
        <td className="px-4 py-3 w-4">
          <span className={`text-[10px] font-mono text-text-muted transition-transform inline-block ${isExpanded ? 'rotate-90' : ''}`}>›</span>
        </td>
        <td className="px-4 py-3"><SevBadge s={m.severity} /></td>
        <td className="px-4 py-3 max-w-xs">
          <div className="flex items-center gap-2">
            <a
              href={m.source_url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              onClick={e => e.stopPropagation()}
              className="text-xs font-mono text-text-primary truncate hover:text-blue-400 hover:underline"
              title={`Open thread: ${m.title}`}
            >
              {m.title || '(no title)'}
              {!m.is_reviewed && <span className="text-[9px] font-mono px-1 py-0.5 rounded bg-accent-green/20 text-accent-green border border-accent-green/40 leading-none">NEW</span>}
            </a>
            {m.source_url && (
              <a
                href={m.source_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={e => e.stopPropagation()}
                className="text-[10px] font-mono text-blue-400 hover:underline shrink-0"
                title="Open forum thread"
              >
                ↗
              </a>
            )}
          </div>
          {m.snippet && <div className="text-[10px] text-text-muted mt-0.5 line-clamp-1">{m.snippet}</div>}
        </td>
        <td className="px-4 py-3 text-[10px] font-mono text-text-muted">{m.keyword_matched}</td>
        <td className="px-4 py-3 text-[10px] font-mono text-text-muted whitespace-nowrap">
          {m.feed_posted_at ? new Date(m.feed_posted_at).toLocaleDateString() : '—'}
        </td>
        <td className="px-4 py-3">
          {m.source_url ? (
            <a
              href={m.source_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={e => e.stopPropagation()}
              title={m.source_url}
              className="inline-flex items-center gap-1 text-[10px] font-mono text-accent-green hover:underline whitespace-nowrap"
            >
              {domain}
              <svg className="w-2.5 h-2.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          ) : (
            <span className="text-[10px] font-mono text-text-muted">—</span>
          )}
        </td>
        <td className="px-4 py-3">
          {m.is_reviewed
            ? <span className="text-[10px] font-mono text-accent-green">✓ reviewed</span>
            : <span className="text-[10px] font-mono text-yellow-600 font-semibold">● NEW</span>}
        </td>
      </tr>
      {isExpanded && (
        <tr className="border-b border-border bg-surface/40">
          <td colSpan={7} className="px-6 py-4">
            <div className="space-y-4 max-w-3xl">

              {/* AI Analysis block */}
              {m.raw_data?.ai_analysis && (
                <div className="border border-blue-900 bg-blue-950/30 rounded-lg p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-blue-400 uppercase tracking-widest">AI Analysis</span>
                    <span className="text-[10px] font-mono text-blue-600">
                      {Math.round(m.raw_data.ai_analysis.confidence * 100)}% confidence
                    </span>
                  </div>
                  {m.raw_data.ai_analysis.summary && (
                    <p className="text-xs font-mono text-text-primary leading-relaxed">
                      {m.raw_data.ai_analysis.summary}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-3 text-[10px] font-mono">
                    {m.raw_data.ai_analysis.record_count && (
                      <span className="text-orange-400">
                        Records: {m.raw_data.ai_analysis.record_count}
                      </span>
                    )}
                    {m.raw_data.ai_analysis.data_types.length > 0 && (
                      <span className="text-text-muted">
                        Data: {m.raw_data.ai_analysis.data_types.join(', ')}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {m.snippet && (
                <div>
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Forum Snippet</div>
                  <div className="text-xs font-mono text-text-primary leading-relaxed whitespace-pre-wrap">{m.snippet}</div>
                </div>
              )}
              {m.threat_actor && (
                <div className="text-[10px] font-mono text-orange-400">Threat actor: {m.threat_actor}</div>
              )}
              {m.feed_posted_at && (
                <div className="text-[10px] font-mono text-text-muted">Thread posted: {new Date(m.feed_posted_at).toLocaleString()}</div>
              )}
              {m.source_url && (
                <div className="flex justify-end">
                  <a
                    href={m.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={e => e.stopPropagation()}
                    className="inline-flex items-center gap-2 text-xs font-mono px-4 py-2 rounded bg-accent-green/10 border border-accent-green/30 text-accent-green hover:bg-accent-green/20 transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    Open Thread on Forum
                  </a>
                </div>
              )}
              <div>
                <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Analyst Notes</div>
                <textarea
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  onClick={e => e.stopPropagation()}
                  rows={2}
                  placeholder="Add notes..."
                  className="w-full bg-background border border-border rounded px-3 py-2 text-xs font-mono text-text-primary focus:border-accent-green focus:outline-none resize-none"
                />
              </div>
              <div className="flex gap-2 flex-wrap" onClick={e => e.stopPropagation()}>
                {!m.is_reviewed && (
                  <button
                    disabled={reviewing}
                    onClick={() => onReview(m.id, { is_reviewed: true, analyst_notes: notes } as any)}
                    className="text-xs font-mono px-3 py-1.5 bg-accent-green text-black rounded hover:opacity-90 disabled:opacity-40">
                    {reviewing ? 'Saving...' : '✓ Mark Reviewed'}
                  </button>
                )}
                {notes !== (m.analyst_notes || '') && (
                  <button
                    disabled={reviewing}
                    onClick={() => onReview(m.id, { analyst_notes: notes } as any)}
                    className="text-xs font-mono px-3 py-1.5 border border-accent-green text-accent-green rounded hover:bg-accent-green/10 disabled:opacity-40">
                    Save Notes
                  </button>
                )}
                {!m.is_reviewed && (
                  <button
                    disabled={reviewing}
                    onClick={() => onReview(m.id, { is_false_positive: true, is_reviewed: true } as any)}
                    className="text-xs font-mono px-3 py-1.5 border border-red-800 text-red-400 rounded hover:bg-red-950 disabled:opacity-40">
                    ✗ False Positive
                  </button>
                )}
                {m.is_reviewed && (
                  <span className="text-[10px] font-mono text-accent-green self-center">Already reviewed</span>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export default function DarkWebPage() {
  const [stats, setStats] = useState<any>(null)
  const [ransomware, setRansomware] = useState<any>(null)
  const [ransomwareSummary, setRansomwareSummary] = useState<any>(null)
  const [scans, setScans] = useState<Scan[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('ransomware')
  const [ransomwareDays, setRansomwareDays] = useState(30)
  const [selectedVictim, setSelectedVictim] = useState<RansomwareVictim | null>(null)
  // Forum mentions state
  const [forumMentions, setForumMentions] = useState<ForumMention[]>([])
  const [forumMentionStats, setForumMentionStats] = useState<MentionStats>({ total: 0, critical_high: 0, unreviewed: 0, by_source: {} })
  const [forumExpandedId, setForumExpandedId] = useState<string | null>(null)
  const [forumReviewingId, setForumReviewingId] = useState<string | null>(null)
  const [forumFilterSeverity, setForumFilterSeverity] = useState('')
  const [forumFilterSearch, setForumFilterSearch] = useState('')
  const [forumFilterDays, setForumFilterDays] = useState(30)
  const [forumFilterTitleOnly, setForumFilterTitleOnly] = useState(false)
  const [forumPage, setForumPage] = useState(1)
  const forumReqId = useRef(0)
  const PAGE_LIMIT = 20

  const loadForumMentions = useCallback(async () => {
    const reqId = ++forumReqId.current
    const params = new URLSearchParams({
      days: String(forumFilterDays),
      page: String(forumPage),
      limit: String(PAGE_LIMIT),
    })
    if (forumFilterSeverity) params.set('severity', forumFilterSeverity)
    if (forumFilterSearch) params.set('keyword', forumFilterSearch)
    params.set('search_in', forumFilterTitleOnly ? 'title' : 'all')

    const res = await api.get(`/darkweb/forum-mentions?${params}`)
    if (reqId !== forumReqId.current) return
    setForumMentions(res.data.mentions ?? [])
    setForumMentionStats(res.data.stats ?? { total: 0, critical_high: 0, unreviewed: 0, by_source: {} })
  }, [forumFilterDays, forumPage, forumFilterSeverity, forumFilterSearch, forumFilterTitleOnly])

  const reviewMention = async (id: string, updates: Record<string, any>) => {
    setForumReviewingId(id)
    try {
      await api.patch(`/darkweb/mentions/${id}`, updates)
      setForumMentions(prev => prev.map(m => m.id === id ? { ...m, ...updates } : m))
      loadForumMentions()
    } catch {} finally { setForumReviewingId(null) }
  }

  const markAllViewed = async () => {
    try {
      await api.post('/darkweb/forum-mentions/mark-all-viewed')
      setForumMentions(prev => prev.map(m => ({ ...m, is_reviewed: true })))
      loadForumMentions()
    } catch {}
  }

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [statsRes, victimsRes, rwStatsRes, rwSummaryRes, scansRes] = await Promise.all([
        api.get('/darkweb/stats'),
        api.get('/darkweb/ransomware/victims', { params: { days: ransomwareDays, limit: 100 } }),
        api.get('/darkweb/ransomware/stats'),
        api.get('/darkweb/ransomware/summary', { params: { days: ransomwareDays } }),
        api.get('/darkweb/scans', { params: { limit: 10 } }),
      ])
      setStats(statsRes.data)
      setRansomware({ victims: victimsRes.data, stats: rwStatsRes.data })
      setRansomwareSummary(rwSummaryRes.data)
      setScans(scansRes.data || [])
    } finally {
      setLoading(false)
    }
  }, [ransomwareDays])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  // Re-fetch forum mentions when any filter or page changes
  useEffect(() => {
    loadForumMentions()
  }, [forumFilterSeverity, forumFilterSearch, forumFilterDays, forumFilterTitleOnly, forumPage, loadForumMentions])

  const triggerScan = async (scanType: 'ransomware' | 'historical' | 'forums') => {
    setRunning(scanType)
    try {
      await api.post('/darkweb/scan/trigger', null, { params: { scan_type: scanType } })
      setTimeout(() => {
        void loadAll()
        if (scanType === 'forums') void loadForumMentions()
        setRunning(null)
      }, 15000)
    } catch {
      setRunning(null)
    }
  }

  const markSeen = async (id: string) => {
    await api.patch(`/darkweb/ransomware/victims/${id}/seen`)
    await loadAll()
  }

  const updateVictim = async (id: string, updates: Record<string, any>) => {
    await api.patch(`/darkweb/mentions/${id}`, updates)
    await loadAll()
    setSelectedVictim((current) => current?.id === id ? { ...current, ...updates } : current)
  }

  return (
    <AppLayout title="SENTINEL / Dark Web Intel">
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-xl font-mono font-bold text-text-primary">Dark Web Intel</h1>
            <p className="text-sm text-text-muted mt-1">Ransomware feed tracking and authenticated forum intelligence.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard label="Mentions 24h" value={stats?.mentions_24h ?? 0} />
          <StatCard label="Ransomware 24h" value={stats?.ransomware_24h ?? 0} />
          <StatCard label="Forum 24h" value={stats?.forum_mentions_24h ?? 0} />
        </div>

        <div className="flex gap-2 border-b border-border">
          {[
            { id: 'ransomware' as const, label: 'Ransomware Intel', count: ransomware?.stats?.unread_ransomware_count ?? 0 },
            { id: 'forums' as const, label: 'Forum Intel', count: forumMentionStats.unreviewed },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-xs font-mono uppercase tracking-widest border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-accent-green text-accent-green'
                  : 'border-transparent text-text-muted hover:text-text-primary'
              }`}
            >
              {tab.label}
              {tab.id === 'forums' && tab.count > 0 && (
                <span className="ml-1 text-[10px] text-red-500 font-bold">{tab.count}</span>
              )}
              {tab.id === 'ransomware' && tab.count > 0 && (
                <span className="ml-1 text-[10px] text-red-500 font-bold">{tab.count}</span>
              )}
            </button>
          ))}
        </div>

        {activeTab === 'ransomware' && <section className="bg-surface border border-border rounded-lg overflow-hidden">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <div>
              <h2 className="font-mono text-sm font-bold tracking-widest text-accent-green">RANSOMWARE INTEL</h2>
              <span className="text-xs font-mono text-text-muted">Sri Lanka-related victims for selected timeframe</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <select
                value={ransomwareDays}
                onChange={(event) => setRansomwareDays(Number(event.target.value))}
                className="bg-background border border-border rounded px-3 py-2 text-xs text-text-primary font-mono focus:border-accent-green focus:outline-none"
              >
                <option value={1}>Last 24 hours</option>
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={365}>Last year</option>
                <option value={0}>All time</option>
              </select>
              <button onClick={() => triggerScan('ransomware')} disabled={!!running} className="px-3 py-2 rounded bg-accent-green text-black font-mono text-xs font-bold disabled:opacity-50">
                {running === 'ransomware' ? 'Running...' : 'Scan Now'}
              </button>
              <button onClick={() => triggerScan('historical')} disabled={!!running} className="px-3 py-2 rounded border border-border text-text-muted font-mono text-xs disabled:opacity-50">
                Sync LK Country Feed
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 border-b border-border bg-background/40">
            <StatCard label="Current Results" value={ransomware?.victims?.victims?.length ?? 0} sub={ransomwareDays === 0 ? 'all time' : `${ransomwareDays} days`} />
            <StatCard label="All Tracked" value={ransomware?.stats?.total_victims ?? 0} sub="Sri Lanka related" />
            <StatCard label="Last 7 Days" value={ransomware?.stats?.victims_last_7d ?? 0} />
            <StatCard label="Critical / High" value={ransomware?.stats?.critical_high_hits ?? 0} />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-4 border-b border-border">
            <div className="bg-background border border-border rounded p-3">
              <div className="text-xs font-mono text-text-muted uppercase tracking-widest mb-3">Top Groups</div>
              <div className="space-y-2">
                {(ransomwareSummary?.groups || []).slice(0, 5).map((g: any) => (
                  <div key={g.group} className="flex justify-between gap-3 text-xs font-mono">
                    <span className="text-text-primary truncate">{g.group}</span>
                    <span className="text-accent-green">{g.victims}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-background border border-border rounded p-3">
              <div className="text-xs font-mono text-text-muted uppercase tracking-widest mb-3">Sectors</div>
              <div className="space-y-2">
                {(ransomwareSummary?.by_sector || []).slice(0, 5).map((s: any) => (
                  <div key={s.sector} className="flex justify-between gap-3 text-xs font-mono">
                    <span className="text-text-primary truncate">{s.sector}</span>
                    <span className="text-accent-green">{s.count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-background border border-border rounded p-3">
              <div className="text-xs font-mono text-text-muted uppercase tracking-widest mb-3">Monthly Timeline</div>
              <div className="space-y-2">
                {(ransomwareSummary?.timeline || []).slice(-5).map((t: any) => (
                  <div key={t.month} className="flex justify-between gap-3 text-xs font-mono">
                    <span className="text-text-primary">{t.month}</span>
                    <span className="text-accent-green">{t.count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs font-mono text-text-muted uppercase bg-background">
                <tr>
                  <th className="text-left p-3">Victim</th>
                  <th className="text-left p-3">Group</th>
                  <th className="text-left p-3">Country</th>
                  <th className="text-left p-3">Sector</th>
                  <th className="text-left p-3">Data</th>
                  <th className="text-left p-3">Severity</th>
                  <th className="text-left p-3">Posted</th>
                  <th className="text-left p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {(ransomware?.victims?.victims || []).map((v: RansomwareVictim) => (
                  <tr key={v.id} className="border-t border-border">
                    <td className="p-3 text-text-primary">{v.victim_org || v.title || 'Unknown'}</td>
                    <td className="p-3 text-text-muted">{v.threat_actor || '-'}</td>
                    <td className="p-3 text-text-muted">{v.victim_country || '-'}</td>
                    <td className="p-3 text-text-muted">{v.sector || 'Unknown'}</td>
                    <td className="p-3 text-text-muted">{v.data_status || 'Unknown'}</td>
                    <td className="p-3"><Severity value={v.severity} /></td>
                    <td className="p-3 text-text-muted font-mono text-xs">{formatColomboTime(v.posted_at)}</td>
                    <td className="p-3 flex flex-wrap gap-3">
                      <button onClick={() => setSelectedVictim(v)} className="text-xs font-mono text-accent-green hover:underline">Details</button>
                      {v.source_url && (
                        <a href={v.source_url} target="_blank" rel="noopener noreferrer" className="text-xs font-mono text-blue-400 hover:underline">Source</a>
                      )}
                      {v.analyst_seen_at ? (
                        <span className="text-xs text-text-muted font-mono">Seen</span>
                      ) : (
                        <button onClick={() => markSeen(v.id)} className="text-xs font-mono text-accent-green hover:underline">Mark seen</button>
                      )}
                    </td>
                  </tr>
                ))}
                {!loading && !ransomware?.victims?.victims?.length && <tr><td className="p-6 text-text-muted" colSpan={8}>No ransomware victims found.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>}

        {selectedVictim && (
          <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setSelectedVictim(null)}>
            <div className="bg-surface border border-border rounded-lg w-full max-w-3xl max-h-[85vh] overflow-y-auto p-6" onClick={(event) => event.stopPropagation()}>
              <div className="flex items-start justify-between gap-4 mb-5">
                <div>
                  <div className="text-xs font-mono text-accent-green uppercase tracking-widest mb-2">Ransomware Victim Detail</div>
                  <h3 className="text-lg font-mono font-bold text-text-primary">{selectedVictim.victim_org || selectedVictim.title || 'Unknown victim'}</h3>
                  <p className="text-sm text-text-muted mt-1">{selectedVictim.threat_actor || 'Unknown group'} / {selectedVictim.victim_country || 'Unknown country'}</p>
                </div>
                <button onClick={() => setSelectedVictim(null)} className="text-text-muted hover:text-text-primary text-xl">x</button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
                <div className="bg-background border border-border rounded p-3">
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Severity</div>
                  <Severity value={selectedVictim.severity} />
                </div>
                <div className="bg-background border border-border rounded p-3">
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Matched By</div>
                  <div className="text-sm font-mono text-text-primary">{selectedVictim.keyword_matched || '-'}</div>
                </div>
                <div className="bg-background border border-border rounded p-3">
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Posted</div>
                  <div className="text-sm font-mono text-text-primary">{formatColomboTime(selectedVictim.posted_at)}</div>
                </div>
                <div className="bg-background border border-border rounded p-3">
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Sector</div>
                  <div className="text-sm font-mono text-text-primary">{selectedVictim.sector || 'Unknown'}</div>
                </div>
                <div className="bg-background border border-border rounded p-3">
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Data Status</div>
                  <div className="text-sm font-mono text-text-primary">{selectedVictim.data_status || 'Unknown'}</div>
                </div>
                <div className="bg-background border border-border rounded p-3">
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Triage</div>
                  <select
                    value={selectedVictim.triage_status || 'new'}
                    onChange={(event) => updateVictim(selectedVictim.id, {
                      triage_status: event.target.value,
                      is_reviewed: event.target.value !== 'new',
                      is_false_positive: event.target.value === 'false_positive',
                    })}
                    className="w-full bg-surface border border-border rounded px-2 py-1 text-sm font-mono text-text-primary"
                  >
                    <option value="new">New</option>
                    <option value="reviewed">Reviewed</option>
                    <option value="escalated">Escalated</option>
                    <option value="false_positive">False positive</option>
                  </select>
                </div>
              </div>

              {selectedVictim.snippet && (
                <div className="mb-5">
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-2">Feed Summary</div>
                  <div className="bg-background border border-border rounded p-4 text-sm text-text-muted leading-relaxed">{selectedVictim.snippet}</div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
                {[
                  ['Website / Source', selectedVictim.source_url],
                  ['Collected At', selectedVictim.collected_at ? formatColomboTime(selectedVictim.collected_at) : null],
                  ['Feed Posted At', selectedVictim.feed_posted_at ? formatColomboTime(selectedVictim.feed_posted_at) : null],
                  ['Analyst Status', selectedVictim.analyst_seen_at ? 'Seen' : 'Unseen'],
                ].map(([label, value]) => (
                  <div key={label || ''} className="bg-background border border-border rounded p-3 min-w-0">
                    <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">{label}</div>
                    {label === 'Website / Source' && value ? (
                      <a href={String(value)} target="_blank" rel="noopener noreferrer" className="text-sm font-mono text-blue-400 hover:underline break-all">{value}</a>
                    ) : (
                      <div className="text-sm font-mono text-text-primary break-all">{value || '-'}</div>
                    )}
                  </div>
                ))}
              </div>

              {selectedVictim.raw_data && Object.keys(selectedVictim.raw_data).length > 0 && (
                <div>
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-2">Raw Feed Fields</div>
                  <div className="bg-background border border-border rounded divide-y divide-border max-h-64 overflow-y-auto">
                    {Object.entries(selectedVictim.raw_data).map(([key, value]) => (
                      <div key={key} className="grid grid-cols-3 gap-3 p-3 text-xs">
                        <div className="font-mono text-text-muted break-all">{key}</div>
                        <div className="col-span-2 font-mono text-text-primary break-all">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'forums' && <section className="bg-surface border border-border rounded-lg overflow-hidden">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <div>
              <h2 className="font-mono text-sm font-bold tracking-widest text-accent-green">FORUM INTEL</h2>
              <span className="text-xs font-mono text-text-muted">Unreviewed: {forumMentionStats.unreviewed}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => triggerScan('forums')} disabled={!!running} className="px-3 py-2 rounded bg-accent-green text-black font-mono text-xs font-bold disabled:opacity-50">
                {running === 'forums' ? 'Running...' : 'Scan Now'}
              </button>
              <a href="/dark-web/forums" className="px-3 py-2 rounded border border-border text-xs font-mono text-text-muted hover:border-text-muted">Manage Sources →</a>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 border-b border-border bg-background/40">
            <StatCard label="Total Mentions" value={forumMentionStats.total} sub="all time" />
            <StatCard label="Unreviewed" value={forumMentionStats.unreviewed} sub="needs analyst review" />
            <StatCard label="Critical / High" value={forumMentionStats.critical_high} sub="high priority" />
            <StatCard label="Sources" value={Object.keys(forumMentionStats.by_source || {}).length} sub={Object.entries(forumMentionStats.by_source || {}).map(([k, v]) => `${k}: ${v}`).join(', ')} />
          </div>
          <div className="p-4 border-b border-border">
            <div className="flex flex-wrap gap-2 items-center">
              <input
                type="text"
                placeholder="title, org, gov.lk, srilanka..."
                value={forumFilterSearch}
                onChange={e => { setForumFilterSearch(e.target.value); setForumPage(1) }}
                className="bg-background border border-border rounded px-3 py-1.5 text-xs font-mono text-text-primary focus:border-accent-green focus:outline-none w-56"
              />
              <select
                value={forumFilterSeverity}
                onChange={e => { setForumFilterSeverity(e.target.value); setForumPage(1) }}
                className="bg-background border border-border rounded px-3 py-1.5 text-xs font-mono text-text-primary focus:border-accent-green focus:outline-none">
                <option value="">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
              <select
                value={String(forumFilterDays)}
                onChange={e => { setForumFilterDays(Number(e.target.value)); setForumPage(1) }}
                className="bg-background border border-border rounded px-3 py-1.5 text-xs font-mono text-text-primary focus:border-accent-green focus:outline-none">
                <option value="7">Last 7 days</option>
                <option value="30">Last 30 days</option>
                <option value="90">Last 90 days</option>
                <option value="365">Last year</option>
              </select>

              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={forumFilterTitleOnly}
                  onChange={e => { setForumFilterTitleOnly(e.target.checked); setForumPage(1) }}
                  className="accent-accent-green"
                />
                <span className="text-[10px] font-mono text-text-muted">Title only</span>
              </label>
              {(forumFilterSeverity || forumFilterSearch) && (
                <button
                  onClick={() => { setForumFilterSeverity(''); setForumFilterSearch(''); setForumPage(1) }}
                  className="text-[10px] font-mono text-text-muted hover:text-text-primary border border-border rounded px-2 py-1.5">
                  Clear filters
                </button>
              )}
              {forumMentionStats.unreviewed > 0 && (
                <button
                  onClick={markAllViewed}
                  className="text-[10px] font-mono text-accent-green border border-accent-green/40 rounded px-3 py-1.5 hover:bg-accent-green/10 transition-colors ml-auto">
                  Mark All Viewed ({forumMentionStats.unreviewed})
                </button>
              )}
            </div>
          </div>
          {loading ? (
            <div className="py-12 text-center text-xs text-text-muted font-mono">Loading...</div>
          ) : forumMentions.length === 0 ? (
            <div className="border border-dashed border-border rounded-lg py-12 text-center space-y-2 m-4">
              <div className="text-sm font-mono text-text-muted">No forum hits yet</div>
              <div className="text-xs text-text-muted">
                {forumFilterSeverity || forumFilterSearch
                  ? 'No hits match your filters — try clearing them'
                  : 'Trigger a scan — results appear here when keyword matches are found'}
              </div>
              {!forumFilterSeverity && !forumFilterSearch && (
                <button onClick={() => triggerScan('forums')} disabled={!!running}
                  className="mt-3 text-xs font-mono text-accent-green hover:underline disabled:opacity-40">
                  {running === 'forums' ? 'Scanning...' : 'Trigger Scan →'}
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto p-0">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    {['', 'Severity', 'Thread / Match', 'Keyword', 'Thread Date', 'Source', 'Status'].map(h => (
                      <th key={h} className="text-left text-[10px] font-mono text-text-muted uppercase tracking-widest px-4 pb-2 pt-3">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {forumMentions.map(m => (
                    <MentionRow
                      key={m.id}
                      m={m}
                      isExpanded={forumExpandedId === m.id}
                      onToggle={() => setForumExpandedId(prev => prev === m.id ? null : m.id)}
                      onReview={reviewMention}
                      reviewing={forumReviewingId === m.id}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {forumMentions.length > 0 && (() => {
            const totalPages = Math.ceil(forumMentionStats.total / PAGE_LIMIT)
            return totalPages > 1 && (
              <div className="flex items-center justify-between text-[10px] font-mono text-text-muted px-4 py-3 border-t border-border">
                <span>Page {forumPage} of {totalPages} · {forumMentionStats.total} total</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setForumPage(p => Math.max(1, p - 1))}
                    disabled={forumPage <= 1}
                    className="px-3 py-1 border border-border rounded hover:border-text-muted disabled:opacity-30">
                    ← Prev
                  </button>
                  <button
                    onClick={() => setForumPage(p => Math.min(totalPages, p + 1))}
                    disabled={forumPage >= totalPages}
                    className="px-3 py-1 border border-border rounded hover:border-text-muted disabled:opacity-30">
                    Next →
                  </button>
                </div>
              </div>
            )
          })()}
        </section>}

        <section className="bg-surface border border-border rounded-lg overflow-hidden">
          <div className="p-4 border-b border-border">
            <h2 className="font-mono text-sm font-bold tracking-widest text-accent-green">
              RECENT {activeTab === 'ransomware' ? 'RANSOMWARE' : 'FORUM'} SCANS
            </h2>
          </div>
          <div className="divide-y divide-border">
            {scans.filter((scan) => activeTab === 'ransomware'
              ? scan.scan_type.startsWith('ransomware')
              : scan.scan_type === 'forums'
            ).map((scan) => (
              <div key={scan.id} className="p-4 grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
                <div className="font-mono text-text-primary">{scan.scan_type}</div>
                <div className="text-text-muted">{scan.status}</div>
                <div className="text-text-muted">Found: {scan.mentions_found ?? 0}</div>
                <div className="text-text-muted">New: {scan.new_mentions ?? 0}</div>
                <div className="text-text-muted font-mono text-xs">{formatColomboTime(scan.created_at)}</div>
              </div>
            ))}
            {!loading && !scans.filter((scan) => activeTab === 'ransomware'
              ? scan.scan_type.startsWith('ransomware')
              : scan.scan_type === 'forums'
            ).length && <div className="p-6 text-text-muted">No scans recorded.</div>}
          </div>
        </section>
      </div>
    </AppLayout>
  )
}
