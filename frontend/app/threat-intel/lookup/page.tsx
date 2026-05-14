'use client'

import { useState, useEffect, useCallback, useRef, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import EnrichmentCards from '@/components/ui/EnrichmentCards'
import ThreatScoreRing from '@/components/ui/ThreatScoreRing'
import IOCBadge from '@/components/ui/IOCBadge'
import { Search, Copy, Download, FileText, Check, AlertCircle, Layers, Play, Clock, CheckCircle } from 'lucide-react'
import { formatRelativeTime } from '@/lib/utils'
import { cn } from '@/lib/utils'

// ─── IOC type detection ──────────────────────

function detectType(raw: string): string {
  const v = raw.trim()
  if (!v) return ''
  if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(v)) return 'ip'
  if (/^[a-fA-F0-9]{32}$/.test(v)) return 'hash_md5'
  if (/^[a-fA-F0-9]{40}$/.test(v)) return 'hash_sha1'
  if (/^[a-fA-F0-9]{64}$/.test(v)) return 'hash_sha256'
  if (/^https?:\/\/|^ftp:\/\//.test(v)) return 'url'
  if (/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) return 'email'
  if (/^CVE-\d{4}-\d+$/i.test(v)) return 'cve'
  if (/^AS\d+$/i.test(v)) return 'asn'
  if (v.length >= 3 && !v.includes(' ') && v.includes('.')) return 'domain'
  return ''
}

const TYPE_BADGE_LABELS: Record<string, string> = {
  ip: 'IPv4', hash_md5: 'MD5', hash_sha1: 'SHA1', hash_sha256: 'SHA256',
  url: 'URL', email: 'Email', cve: 'CVE', asn: 'ASN', domain: 'Domain',
}

const RISK_CLASSES: Record<string, string> = {
  critical: 'bg-danger/20 text-danger border border-danger/40',
  high: 'bg-warning/20 text-warning border border-warning/40',
  medium: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  low: 'bg-accent-green/10 text-accent-green border border-accent-green/30',
  clean: 'bg-border/60 text-text-muted border border-border',
}

const RISK_BADGE: Record<string, string> = RISK_CLASSES

// ─── Types ───────────────────────────────────

interface IOCRecord {
  id: number
  value: string
  ioc_type: string
  risk_score: number
  risk_level: string
  sources: string[]
  tags: string[]
  analyst_notes?: string
  first_seen: string
  last_seen: string
}

interface LookupResult {
  ioc: IOCRecord
  enrichments: Record<string, any>
  risk_score: number
  risk_level: string
}

interface BulkJobResult {
  id?: number
  value: string
  ioc_type?: string
  risk_score?: number
  risk_level?: string
  error?: string
}

interface BulkJob {
  id: number
  status: string
  total: number
  processed: number
  results: BulkJobResult[]
}

// ─── Single Lookup Tab ───────────────────────

function SingleLookupTab({ initialValue }: { initialValue?: string }) {
  const [searchValue, setSearchValue] = useState(initialValue ?? '')
  const [detectedType, setDetectedType] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [result, setResult] = useState<LookupResult | null>(null)
  const [error, setError] = useState('')
  const [noteText, setNoteText] = useState('')
  const [savingNote, setSavingNote] = useState(false)
  const [noteSaved, setNoteSaved] = useState(false)
  const [copied, setCopied] = useState(false)
  const didInit = useRef(false)

  const doLookup = useCallback(async (value: string) => {
    if (!value.trim()) return
    setIsSearching(true)
    setResult(null)
    setError('')
    try {
      const { data } = await api.post('/threat-intel/lookup', { value: value.trim() })
      setResult(data)
      setNoteText(data.ioc?.analyst_notes ?? '')
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Lookup failed')
    }
    setIsSearching(false)
  }, [])

  useEffect(() => {
    if (!didInit.current && initialValue) {
      didInit.current = true
      doLookup(initialValue)
    }
  }, [initialValue, doLookup])

  useEffect(() => {
    setDetectedType(detectType(searchValue))
  }, [searchValue])

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    await doLookup(searchValue)
  }

  const handleSaveNote = async () => {
    if (!result?.ioc?.id) return
    setSavingNote(true)
    try {
      await api.patch(`/threat-intel/ioc/${result.ioc.id}/notes`, { notes: noteText })
      setNoteSaved(true)
      setResult((r) => r ? { ...r, ioc: { ...r.ioc, analyst_notes: noteText } } : r)
      setTimeout(() => setNoteSaved(false), 2000)
    } catch {}
    setSavingNote(false)
  }

  const handleCopyIOC = () => {
    navigator.clipboard.writeText(result?.ioc?.value ?? searchValue.trim())
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const handleExport = async () => {
    if (!result?.ioc?.id) return
    try {
      const resp = await api.get(`/threat-intel/export/${result.ioc.id}`, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `ioc_${result.ioc.id}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  const isEmpty = !isSearching && !result && !error

  return (
    <div className="space-y-4">
      {/* Search bar */}
      <form onSubmit={handleSearch} className="sentinel-card">
        <div className="flex gap-2 items-center">
          <div className="relative flex-1">
            <input
              type="text"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              placeholder="IP, domain, MD5/SHA256, URL, email, CVE, ASN..."
              className="sentinel-input font-mono w-full pr-28"
              autoFocus
            />
            {detectedType && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-accent-blue/10 text-accent-blue border border-accent-blue/30 pointer-events-none">
                {TYPE_BADGE_LABELS[detectedType] ?? detectedType.toUpperCase()}
              </span>
            )}
          </div>
          <button
            type="submit"
            disabled={isSearching || !searchValue.trim()}
            className="flex items-center gap-2 bg-accent-green text-background px-4 py-2 rounded text-sm font-bold hover:bg-accent-green/90 disabled:opacity-50 transition-colors whitespace-nowrap"
          >
            <Search className="w-4 h-4" />
            {isSearching ? 'Searching...' : 'Enrich'}
          </button>
        </div>
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <span className="text-[10px] text-text-muted font-mono">Try:</span>
          {['80.94.92.167', '1.1.1.1', 'google.com', '44d88612fea8a8f36de82e1278abb02f', 'CVE-2021-44228'].map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => { setSearchValue(ex); doLookup(ex) }}
              className="text-[10px] font-mono text-accent-blue hover:text-accent-blue/80 transition-colors"
            >
              {ex}
            </button>
          ))}
        </div>
      </form>

      {error && (
        <div className="flex items-center gap-2 text-danger text-xs bg-danger/10 border border-danger/20 rounded px-3 py-2 font-mono">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" /> {error}
        </div>
      )}

      {/* Empty state */}
      {isEmpty && (
        <div className="sentinel-card text-center py-16">
          <div className="w-16 h-16 rounded-full border-2 border-dashed border-border/60 flex items-center justify-center mx-auto mb-4">
            <Search className="w-7 h-7 text-text-muted/50" />
          </div>
          <p className="text-sm text-text-muted font-mono">Enter an IOC above to begin enrichment</p>
          <p className="text-xs text-text-muted/50 font-mono mt-1">IP · Domain · MD5 · SHA1 · SHA256 · URL · Email · CVE · ASN</p>
        </div>
      )}

      {/* Loading skeleton */}
      {isSearching && (
        <div className="sentinel-card animate-pulse">
          <div className="flex items-center gap-4">
            <div className="w-20 h-20 rounded-full bg-border/40 shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-56 bg-border/40 rounded" />
              <div className="h-3 w-36 bg-border/30 rounded" />
              <div className="h-3 w-24 bg-border/20 rounded" />
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Summary bar */}
          <div className="sentinel-card">
            <div className="flex items-start gap-4 flex-wrap">
              <ThreatScoreRing score={Math.round(result.risk_score)} size={84} />
              <div className="flex-1 min-w-0 space-y-1.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <code className="text-sm font-mono text-text-primary font-bold break-all">{result.ioc.value}</code>
                  <IOCBadge type={result.ioc.ioc_type} />
                  <span className={cn('text-[10px] font-mono font-bold px-2 py-0.5 rounded border', RISK_CLASSES[result.risk_level] ?? RISK_CLASSES.clean)}>
                    {result.risk_level.toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-[11px] text-text-muted font-mono flex-wrap">
                  <span>First seen: {formatRelativeTime(result.ioc.first_seen)}</span>
                  <span>Last seen: {formatRelativeTime(result.ioc.last_seen)}</span>
                  <span>{result.ioc.sources.length} source{result.ioc.sources.length !== 1 ? 's' : ''}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0 flex-wrap">
                <button
                  onClick={handleCopyIOC}
                  className="flex items-center gap-1.5 text-xs border border-border rounded px-3 py-1.5 hover:bg-surface transition-colors font-mono text-text-muted hover:text-text-primary"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-accent-green" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied' : 'Copy IOC'}
                </button>
                <button
                  onClick={handleExport}
                  className="flex items-center gap-1.5 text-xs border border-border rounded px-3 py-1.5 hover:bg-surface transition-colors font-mono text-text-muted hover:text-text-primary"
                >
                  <Download className="w-3.5 h-3.5" />
                  Export CSV
                </button>
              </div>
            </div>
          </div>

          {/* Source cards */}
          <EnrichmentCards
            enrichments={result.enrichments}
            iocType={result.ioc.ioc_type}
          />

          {/* Analyst notes */}
          <div className="sentinel-card space-y-3">
            <h3 className="text-xs font-mono font-bold text-text-muted uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" />
              Analyst Notes
            </h3>
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              rows={3}
              className="sentinel-input w-full resize-none font-mono text-xs"
              placeholder="Add notes for this IOC (stored in database)..."
            />
            <div className="flex justify-end">
              <button
                onClick={handleSaveNote}
                disabled={savingNote}
                className="flex items-center gap-2 bg-accent-green text-background font-bold text-xs px-3 py-1.5 rounded hover:bg-accent-green/90 disabled:opacity-50 transition-colors"
              >
                {noteSaved ? <Check className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />}
                {noteSaved ? 'Saved!' : savingNote ? 'Saving...' : 'Save Note'}
              </button>
            </div>
          </div>
        </>
      )}

      {/* Loading source cards */}
      {isSearching && (
        <EnrichmentCards enrichments={{}} loading iocType={detectedType} />
      )}
    </div>
  )
}

// ─── Bulk Lookup Tab ──────────────────────────

function BulkLookupTab() {
  const router = useRouter()
  const [inputText, setInputText] = useState('')
  const [parsedLines, setParsedLines] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [job, setJob] = useState<BulkJob | null>(null)
  const [error, setError] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    const lines = inputText.split('\n').map((l) => l.trim()).filter(Boolean).slice(0, 50)
    setParsedLines(lines)
  }, [inputText])

  useEffect(() => {
    if (!job || job.status === 'completed' || job.status === 'failed') {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
      return
    }
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get(`/threat-intel/bulk/${job.id}`)
        setJob(data)
        if (data.status === 'completed' || data.status === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current)
        }
      } catch {}
    }, 2000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [job?.id, job?.status])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!parsedLines.length) return
    setSubmitting(true)
    setError('')
    setJob(null)
    try {
      const { data } = await api.post('/threat-intel/bulk', { iocs: parsedLines })
      setJob(data)
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Failed to start bulk job')
    }
    setSubmitting(false)
  }

  const handleExportAll = async () => {
    if (!job?.results) return
    const ids = job.results.filter((r) => r.id).map((r) => r.id!)
    if (!ids.length) return
    try {
      const resp = await api.post('/threat-intel/export/bulk', { ids }, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `bulk_${job.id}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  const progressPct = job ? Math.round((job.processed / Math.max(job.total, 1)) * 100) : 0

  return (
    <div className="space-y-4">
      {!job ? (
        <form onSubmit={handleSubmit} className="sentinel-card space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-mono text-text-muted uppercase tracking-wider">IOC List — one per line</label>
            <span className={cn('text-xs font-mono', parsedLines.length >= 50 ? 'text-danger' : 'text-text-muted')}>
              {parsedLines.length} / 50
            </span>
          </div>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            rows={10}
            className="sentinel-input w-full resize-none font-mono text-xs"
            placeholder={'Paste IOCs here, one per line:\n1.2.3.4\nevil.com\n44d88612fea8a8f36de82e1278abb02f\nhttps://malware.example.com/payload'}
          />

          {parsedLines.length > 0 && (
            <div>
              <div className="text-[10px] font-mono text-text-muted mb-1.5">{parsedLines.length} IOCs detected — preview:</div>
              <div className="bg-background/60 rounded border border-border p-2 max-h-36 overflow-y-auto space-y-1">
                {parsedLines.map((line, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs font-mono">
                    <span className="text-text-muted w-5 text-right shrink-0 text-[10px]">{i + 1}</span>
                    <IOCBadge type={detectType(line)} />
                    <code className="text-text-primary truncate text-[11px]">{line}</code>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 text-danger text-xs bg-danger/10 border border-danger/20 rounded px-3 py-2 font-mono">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" /> {error}
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting || !parsedLines.length}
              className="flex items-center gap-2 bg-accent-green text-background font-bold text-sm px-4 py-2 rounded hover:bg-accent-green/90 disabled:opacity-50 transition-colors"
            >
              <Play className="w-4 h-4" />
              {submitting ? 'Starting...' : `Run Bulk Lookup (${parsedLines.length} IOCs)`}
            </button>
          </div>
        </form>
      ) : (
        <div className="space-y-4">
          {/* Progress */}
          <div className="sentinel-card space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {job.status === 'completed'
                  ? <CheckCircle className="w-4 h-4 text-accent-green" />
                  : job.status === 'failed'
                  ? <AlertCircle className="w-4 h-4 text-danger" />
                  : <Clock className="w-4 h-4 text-warning animate-pulse" />}
                <span className="text-sm font-mono font-bold">
                  {job.status === 'completed' ? `Complete — ${job.results?.length ?? 0} results`
                    : job.status === 'failed' ? 'Job failed'
                    : job.status === 'running' ? `Processing ${job.processed} / ${job.total}...`
                    : 'Job queued...'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {job.status === 'completed' && (
                  <button
                    onClick={handleExportAll}
                    className="flex items-center gap-1.5 text-xs border border-border rounded px-3 py-1.5 hover:bg-surface font-mono text-text-muted hover:text-text-primary transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" /> Export All CSV
                  </button>
                )}
                <button
                  onClick={() => { setJob(null); setInputText('') }}
                  className="text-xs text-text-muted hover:text-text-primary font-mono transition-colors"
                >
                  New Job
                </button>
              </div>
            </div>
            <div className="space-y-1">
              <div className="flex justify-between text-[11px] font-mono text-text-muted">
                <span>{job.processed} of {job.total} processed</span>
                <span>{progressPct}%</span>
              </div>
              <div className="h-1.5 bg-border rounded-full overflow-hidden">
                <div
                  className={cn('h-full rounded-full transition-all duration-500',
                    job.status === 'failed' ? 'bg-danger'
                    : job.status === 'completed' ? 'bg-accent-green'
                    : 'bg-accent-blue')}
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          </div>

          {/* Results table */}
          {(job.results ?? []).length > 0 && (
            <div className="sentinel-card p-0 overflow-hidden">
              <div className="px-4 py-3 border-b border-border">
                <span className="text-xs font-mono font-bold text-text-muted uppercase tracking-wider">
                  Results ({job.results.length})
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="sentinel-table">
                  <thead>
                    <tr>
                      <th>IOC</th>
                      <th>Type</th>
                      <th>Score</th>
                      <th>Level</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {job.results.map((r, i) => (
                      <tr key={i} className={r.error ? 'opacity-50' : ''}>
                        <td>
                          <code className="text-xs font-mono text-text-primary truncate max-w-[240px] block" title={r.value}>
                            {r.value}
                          </code>
                          {r.error && <span className="text-[10px] text-danger font-mono">{r.error}</span>}
                        </td>
                        <td>
                          {r.ioc_type ? <IOCBadge type={r.ioc_type} /> : <span className="text-xs text-text-muted font-mono">—</span>}
                        </td>
                        <td>
                          {r.risk_score !== undefined ? (
                            <span className={cn('font-mono text-xs font-bold',
                              r.risk_score >= 75 ? 'text-danger'
                              : r.risk_score >= 50 ? 'text-warning'
                              : r.risk_score >= 25 ? 'text-blue-400'
                              : 'text-accent-green')}>
                              {Math.round(r.risk_score)}
                            </span>
                          ) : <span className="text-xs text-text-muted font-mono">—</span>}
                        </td>
                        <td>
                          {r.risk_level ? (
                            <span className={cn('text-[10px] font-mono font-bold px-2 py-0.5 rounded border', RISK_BADGE[r.risk_level] ?? RISK_BADGE.clean)}>
                              {r.risk_level.toUpperCase()}
                            </span>
                          ) : <span className="text-xs text-text-muted font-mono">—</span>}
                        </td>
                        <td>
                          {r.id && (
                            <button
                              onClick={() => router.push(`/threat-intel/lookup?v=${encodeURIComponent(r.value)}`)}
                              className="text-[10px] font-mono text-accent-blue hover:text-accent-blue/80 transition-colors"
                            >
                              View →
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Page shell ───────────────────────────────

function LookupPageInner() {
  const searchParams = useSearchParams()
  const [activeTab, setActiveTab] = useState<'single' | 'bulk'>('single')
  const initialValue = searchParams.get('v') ?? undefined

  return (
    <div className="space-y-4 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-lg font-bold font-mono text-accent-green">IOC LOOKUP</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Enrich any IP, domain, hash, URL, email or CVE against multiple threat intelligence sources
          </p>
        </div>
        {/* Tab switcher */}
        <div className="flex gap-1 p-1 bg-background/50 rounded border border-border/50">
          {(['single', 'bulk'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'flex items-center gap-1.5 px-4 py-1.5 text-xs font-mono rounded transition-colors',
                activeTab === tab
                  ? 'bg-accent-green/20 text-accent-green border border-accent-green/30'
                  : 'text-text-muted hover:text-text-primary',
              )}
            >
              {tab === 'single' ? <Search className="w-3.5 h-3.5" /> : <Layers className="w-3.5 h-3.5" />}
              {tab === 'single' ? 'Single Lookup' : 'Bulk Lookup'}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'single'
        ? <SingleLookupTab initialValue={initialValue} />
        : <BulkLookupTab />}
    </div>
  )
}

export default function LookupPage() {
  return (
    <AppLayout title="SENTINEL / IOC Lookup">
      <Suspense fallback={<div className="text-text-muted font-mono text-xs p-4">Loading...</div>}>
        <LookupPageInner />
      </Suspense>
    </AppLayout>
  )
}
