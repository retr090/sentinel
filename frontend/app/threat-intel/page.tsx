'use client'

import { useState, useEffect, useCallback, useRef, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import EnrichmentCards from '@/components/ui/EnrichmentCards'
import ThreatScoreRing from '@/components/ui/ThreatScoreRing'
import IOCBadge from '@/components/ui/IOCBadge'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/lib/utils'
import {
  Search, Copy, Download, FileText, Check, AlertCircle,
  Layers, Play, Clock, CheckCircle, Cpu, Shield,
  Trash2, Eye, Filter,
} from 'lucide-react'

type Tab = 'lookup' | 'history' | 'bulk'

// ─── IOC type detection ───────────────────────────────────────────────────────

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

// ─── Types ────────────────────────────────────────────────────────────────────

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
  created_at: string
}

interface Analysis {
  verdict: string
  category: string
  summary: string
  key_findings: string[]
  recommended_actions: string[]
  confidence: string
  sources_flagged: number
  sources_total: number
  threat_actor?: string | null
  mitre_tactics?: string[]
  generated_by: string
  model?: string
}

interface LookupResult {
  ioc: IOCRecord
  enrichments: Record<string, any>
  risk_score: number
  risk_level: string
  analysis?: Analysis
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

// ─── Analysis Panel ───────────────────────────────────────────────────────────

const VERDICT_STYLES: Record<string, { border: string; bg: string; dot: string; text: string }> = {
  MALICIOUS:    { border: 'border-l-danger',       bg: 'bg-danger/5',       dot: 'bg-danger',       text: 'text-danger' },
  SUSPICIOUS:   { border: 'border-l-orange-500',   bg: 'bg-orange-500/5',   dot: 'bg-orange-500',   text: 'text-orange-400' },
  CLEAN:        { border: 'border-l-accent-green', bg: 'bg-accent-green/5', dot: 'bg-accent-green', text: 'text-accent-green' },
  INCONCLUSIVE: { border: 'border-l-warning',      bg: 'bg-warning/5',      dot: 'bg-warning',      text: 'text-warning' },
}

const CONFIDENCE_STYLES: Record<string, string> = {
  HIGH:   'border-danger/50 text-danger',
  MEDIUM: 'border-warning/50 text-warning',
  LOW:    'border-border text-text-muted',
}

function AnalysisSkeleton() {
  return (
    <div className="sentinel-card border-l-4 border-l-border animate-pulse">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-2.5 h-2.5 rounded-full bg-border/60" />
        <div className="h-3.5 w-28 bg-border/60 rounded" />
        <div className="h-3 w-44 bg-border/40 rounded" />
      </div>
      <div className="h-3 w-full bg-border/40 rounded mb-1.5" />
      <div className="h-3 w-4/5 bg-border/30 rounded mb-4" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-2.5 bg-border/30 rounded" />)}</div>
        <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-2.5 bg-border/30 rounded" />)}</div>
      </div>
    </div>
  )
}

function AnalysisPanel({ analysis }: { analysis?: Analysis }) {
  if (!analysis) return <AnalysisSkeleton />
  const styles = VERDICT_STYLES[analysis.verdict] ?? VERDICT_STYLES.INCONCLUSIVE
  const confStyle = CONFIDENCE_STYLES[analysis.confidence] ?? CONFIDENCE_STYLES.LOW
  return (
    <div className={cn('sentinel-card border-l-4 space-y-3', styles.border, styles.bg)}>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          <div className={cn('w-2.5 h-2.5 rounded-full shrink-0', styles.dot)} />
          <span className={cn('text-sm font-bold font-mono tracking-wider', styles.text)}>{analysis.verdict}</span>
          <span className="text-sm text-text-muted font-mono">— {analysis.category}</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono flex-wrap">
          <span className="text-text-muted">{analysis.sources_flagged}/{analysis.sources_total} sources flagged</span>
          <span className={cn('px-1.5 py-0.5 rounded border', confStyle)}>{analysis.confidence} CONFIDENCE</span>
          <span className="flex items-center gap-1 text-text-muted/60">
            <Cpu className="w-3 h-3" />
            {analysis.generated_by === 'groq_ai' ? `AI · ${analysis.model}` : 'Rule Engine'}
          </span>
        </div>
      </div>
      <p className="text-xs text-text-primary font-mono leading-relaxed">{analysis.summary}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
        <div>
          <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-2">Key Findings</div>
          <ul className="space-y-1.5">
            {analysis.key_findings.map((f, i) => (
              <li key={i} className="flex items-start gap-2 text-[11px] font-mono text-text-primary">
                <span className="text-warning mt-0.5 shrink-0">▸</span>{f}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-2">Recommended Actions</div>
          <ul className="space-y-1.5">
            {analysis.recommended_actions.map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-[11px] font-mono text-text-primary">
                <span className="text-accent-blue mt-0.5 shrink-0">→</span>{a}
              </li>
            ))}
          </ul>
        </div>
      </div>
      {(analysis.mitre_tactics ?? []).length > 0 && (
        <div className="flex items-center gap-2 pt-2 border-t border-border/40 flex-wrap">
          <span className="text-[10px] font-mono text-text-muted">MITRE ATT&CK:</span>
          {analysis.mitre_tactics!.map((t, i) => (
            <span key={i} className="text-[10px] px-1.5 py-0.5 rounded border border-border text-text-muted font-mono">{t}</span>
          ))}
        </div>
      )}
      {analysis.threat_actor && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-text-muted">Threat Actor:</span>
          <span className="text-[10px] font-mono font-bold text-danger">{analysis.threat_actor}</span>
        </div>
      )}
    </div>
  )
}

// ─── IOC Lookup Tab ───────────────────────────────────────────────────────────

function LookupTab({ initialValue, onViewIOC }: { initialValue?: string; onViewIOC?: (v: string) => void }) {
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

  useEffect(() => { setDetectedType(detectType(searchValue)) }, [searchValue])

  // Expose a way to trigger lookup from outside (parent switches tab + sets value)
  useEffect(() => {
    if (initialValue && initialValue !== searchValue) {
      setSearchValue(initialValue)
      doLookup(initialValue)
    }
  }, [initialValue]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSaveNote = async () => {
    if (!result?.ioc?.id) return
    setSavingNote(true)
    try {
      await api.patch(`/threat-intel/ioc/${result.ioc.id}/notes`, { notes: noteText })
      setNoteSaved(true)
      setResult(r => r ? { ...r, ioc: { ...r.ioc, analyst_notes: noteText } } : r)
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
      const a = document.createElement('a'); a.href = url; a.download = `ioc_${result.ioc.id}.csv`; a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  return (
    <div className="space-y-4">
      <div className="sentinel-card">
        <div className="flex gap-2 items-center">
          <div className="relative flex-1">
            <input
              type="text"
              value={searchValue}
              onChange={e => setSearchValue(e.target.value)}
              placeholder="IP, domain, MD5/SHA256, URL, email, CVE, ASN..."
              className="sentinel-input font-mono w-full pr-28"
              autoFocus
              autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
              data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other"
              onKeyDown={e => { if (e.key === 'Enter') doLookup(searchValue) }}
            />
            {detectedType && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-accent-blue/10 text-accent-blue border border-accent-blue/30 pointer-events-none">
                {TYPE_BADGE_LABELS[detectedType] ?? detectedType.toUpperCase()}
              </span>
            )}
          </div>
          <button
            onClick={() => doLookup(searchValue)}
            disabled={isSearching || !searchValue.trim()}
            className="flex items-center gap-2 bg-accent-green text-background px-4 py-2 rounded text-sm font-bold hover:bg-accent-green/90 disabled:opacity-50 transition-colors whitespace-nowrap"
          >
            <Search className="w-4 h-4" />
            {isSearching ? 'Searching...' : 'Enrich'}
          </button>
        </div>
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <span className="text-[10px] text-text-muted font-mono">Try:</span>
          {['80.94.92.167', '1.1.1.1', 'google.com', '44d88612fea8a8f36de82e1278abb02f', 'CVE-2021-44228'].map(ex => (
            <button key={ex} onClick={() => { setSearchValue(ex); doLookup(ex) }}
              className="text-[10px] font-mono text-accent-blue hover:text-accent-blue/80 transition-colors">{ex}</button>
          ))}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-danger text-xs bg-danger/10 border border-danger/20 rounded px-3 py-2 font-mono">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" /> {error}
        </div>
      )}

      {!isSearching && !result && !error && (
        <div className="sentinel-card text-center py-16">
          <div className="w-16 h-16 rounded-full border-2 border-dashed border-border/60 flex items-center justify-center mx-auto mb-4">
            <Search className="w-7 h-7 text-text-muted/50" />
          </div>
          <p className="text-sm text-text-muted font-mono">Enter an IOC above to begin enrichment</p>
          <p className="text-xs text-text-muted/50 font-mono mt-1">IP · Domain · MD5 · SHA1 · SHA256 · URL · Email · CVE · ASN</p>
        </div>
      )}

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

      {result && (
        <>
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
                <button onClick={handleCopyIOC}
                  className="flex items-center gap-1.5 text-xs border border-border rounded px-3 py-1.5 hover:bg-surface transition-colors font-mono text-text-muted hover:text-text-primary">
                  {copied ? <Check className="w-3.5 h-3.5 text-accent-green" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied' : 'Copy IOC'}
                </button>
                <button onClick={handleExport}
                  className="flex items-center gap-1.5 text-xs border border-border rounded px-3 py-1.5 hover:bg-surface transition-colors font-mono text-text-muted hover:text-text-primary">
                  <Download className="w-3.5 h-3.5" /> Export CSV
                </button>
              </div>
            </div>
          </div>

          <AnalysisPanel analysis={result.analysis} />
          <EnrichmentCards enrichments={result.enrichments} iocType={result.ioc.ioc_type} />

          <div className="sentinel-card space-y-3">
            <h3 className="text-xs font-mono font-bold text-text-muted uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" /> Analyst Notes
            </h3>
            <textarea value={noteText} onChange={e => setNoteText(e.target.value)} rows={3}
              className="sentinel-input w-full resize-none font-mono text-xs"
              placeholder="Add notes for this IOC (stored in database)..."
              autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
              data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other" />
            <div className="flex justify-end">
              <button onClick={handleSaveNote} disabled={savingNote}
                className="flex items-center gap-2 bg-accent-green text-background font-bold text-xs px-3 py-1.5 rounded hover:bg-accent-green/90 disabled:opacity-50 transition-colors">
                {noteSaved ? <Check className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />}
                {noteSaved ? 'Saved!' : savingNote ? 'Saving...' : 'Save Note'}
              </button>
            </div>
          </div>
        </>
      )}

      {isSearching && <><AnalysisSkeleton /><EnrichmentCards enrichments={{}} loading iocType={detectedType} /></>}
    </div>
  )
}

// ─── TI History Tab ───────────────────────────────────────────────────────────

function HistoryTab({ onViewIOC }: { onViewIOC: (v: string) => void }) {
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
      setIocs(data.items); setTotal(data.total)
    } catch {}
    setLoading(false)
  }, [page, filterType, filterRisk, filterSearch])

  useEffect(() => { fetchHistory() }, [fetchHistory])

  const handleDelete = async (id: number) => {
    if (!confirm('Archive this IOC?')) return
    setDeletingId(id)
    try {
      await api.delete(`/threat-intel/ioc/${id}`)
      setIocs(prev => prev.filter(i => i.id !== id)); setTotal(t => t - 1)
    } catch {}
    setDeletingId(null)
  }

  const handleExport = async (id: number) => {
    setExportingId(id)
    try {
      const resp = await api.get(`/threat-intel/export/${id}`, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a'); a.href = url; a.download = `ioc_${id}.csv`; a.click()
      URL.revokeObjectURL(url)
    } catch {}
    setExportingId(null)
  }

  const totalPages = Math.ceil(total / PAGE_SIZE) || 1

  return (
    <div className="space-y-4">
      <div className="sentinel-card">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-text-muted font-mono">
            <Filter className="w-3.5 h-3.5" /> Filters:
          </div>
          <select value={filterType} onChange={e => { setFilterType(e.target.value); setPage(1) }}
            className="bg-background border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none font-mono">
            <option value="">All Types</option>
            <option value="ip">IP</option>
            <option value="domain">Domain</option>
            <option value="hash">Hash</option>
            <option value="url">URL</option>
            <option value="email">Email</option>
            <option value="cve">CVE</option>
          </select>
          <select value={filterRisk} onChange={e => { setFilterRisk(e.target.value); setPage(1) }}
            className="bg-background border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none font-mono">
            <option value="">All Risk Levels</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="clean">Clean</option>
          </select>
          <div className="flex gap-1.5 flex-1 min-w-[200px]">
            <input type="text" value={searchInput} onChange={e => setSearchInput(e.target.value)}
              placeholder="Filter by value..." className="sentinel-input text-xs font-mono flex-1 py-1.5"
              autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
              data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other"
              onKeyDown={e => { if (e.key === 'Enter') { setFilterSearch(searchInput); setPage(1) } }} />
            <button onClick={() => { setFilterSearch(searchInput); setPage(1) }}
              className="flex items-center gap-1 text-xs border border-border rounded px-2 py-1.5 hover:bg-surface font-mono text-text-muted hover:text-text-primary">
              <Search className="w-3.5 h-3.5" />
            </button>
          </div>
          {(filterType || filterRisk || filterSearch) && (
            <button onClick={() => { setFilterType(''); setFilterRisk(''); setFilterSearch(''); setSearchInput(''); setPage(1) }}
              className="text-xs text-text-muted hover:text-danger font-mono transition-colors">
              Clear filters
            </button>
          )}
        </div>
      </div>

      <div className="sentinel-card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="sentinel-table">
            <thead>
              <tr>
                <th>IOC Value</th><th>Type</th><th>Risk Score</th><th>Risk Level</th>
                <th>Sources</th><th>Last Seen</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={7} className="text-center py-10 text-text-muted font-mono text-xs">LOADING...</td></tr>}
              {!loading && iocs.length === 0 && <tr><td colSpan={7} className="text-center py-10 text-text-muted font-mono text-xs">NO IOCs FOUND</td></tr>}
              {iocs.map(ioc => (
                <tr key={ioc.id} className="cursor-pointer hover:bg-surface/50 transition-colors" onClick={() => onViewIOC(ioc.value)}>
                  <td><code className="text-xs font-mono text-text-primary truncate max-w-[200px] block" title={ioc.value}>{ioc.value}</code></td>
                  <td><IOCBadge type={ioc.ioc_type} /></td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="w-12 h-1 bg-border rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{
                          width: `${ioc.risk_score}%`,
                          background: ioc.risk_score >= 75 ? '#ef4444' : ioc.risk_score >= 50 ? '#f59e0b' : ioc.risk_score >= 25 ? '#3b82f6' : '#10b981',
                        }} />
                      </div>
                      <span className={cn('font-mono text-xs font-bold',
                        ioc.risk_score >= 75 ? 'text-danger' : ioc.risk_score >= 50 ? 'text-warning' : ioc.risk_score >= 25 ? 'text-blue-400' : 'text-accent-green')}>
                        {Math.round(ioc.risk_score)}
                      </span>
                    </div>
                  </td>
                  <td>
                    <span className={cn('text-[10px] font-mono font-bold px-2 py-0.5 rounded border', RISK_CLASSES[ioc.risk_level] ?? RISK_CLASSES.clean)}>
                      {(ioc.risk_level ?? 'clean').toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <div className="flex gap-1 flex-wrap">
                      {(ioc.sources ?? []).slice(0, 3).map(s => (
                        <span key={s} className="text-[9px] font-mono px-1 py-0.5 bg-surface rounded border border-border text-text-muted">{s}</span>
                      ))}
                      {(ioc.sources ?? []).length > 3 && <span className="text-[9px] font-mono text-text-muted">+{ioc.sources.length - 3}</span>}
                    </div>
                  </td>
                  <td><span className="text-xs text-text-muted font-mono">{formatRelativeTime(ioc.last_seen)}</span></td>
                  <td onClick={e => e.stopPropagation()}>
                    <div className="flex items-center gap-1">
                      <button onClick={() => onViewIOC(ioc.value)} className="p-1.5 text-text-muted hover:text-accent-blue rounded transition-colors" title="View details">
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => handleExport(ioc.id)} disabled={exportingId === ioc.id}
                        className="p-1.5 text-text-muted hover:text-accent-green rounded transition-colors disabled:opacity-50" title="Export CSV">
                        <Download className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => handleDelete(ioc.id)} disabled={deletingId === ioc.id}
                        className="p-1.5 text-text-muted hover:text-danger rounded transition-colors disabled:opacity-50" title="Archive">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border">
            <span className="text-xs text-text-muted font-mono">{(page-1)*PAGE_SIZE+1}–{Math.min(page*PAGE_SIZE,total)} of {total}</span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1}
                className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30 hover:bg-surface font-mono">Prev</button>
              <span className="text-xs font-mono text-text-muted px-1 self-center">{page} / {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages, p+1))} disabled={page>=totalPages}
                className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30 hover:bg-surface font-mono">Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Bulk Lookup Tab ──────────────────────────────────────────────────────────

function BulkTab({ onViewIOC }: { onViewIOC: (v: string) => void }) {
  const [inputText, setInputText] = useState('')
  const [parsedLines, setParsedLines] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [job, setJob] = useState<BulkJob | null>(null)
  const [error, setError] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    setParsedLines(inputText.split('\n').map(l => l.trim()).filter(Boolean).slice(0, 50))
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

  const handleSubmit = async () => {
    if (!parsedLines.length) return
    setSubmitting(true); setError(''); setJob(null)
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
    const ids = job.results.filter(r => r.id).map(r => r.id!)
    if (!ids.length) return
    try {
      const resp = await api.post('/threat-intel/export/bulk', { ids }, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a'); a.href = url; a.download = `bulk_${job.id}.csv`; a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  const progressPct = job ? Math.round((job.processed / Math.max(job.total, 1)) * 100) : 0

  if (!job) return (
    <div className="space-y-4">
      <div className="sentinel-card space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-mono text-text-muted uppercase tracking-wider">IOC List — one per line</label>
          <span className={cn('text-xs font-mono', parsedLines.length >= 50 ? 'text-danger' : 'text-text-muted')}>
            {parsedLines.length} / 50
          </span>
        </div>
        <textarea value={inputText} onChange={e => setInputText(e.target.value)} rows={12}
          className="sentinel-input w-full resize-none font-mono text-xs"
          placeholder={'Paste IOCs here, one per line:\n1.2.3.4\nevil.com\n44d88612fea8a8f36de82e1278abb02f'}
          autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
          data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other" />
        {parsedLines.length > 0 && (
          <div>
            <div className="text-[10px] font-mono text-text-muted mb-1.5">{parsedLines.length} IOCs detected — preview:</div>
            <div className="bg-background/60 rounded border border-border p-2 max-h-36 overflow-y-auto space-y-1">
              {parsedLines.map((line, i) => (
                <div key={i} className="flex items-center gap-2 text-xs font-mono">
                  <span className="text-text-muted w-5 text-right shrink-0 text-[10px]">{i+1}</span>
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
          <button onClick={handleSubmit} disabled={submitting || !parsedLines.length}
            className="flex items-center gap-2 bg-accent-green text-background font-bold text-sm px-4 py-2 rounded hover:bg-accent-green/90 disabled:opacity-50 transition-colors">
            <Play className="w-4 h-4" />
            {submitting ? 'Starting...' : `Run Bulk Lookup (${parsedLines.length} IOCs)`}
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="sentinel-card space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {job.status === 'completed' ? <CheckCircle className="w-4 h-4 text-accent-green" />
              : job.status === 'failed' ? <AlertCircle className="w-4 h-4 text-danger" />
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
              <button onClick={handleExportAll}
                className="flex items-center gap-1.5 text-xs border border-border rounded px-3 py-1.5 hover:bg-surface font-mono text-text-muted hover:text-text-primary transition-colors">
                <Download className="w-3.5 h-3.5" /> Export All CSV
              </button>
            )}
            <button onClick={() => { setJob(null); setInputText('') }}
              className="text-xs text-text-muted hover:text-text-primary font-mono transition-colors">
              New Job
            </button>
          </div>
        </div>
        <div className="space-y-1">
          <div className="flex justify-between text-[11px] font-mono text-text-muted">
            <span>{job.processed} of {job.total} processed</span><span>{progressPct}%</span>
          </div>
          <div className="h-1.5 bg-border rounded-full overflow-hidden">
            <div className={cn('h-full rounded-full transition-all duration-500',
              job.status === 'failed' ? 'bg-danger' : job.status === 'completed' ? 'bg-accent-green' : 'bg-accent-blue')}
              style={{ width: `${progressPct}%` }} />
          </div>
        </div>
      </div>

      {(job.results ?? []).length > 0 && (
        <div className="sentinel-card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-border">
            <span className="text-xs font-mono font-bold text-text-muted uppercase tracking-wider">Results ({job.results.length})</span>
          </div>
          <div className="overflow-x-auto">
            <table className="sentinel-table">
              <thead><tr><th>IOC</th><th>Type</th><th>Score</th><th>Level</th><th>Action</th></tr></thead>
              <tbody>
                {job.results.map((r, i) => (
                  <tr key={i} className={r.error ? 'opacity-50' : ''}>
                    <td>
                      <code className="text-xs font-mono text-text-primary truncate max-w-[240px] block" title={r.value}>{r.value}</code>
                      {r.error && <span className="text-[10px] text-danger font-mono">{r.error}</span>}
                    </td>
                    <td>{r.ioc_type ? <IOCBadge type={r.ioc_type} /> : <span className="text-xs text-text-muted font-mono">—</span>}</td>
                    <td>
                      {r.risk_score !== undefined ? (
                        <span className={cn('font-mono text-xs font-bold',
                          r.risk_score >= 75 ? 'text-danger' : r.risk_score >= 50 ? 'text-warning' : r.risk_score >= 25 ? 'text-blue-400' : 'text-accent-green')}>
                          {Math.round(r.risk_score)}
                        </span>
                      ) : <span className="text-xs text-text-muted font-mono">—</span>}
                    </td>
                    <td>
                      {r.risk_level ? (
                        <span className={cn('text-[10px] font-mono font-bold px-2 py-0.5 rounded border', RISK_CLASSES[r.risk_level] ?? RISK_CLASSES.clean)}>
                          {r.risk_level.toUpperCase()}
                        </span>
                      ) : <span className="text-xs text-text-muted font-mono">—</span>}
                    </td>
                    <td>
                      {r.id && (
                        <button onClick={() => onViewIOC(r.value)}
                          className="text-[10px] font-mono text-accent-blue hover:text-accent-blue/80 transition-colors">
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
  )
}

// ─── Page Shell ───────────────────────────────────────────────────────────────

const TABS: { id: Tab; label: string; icon: typeof Search }[] = [
  { id: 'lookup',  label: 'IOC Lookup',  icon: Search },
  { id: 'history', label: 'TI History',  icon: Clock },
  { id: 'bulk',    label: 'Bulk Search', icon: Layers },
]

function ThreatIntelInner() {
  const searchParams = useSearchParams()
  const initialTab = (searchParams.get('tab') as Tab) || 'lookup'
  const initialValue = searchParams.get('v') ?? undefined

  const [activeTab, setActiveTab] = useState<Tab>(initialTab)
  const [lookupValue, setLookupValue] = useState<string | undefined>(initialValue)

  const handleViewIOC = (value: string) => {
    setLookupValue(value)
    setActiveTab('lookup')
  }

  return (
    <div className="space-y-4 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-lg font-bold font-mono flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent-green" /> Threat Intelligence
          </h1>
          <p className="text-xs text-text-muted mt-0.5">IOC enrichment, history, and bulk analysis across multiple threat intel sources</p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 p-1 bg-background/50 rounded border border-border/50 w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setActiveTab(id)}
            className={cn(
              'flex items-center gap-1.5 px-4 py-1.5 text-xs font-mono rounded transition-colors',
              activeTab === id
                ? 'bg-accent-green/20 text-accent-green border border-accent-green/30'
                : 'text-text-muted hover:text-text-primary',
            )}>
            <Icon className="w-3.5 h-3.5" />{label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'lookup'  && <LookupTab initialValue={lookupValue} />}
      {activeTab === 'history' && <HistoryTab onViewIOC={handleViewIOC} />}
      {activeTab === 'bulk'    && <BulkTab onViewIOC={handleViewIOC} />}
    </div>
  )
}

export default function ThreatIntelPage() {
  return (
    <AppLayout title="SENTINEL / Threat Intelligence">
      <Suspense fallback={<div className="text-text-muted font-mono text-xs p-4">Loading...</div>}>
        <ThreatIntelInner />
      </Suspense>
    </AppLayout>
  )
}
