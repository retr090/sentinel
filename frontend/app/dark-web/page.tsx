'use client'

import { useCallback, useEffect, useState } from 'react'
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
  title?: string
  source?: string
  severity?: string
  keyword_matched?: string
  discovered_at?: string
  is_reviewed?: boolean
  source_url?: string
  snippet?: string
  threat_actor?: string
  analyst_notes?: string
  triage_status?: string
  is_false_positive?: boolean
  raw_data?: Record<string, any>
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

const parseBackendTime = (value: string) => (
  /(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`
)

const formatColomboTime = (value?: string) => (
  value
    ? new Date(parseBackendTime(value)).toLocaleString('en-GB', { timeZone: 'Asia/Colombo', hour12: false }) + ' GMT+05:30'
    : '-'
)

export default function DarkWebPage() {
  const [stats, setStats] = useState<any>(null)
  const [ransomware, setRansomware] = useState<any>(null)
  const [ransomwareSummary, setRansomwareSummary] = useState<any>(null)
  const [forums, setForums] = useState<any>(null)
  const [scans, setScans] = useState<Scan[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('ransomware')
  const [ransomwareDays, setRansomwareDays] = useState(30)
  const [selectedVictim, setSelectedVictim] = useState<RansomwareVictim | null>(null)
  const [selectedMention, setSelectedMention] = useState<ForumMention | null>(null)

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [statsRes, victimsRes, rwStatsRes, rwSummaryRes, forumsRes, scansRes] = await Promise.all([
        api.get('/darkweb/stats'),
        api.get('/darkweb/ransomware/victims', { params: { days: ransomwareDays, limit: 100 } }),
        api.get('/darkweb/ransomware/stats'),
        api.get('/darkweb/ransomware/summary', { params: { days: ransomwareDays } }),
        api.get('/darkweb/forum-mentions', { params: { days: 30, limit: 25 } }),
        api.get('/darkweb/scans', { params: { limit: 10 } }),
      ])
      setStats(statsRes.data)
      setRansomware({ victims: victimsRes.data, stats: rwStatsRes.data })
      setRansomwareSummary(rwSummaryRes.data)
      setForums(forumsRes.data)
      setScans(scansRes.data || [])
    } finally {
      setLoading(false)
    }
  }, [ransomwareDays])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  const triggerScan = async (scanType: 'ransomware' | 'historical' | 'forums') => {
    setRunning(scanType)
    try {
      await api.post('/darkweb/scan/trigger', null, { params: { scan_type: scanType } })
      setTimeout(() => void loadAll().finally(() => setRunning(null)), 15000)
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
            { id: 'ransomware' as const, label: 'Ransomware Intel', count: ransomware?.stats?.total_victims ?? 0 },
            { id: 'forums' as const, label: 'Forum Intel', count: forums?.stats?.total ?? 0 },
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
              {tab.label} <span className="text-[10px] opacity-70">{tab.count}</span>
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

        {selectedMention && (
          <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setSelectedMention(null)}>
            <div className="bg-surface border border-border rounded-lg w-full max-w-3xl max-h-[85vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-start justify-between gap-4 mb-5">
                <div>
                  <div className="text-xs font-mono text-accent-green uppercase tracking-widest mb-2">Forum Mention Detail</div>
                  <h3 className="text-lg font-mono font-bold text-text-primary">{selectedMention.title || 'Untitled forum mention'}</h3>
                  <p className="text-sm text-text-muted mt-1">{selectedMention.source} / {selectedMention.threat_actor || 'No threat actor'}</p>
                </div>
                <button onClick={() => setSelectedMention(null)} className="text-text-muted hover:text-text-primary text-xl">x</button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
                <div className="bg-background border border-border rounded p-3">
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Severity</div>
                  <Severity value={selectedMention.severity} />
                </div>
                <div className="bg-background border border-border rounded p-3">
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Matched By</div>
                  <div className="text-sm font-mono text-text-primary">{selectedMention.keyword_matched || '-'}</div>
                </div>
                <div className="bg-background border border-border rounded p-3">
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Discovered</div>
                  <div className="text-sm font-mono text-text-primary">{selectedMention.discovered_at ? new Date(selectedMention.discovered_at).toLocaleString() : '-'}</div>
                </div>
              </div>

              {selectedMention.snippet && (
                <div className="mb-5">
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-2">Forum Snippet</div>
                  <div className="bg-background border border-border rounded p-4 text-sm text-text-muted leading-relaxed whitespace-pre-wrap">{selectedMention.snippet}</div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
                {[
                  ['Thread URL', selectedMention.source_url],
                  ['Triage', selectedMention.triage_status || 'new'],
                  ['Reviewed', selectedMention.is_reviewed ? 'Yes' : 'No'],
                  ['False Positive', selectedMention.is_false_positive ? 'Yes' : 'No'],
                ].map(([label, value]) => (
                  <div key={label || ''} className="bg-background border border-border rounded p-3 min-w-0">
                    <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">{label}</div>
                    {label === 'Thread URL' && value ? (
                      <a href={String(value)} target="_blank" rel="noopener noreferrer" className="text-sm font-mono text-blue-400 hover:underline break-all">{value}</a>
                    ) : (
                      <div className="text-sm font-mono text-text-primary break-all">{value || '-'}</div>
                    )}
                  </div>
                ))}
                {selectedMention.analyst_notes && (
                  <div className="col-span-full bg-background border border-border rounded p-3 min-w-0">
                    <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Analyst Notes</div>
                    <div className="text-sm font-mono text-text-primary whitespace-pre-wrap">{selectedMention.analyst_notes}</div>
                  </div>
                )}
              </div>

              {selectedMention.raw_data?.ai_analysis && (
                <div className="mb-5 p-4 bg-background border border-border rounded">
                  <div className="text-[10px] font-mono text-accent-green uppercase tracking-widest mb-3">AI Analysis</div>
                  <div className="space-y-2 text-sm">
                    {typeof selectedMention.raw_data.ai_analysis.confidence === 'number' && (
                      <div className="flex gap-3">
                        <span className="font-mono text-text-muted w-32 shrink-0">Confidence:</span>
                        <span className="font-mono text-text-primary">{Math.round(selectedMention.raw_data.ai_analysis.confidence * 100)}%</span>
                      </div>
                    )}
                    {selectedMention.raw_data.ai_analysis.summary && (
                      <div className="flex gap-3">
                        <span className="font-mono text-text-muted w-32 shrink-0">Summary:</span>
                        <span className="font-mono text-text-primary">{selectedMention.raw_data.ai_analysis.summary}</span>
                      </div>
                    )}
                    {selectedMention.raw_data.ai_analysis.data_types?.length > 0 && (
                      <div className="flex gap-3">
                        <span className="font-mono text-text-muted w-32 shrink-0">Data Types:</span>
                        <span className="font-mono text-text-primary">{selectedMention.raw_data.ai_analysis.data_types.join(', ')}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {selectedMention.raw_data && Object.keys(selectedMention.raw_data).filter(k => k !== 'ai_analysis').length > 0 && (
                <div>
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-2">Raw Data</div>
                  <div className="bg-background border border-border rounded divide-y divide-border max-h-64 overflow-y-auto">
                    {Object.entries(selectedMention.raw_data).filter(([k]) => k !== 'ai_analysis').map(([key, value]) => (
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
              <span className="text-xs font-mono text-text-muted">Unreviewed: {forums?.stats?.unreviewed ?? 0}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => triggerScan('forums')} disabled={!!running} className="px-3 py-2 rounded bg-accent-green text-black font-mono text-xs font-bold disabled:opacity-50">
                {running === 'forums' ? 'Running...' : 'Scan Now'}
              </button>
              <a href="/dark-web/forums" className="px-3 py-2 rounded border border-border text-xs font-mono text-accent-green hover:border-accent-green">Open Workspace</a>
            </div>
          </div>
          <div className="divide-y divide-border">
            {(forums?.mentions || []).map((m: ForumMention) => (
              <div key={m.id} onClick={() => setSelectedMention(m)} className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3 cursor-pointer hover:bg-background/60 transition-colors">
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-text-primary truncate">{m.title || 'Untitled forum mention'}</div>
                  <div className="text-xs text-text-muted font-mono mt-1 truncate">{m.source} / {m.keyword_matched || 'keyword match'} / {m.discovered_at ? new Date(m.discovered_at).toLocaleString() : '-'}</div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  {m.source_url && (
                    <a href={m.source_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-[10px] font-mono text-blue-400 hover:underline">Open</a>
                  )}
                  <Severity value={m.severity} />
                </div>
              </div>
            ))}
            {!loading && !forums?.mentions?.length && <div className="p-6 text-text-muted">No forum mentions found.</div>}
          </div>
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
