'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import EnrichmentCards from '@/components/ui/EnrichmentCards'
import ThreatScoreRing from '@/components/ui/ThreatScoreRing'
import IOCBadge from '@/components/ui/IOCBadge'
import { Search, Copy, Download, FileText, Check, AlertCircle } from 'lucide-react'
import { formatRelativeTime } from '@/lib/utils'

// ─── IOC type detection (mirrors backend) ───

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
  ip: 'IPv4',
  hash_md5: 'MD5',
  hash_sha1: 'SHA1',
  hash_sha256: 'SHA256',
  url: 'URL',
  email: 'Email',
  cve: 'CVE',
  asn: 'ASN',
  domain: 'Domain',
}

const RISK_CLASSES: Record<string, string> = {
  critical: 'bg-danger/20 text-danger border border-danger/40',
  high: 'bg-warning/20 text-warning border border-warning/40',
  medium: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  low: 'bg-accent-green/10 text-accent-green border border-accent-green/30',
  clean: 'bg-accent-green/10 text-accent-green border border-accent-green/30',
}

// ─── types ──────────────────────────────────

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

interface LookupResult {
  ioc: IOCRecord
  enrichments: Record<string, any>
  risk_score: number
  risk_level: string
}

// ─── inner component (needs useSearchParams) ─

function LookupInner() {
  const searchParams = useSearchParams()
  const router = useRouter()

  const [searchValue, setSearchValue] = useState('')
  const [detectedType, setDetectedType] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [result, setResult] = useState<LookupResult | null>(null)
  const [error, setError] = useState('')
  const [noteText, setNoteText] = useState('')
  const [savingNote, setSavingNote] = useState(false)
  const [noteSaved, setNoteSaved] = useState(false)
  const [copied, setCopied] = useState(false)

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

  // Auto-search if ?v=... or ?ioc_id=... in URL
  useEffect(() => {
    const v = searchParams.get('v')
    if (v) {
      setSearchValue(v)
      doLookup(v)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-detect type as user types
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

  return (
    <div className="space-y-4 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-lg font-bold font-mono text-accent-green">IOC LOOKUP</h1>
        <p className="text-xs text-text-muted mt-0.5">Enrich any IP, domain, hash, URL, email or CVE against multiple threat intelligence sources</p>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch} className="sentinel-card">
        <div className="flex gap-2 items-center">
          <div className="relative flex-1">
            <input
              type="text"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              placeholder="Search IP, domain, hash (MD5/SHA256), URL, email, CVE..."
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
            {isSearching ? 'Searching...' : 'Search'}
          </button>
        </div>

        {/* Example IOCs */}
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <span className="text-[10px] text-text-muted font-mono">Try:</span>
          {['1.1.1.1', 'evil.com', '44d88612fea8a8f36de82e1278abb02f', 'CVE-2021-44228'].map((ex) => (
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

      {/* Results */}
      {(isSearching || result) && (
        <>
          {/* Summary bar */}
          <div className="sentinel-card">
            {isSearching ? (
              <div className="flex items-center gap-4 animate-pulse">
                <div className="w-20 h-20 rounded-full bg-border/40 shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-48 bg-border/40 rounded" />
                  <div className="h-3 w-32 bg-border/30 rounded" />
                  <div className="h-3 w-24 bg-border/20 rounded" />
                </div>
              </div>
            ) : result && (
              <div className="flex items-start gap-4 flex-wrap">
                <ThreatScoreRing score={Math.round(result.risk_score)} size={80} />
                <div className="flex-1 min-w-0 space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <code className="text-sm font-mono text-text-primary font-bold break-all">{result.ioc.value}</code>
                    <IOCBadge type={result.ioc.ioc_type} />
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${RISK_CLASSES[result.risk_level] ?? RISK_CLASSES.clean}`}>
                      {result.risk_level.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-[11px] text-text-muted font-mono">
                    <span>First seen: {formatRelativeTime(result.ioc.first_seen)}</span>
                    <span>Last seen: {formatRelativeTime(result.ioc.last_seen)}</span>
                    <span>{result.ioc.sources.length} source{result.ioc.sources.length !== 1 ? 's' : ''} checked</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
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
            )}
          </div>

          {/* Source cards */}
          <EnrichmentCards
            enrichments={result?.enrichments ?? {}}
            loading={isSearching}
            iocType={isSearching ? detectedType : result?.ioc?.ioc_type}
          />

          {/* Analyst notes */}
          {result && (
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
          )}
        </>
      )}

      {/* Empty state */}
      {!isSearching && !result && !error && (
        <div className="sentinel-card text-center py-12">
          <Search className="w-8 h-8 text-text-muted mx-auto mb-3" />
          <p className="text-sm text-text-muted font-mono">Enter an IOC above to begin enrichment</p>
          <p className="text-xs text-text-muted/60 font-mono mt-1">Supports: IP, Domain, MD5/SHA1/SHA256, URL, Email, CVE</p>
        </div>
      )}
    </div>
  )
}

export default function LookupPage() {
  return (
    <AppLayout title="SENTINEL / IOC Lookup">
      <Suspense fallback={<div className="text-text-muted font-mono text-xs p-4">Loading...</div>}>
        <LookupInner />
      </Suspense>
    </AppLayout>
  )
}
