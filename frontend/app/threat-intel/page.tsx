'use client'

import { useEffect, useState, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import IOCBadge from '@/components/ui/IOCBadge'
import ThreatScoreRing from '@/components/ui/ThreatScoreRing'
import { Search, RefreshCw, Shield } from 'lucide-react'
import { formatRelativeTime } from '@/lib/utils'
import EnrichmentCards from '@/components/ui/EnrichmentCards'

interface IOC {
  id: number
  value: string
  ioc_type: string
  risk_score: number
  sources: string[]
  analyst_notes?: string
  first_seen: string
  last_seen: string
}

interface SearchResult {
  ioc: IOC
  enrichments: Record<string, any>
  risk_score: number
}

export default function ThreatIntelPage() {
  const [iocs, setIocs] = useState<IOC[]>([])
  const [searchValue, setSearchValue] = useState('')
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null)
  const [searching, setSearching] = useState(false)
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<any>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [filterType, setFilterType] = useState('')

  const fetchIOCs = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '20' })
      if (filterType) params.set('ioc_type', filterType)
      const { data } = await api.get(`/threat-intel/iocs?${params}`)
      setIocs(data.items)
      setTotal(data.total)
    } catch {}
    setLoading(false)
  }, [page, filterType])

  useEffect(() => {
    fetchIOCs()
    api.get('/threat-intel/stats').then(({ data }) => setStats(data)).catch(() => {})
  }, [fetchIOCs])

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchValue.trim()) return
    setSearching(true)
    setSearchResult(null)
    try {
      const { data } = await api.post(`/threat-intel/search?value=${encodeURIComponent(searchValue)}`)
      setSearchResult(data)
    } catch {}
    setSearching(false)
  }

  const triggerFeedRefresh = async () => {
    try {
      await api.post('/threat-intel/feeds/refresh')
    } catch {}
  }

  return (
    <AppLayout title="SENTINEL / Threat Intelligence">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              <Shield className="w-5 h-5 text-accent-blue" />
              Threat Intelligence
            </h1>
            <p className="text-xs text-text-muted mt-0.5">IOC search, feeds, and enrichment</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={triggerFeedRefresh}
              className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-primary border border-border rounded px-3 py-1.5 hover:bg-surface transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Refresh Feeds
            </button>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Total IOCs', value: stats.total_iocs },
              { label: 'IOCs (24h)', value: stats.iocs_24h },
              { label: 'Critical Risk', value: stats.critical_iocs },
              { label: 'Feed Items (24h)', value: stats.feed_items_24h },
            ].map((s) => (
              <div key={s.label} className="sentinel-card text-center">
                <div className="text-xl font-bold font-mono text-accent-green">{s.value}</div>
                <div className="text-xs text-text-muted mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* IOC Search */}
        <div className="sentinel-card">
          <h2 className="text-sm font-semibold mb-3 font-mono text-accent-blue">IOC LOOKUP</h2>
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              placeholder="Enter IP, domain, hash, URL, or email..."
              className="sentinel-input font-mono flex-1"
            />
            <button
              type="submit"
              disabled={searching}
              className="flex items-center gap-2 bg-accent-blue text-white px-4 py-2 rounded text-sm font-medium hover:bg-accent-blue/90 transition-colors disabled:opacity-50"
            >
              <Search className="w-4 h-4" />
              {searching ? 'Searching...' : 'Search'}
            </button>
          </form>

          {/* Search Result */}
          {(searching || searchResult) && (
            <div className="mt-4 border border-border rounded-lg p-4 bg-background/40">
              {searching ? (
                <div className="flex items-start gap-4">
                  <div className="w-16 h-16 rounded-full bg-border/40 animate-pulse shrink-0" />
                  <div className="flex-1">
                    <div className="h-5 w-36 bg-border/40 rounded animate-pulse mb-1" />
                    <div className="h-3 w-20 bg-border/30 rounded animate-pulse mb-3" />
                    <EnrichmentCards enrichments={{}} loading />
                  </div>
                </div>
              ) : searchResult && (
                <div className="flex items-start gap-4">
                  <ThreatScoreRing score={Math.round(searchResult.risk_score)} />
                  <div className="flex-1">
                    <div className="flex items-center gap-3 flex-wrap mb-2">
                      <IOCBadge type={searchResult.ioc.ioc_type} value={searchResult.ioc.value} />
                    </div>
                    <EnrichmentCards enrichments={searchResult.enrichments} />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* IOC Table */}
        <div className="sentinel-card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold font-mono">IOC DATABASE ({total})</h2>
            <select
              value={filterType}
              onChange={(e) => { setFilterType(e.target.value); setPage(1) }}
              className="bg-background border border-border rounded px-2 py-1 text-xs text-text-primary focus:outline-none"
            >
              <option value="">All Types</option>
              {['ip', 'domain', 'hash', 'url', 'email'].map((t) => (
                <option key={t} value={t}>{t.toUpperCase()}</option>
              ))}
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="sentinel-table">
              <thead>
                <tr>
                  <th>IOC Value</th>
                  <th>Type</th>
                  <th>Risk Score</th>
                  <th>Sources</th>
                  <th>First Seen</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={6} className="text-center py-8 text-text-muted font-mono text-xs">LOADING...</td></tr>
                )}
                {!loading && iocs.length === 0 && (
                  <tr><td colSpan={6} className="text-center py-8 text-text-muted font-mono text-xs">NO IOCs FOUND</td></tr>
                )}
                {iocs.map((ioc) => (
                  <tr key={ioc.id}>
                    <td>
                      <IOCBadge type={ioc.ioc_type} value={ioc.value} />
                    </td>
                    <td><span className="font-mono text-xs text-text-muted">{ioc.ioc_type.toUpperCase()}</span></td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${ioc.risk_score}%`,
                              background: ioc.risk_score >= 75 ? '#ef4444' : ioc.risk_score >= 50 ? '#f59e0b' : '#3b82f6',
                            }}
                          />
                        </div>
                        <span className="font-mono text-xs">{Math.round(ioc.risk_score)}</span>
                      </div>
                    </td>
                    <td>
                      <div className="flex gap-1 flex-wrap">
                        {(ioc.sources || []).slice(0, 3).map((s) => (
                          <span key={s} className="text-[9px] font-mono px-1 py-0.5 bg-surface rounded border border-border text-text-muted">{s}</span>
                        ))}
                      </div>
                    </td>
                    <td><span className="text-xs text-text-muted font-mono">{formatRelativeTime(ioc.first_seen)}</span></td>
                    <td><span className="text-xs text-text-muted font-mono">{formatRelativeTime(ioc.last_seen)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {total > 20 && (
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
              <span className="text-xs text-text-muted font-mono">
                Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30 hover:bg-surface"
                >
                  Prev
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page * 20 >= total}
                  className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30 hover:bg-surface"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
