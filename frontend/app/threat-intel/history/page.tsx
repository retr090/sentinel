'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import IOCBadge from '@/components/ui/IOCBadge'
import { formatRelativeTime } from '@/lib/utils'
import { Clock, Search, Trash2, Download, Eye, Filter } from 'lucide-react'

interface IOCRecord {
  id: number
  value: string
  ioc_type: string
  risk_score: number
  risk_level: string
  sources: string[]
  analyst_notes?: string
  first_seen: string
  last_seen: string
  created_at: string
}

const RISK_BADGE: Record<string, string> = {
  critical: 'bg-danger/20 text-danger border border-danger/40',
  high: 'bg-warning/20 text-warning border border-warning/40',
  medium: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  low: 'bg-accent-green/10 text-accent-green border border-accent-green/30',
  clean: 'bg-border/60 text-text-muted border border-border',
}

const RISK_SCORE_COLOR = (score: number) => {
  if (score >= 75) return 'text-danger'
  if (score >= 50) return 'text-warning'
  if (score >= 25) return 'text-blue-400'
  return 'text-accent-green'
}

export default function HistoryPage() {
  const router = useRouter()
  const [iocs, setIocs] = useState<IOCRecord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [filterType, setFilterType] = useState('')
  const [filterRisk, setFilterRisk] = useState('')
  const [filterSearch, setFilterSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [exportingId, setExportingId] = useState<number | null>(null)

  const PAGE_SIZE = 20

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), limit: String(PAGE_SIZE) })
      if (filterType) params.set('type', filterType)
      if (filterRisk) params.set('risk_level', filterRisk)
      if (filterSearch) params.set('search', filterSearch)
      const { data } = await api.get(`/threat-intel/history?${params}`)
      setIocs(data.items)
      setTotal(data.total)
    } catch {}
    setLoading(false)
  }, [page, filterType, filterRisk, filterSearch])

  useEffect(() => { fetchHistory() }, [fetchHistory])

  const handleDelete = async (id: number) => {
    if (!confirm('Archive this IOC?')) return
    setDeletingId(id)
    try {
      await api.delete(`/threat-intel/ioc/${id}`)
      setIocs((prev) => prev.filter((i) => i.id !== id))
      setTotal((t) => t - 1)
    } catch {}
    setDeletingId(null)
  }

  const handleExport = async (id: number) => {
    setExportingId(id)
    try {
      const resp = await api.get(`/threat-intel/export/${id}`, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `ioc_${id}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch {}
    setExportingId(null)
  }

  const handleView = (ioc: IOCRecord) => {
    router.push(`/threat-intel/lookup?v=${encodeURIComponent(ioc.value)}`)
  }

  const applySearch = (e: React.FormEvent) => {
    e.preventDefault()
    setFilterSearch(searchInput)
    setPage(1)
  }

  const totalPages = Math.ceil(total / PAGE_SIZE) || 1

  return (
    <AppLayout title="SENTINEL / TI History">
      <div className="space-y-4">
        <div>
          <h1 className="text-lg font-bold font-mono text-accent-green flex items-center gap-2">
            <Clock className="w-5 h-5" />
            IOC History
          </h1>
          <p className="text-xs text-text-muted mt-0.5">All previously looked-up IOCs — {total} total</p>
        </div>

        {/* Filters */}
        <div className="sentinel-card">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-text-muted font-mono">
              <Filter className="w-3.5 h-3.5" /> Filters:
            </div>

            {/* Type filter */}
            <select
              value={filterType}
              onChange={(e) => { setFilterType(e.target.value); setPage(1) }}
              className="bg-background border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none font-mono"
            >
              <option value="">All Types</option>
              <option value="ip">IP</option>
              <option value="domain">Domain</option>
              <option value="hash">Hash</option>
              <option value="url">URL</option>
              <option value="email">Email</option>
              <option value="cve">CVE</option>
            </select>

            {/* Risk filter */}
            <select
              value={filterRisk}
              onChange={(e) => { setFilterRisk(e.target.value); setPage(1) }}
              className="bg-background border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none font-mono"
            >
              <option value="">All Risk Levels</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="clean">Clean</option>
            </select>

            {/* Search */}
            <div className="flex gap-1.5 flex-1 min-w-[200px]">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Filter by value..."
                className="sentinel-input text-xs font-mono flex-1 py-1.5"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
                data-1p-ignore
                data-lpignore="true"
                data-bwignore="true"
                data-form-type="other"
                onKeyDown={(e) => { if (e.key === 'Enter') applySearch({ preventDefault: () => {} } as React.FormEvent) }}
              />
              <button type="button" onClick={() => applySearch({ preventDefault: () => {} } as React.FormEvent)} className="flex items-center gap-1 text-xs border border-border rounded px-2 py-1.5 hover:bg-surface font-mono text-text-muted hover:text-text-primary">
                <Search className="w-3.5 h-3.5" />
              </button>
            </div>

            {(filterType || filterRisk || filterSearch) && (
              <button
                onClick={() => { setFilterType(''); setFilterRisk(''); setFilterSearch(''); setSearchInput(''); setPage(1) }}
                className="text-xs text-text-muted hover:text-danger font-mono transition-colors"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>

        {/* Table */}
        <div className="sentinel-card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="sentinel-table">
              <thead>
                <tr>
                  <th>IOC Value</th>
                  <th>Type</th>
                  <th>Risk Score</th>
                  <th>Risk Level</th>
                  <th>Sources</th>
                  <th>Last Seen</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={7} className="text-center py-10 text-text-muted font-mono text-xs">LOADING...</td></tr>
                )}
                {!loading && iocs.length === 0 && (
                  <tr><td colSpan={7} className="text-center py-10 text-text-muted font-mono text-xs">NO IOCs FOUND</td></tr>
                )}
                {iocs.map((ioc) => (
                  <tr
                    key={ioc.id}
                    className="cursor-pointer hover:bg-surface/50 transition-colors"
                    onClick={() => handleView(ioc)}
                  >
                    <td>
                      <code className="text-xs font-mono text-text-primary truncate max-w-[200px] block" title={ioc.value}>
                        {ioc.value}
                      </code>
                    </td>
                    <td><IOCBadge type={ioc.ioc_type} /></td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1 bg-border rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${ioc.risk_score}%`,
                              background: ioc.risk_score >= 75 ? '#ef4444' : ioc.risk_score >= 50 ? '#f59e0b' : ioc.risk_score >= 25 ? '#3b82f6' : '#10b981',
                            }}
                          />
                        </div>
                        <span className={`font-mono text-xs font-bold ${RISK_SCORE_COLOR(ioc.risk_score)}`}>
                          {Math.round(ioc.risk_score)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${RISK_BADGE[ioc.risk_level] ?? RISK_BADGE.clean}`}>
                        {(ioc.risk_level ?? 'clean').toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <div className="flex gap-1 flex-wrap">
                        {(ioc.sources ?? []).slice(0, 3).map((s) => (
                          <span key={s} className="text-[9px] font-mono px-1 py-0.5 bg-surface rounded border border-border text-text-muted">{s}</span>
                        ))}
                        {(ioc.sources ?? []).length > 3 && (
                          <span className="text-[9px] font-mono text-text-muted">+{ioc.sources.length - 3}</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className="text-xs text-text-muted font-mono">{formatRelativeTime(ioc.last_seen)}</span>
                    </td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleView(ioc)}
                          className="p-1.5 text-text-muted hover:text-accent-blue rounded transition-colors"
                          title="View details"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleExport(ioc.id)}
                          disabled={exportingId === ioc.id}
                          className="p-1.5 text-text-muted hover:text-accent-green rounded transition-colors disabled:opacity-50"
                          title="Export CSV"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(ioc.id)}
                          disabled={deletingId === ioc.id}
                          className="p-1.5 text-text-muted hover:text-danger rounded transition-colors disabled:opacity-50"
                          title="Archive"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-border">
              <span className="text-xs text-text-muted font-mono">
                {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30 hover:bg-surface font-mono">
                  Prev
                </button>
                <span className="text-xs font-mono text-text-muted px-1 self-center">{page} / {totalPages}</span>
                <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                  className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30 hover:bg-surface font-mono">
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
