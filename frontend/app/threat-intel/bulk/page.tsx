'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import IOCBadge from '@/components/ui/IOCBadge'
import { Layers, Play, Download, AlertCircle, CheckCircle, Clock } from 'lucide-react'

// ─── IOC type detection (mirrors lookup page) ─

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
  return 'unknown'
}

const RISK_BADGE: Record<string, string> = {
  critical: 'bg-danger/20 text-danger border border-danger/40',
  high: 'bg-warning/20 text-warning border border-warning/40',
  medium: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  low: 'bg-accent-green/10 text-accent-green border border-accent-green/30',
  clean: 'bg-border/60 text-text-muted border border-border',
}

interface BulkResult {
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
  results: BulkResult[]
  created_at: string
}

export default function BulkLookupPage() {
  const router = useRouter()
  const [inputText, setInputText] = useState('')
  const [parsedLines, setParsedLines] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [job, setJob] = useState<BulkJob | null>(null)
  const [error, setError] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Parse textarea input
  useEffect(() => {
    const lines = inputText
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.length > 0)
      .slice(0, 50)
    setParsedLines(lines)
  }, [inputText])

  // Poll job status
  useEffect(() => {
    if (!job || job.status === 'completed' || job.status === 'failed') {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
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

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [job?.id, job?.status])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (parsedLines.length === 0) return
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
      a.download = `bulk_export_${job.id}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  const progressPct = job ? Math.round((job.processed / Math.max(job.total, 1)) * 100) : 0

  return (
    <AppLayout title="SENTINEL / Bulk IOC Lookup">
      <div className="space-y-4 max-w-5xl mx-auto">
        <div>
          <h1 className="text-lg font-bold font-mono text-accent-green flex items-center gap-2">
            <Layers className="w-5 h-5" />
            Bulk IOC Lookup
          </h1>
          <p className="text-xs text-text-muted mt-0.5">Lookup up to 50 IOCs at once — one per line</p>
        </div>

        {/* Input form */}
        {!job && (
          <div className="sentinel-card space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-mono text-text-muted uppercase tracking-wider">IOC List</label>
              <span className={`text-xs font-mono ${parsedLines.length >= 50 ? 'text-danger' : 'text-text-muted'}`}>
                {parsedLines.length} / 50 IOCs
              </span>
            </div>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              rows={12}
              className="sentinel-input w-full resize-none font-mono text-xs"
              placeholder={'Paste IOCs here, one per line:\n1.2.3.4\nevil.com\n44d88612fea8a8f36de82e1278abb02f\nhttps://malware.example.com/payload'}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck={false}
              data-1p-ignore
              data-lpignore="true"
              data-bwignore="true"
              data-form-type="other"
            />

            {/* Preview list */}
            {parsedLines.length > 0 && (
              <div>
                <div className="text-[10px] font-mono text-text-muted mb-2">Preview ({parsedLines.length} IOCs detected):</div>
                <div className="bg-background/60 rounded border border-border p-2 max-h-40 overflow-y-auto space-y-1">
                  {parsedLines.map((line, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs font-mono">
                      <span className="text-text-muted w-5 text-right shrink-0">{i + 1}</span>
                      <IOCBadge type={detectType(line)} />
                      <code className="text-text-primary truncate">{line}</code>
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
                type="button"
                onClick={() => handleSubmit({ preventDefault: () => {} } as React.FormEvent)}
                disabled={submitting || parsedLines.length === 0}
                className="flex items-center gap-2 bg-accent-green text-background font-bold text-sm px-4 py-2 rounded hover:bg-accent-green/90 disabled:opacity-50 transition-colors"
              >
                <Play className="w-4 h-4" />
                {submitting ? 'Starting...' : `Start Lookup (${parsedLines.length} IOCs)`}
              </button>
            </div>
          </div>
        )}

        {/* Job status */}
        {job && (
          <div className="space-y-4">
            {/* Progress card */}
            <div className="sentinel-card space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {job.status === 'completed' ? (
                    <CheckCircle className="w-4 h-4 text-accent-green" />
                  ) : job.status === 'failed' ? (
                    <AlertCircle className="w-4 h-4 text-danger" />
                  ) : (
                    <Clock className="w-4 h-4 text-warning animate-pulse" />
                  )}
                  <span className="text-sm font-mono font-bold">
                    {job.status === 'completed' ? 'Lookup Complete' :
                     job.status === 'failed' ? 'Job Failed' :
                     job.status === 'running' ? `Processing ${job.processed}/${job.total} IOCs...` :
                     'Job queued...'}
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
                    onClick={() => { setJob(null); setInputText(''); setParsedLines([]) }}
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
                <div className="h-2 bg-border rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      job.status === 'failed' ? 'bg-danger' :
                      job.status === 'completed' ? 'bg-accent-green' : 'bg-accent-blue'
                    }`}
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
                        <th>IOC Value</th>
                        <th>Type</th>
                        <th>Risk Score</th>
                        <th>Risk Level</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {job.results.map((r, i) => (
                        <tr key={i} className={r.error ? 'opacity-50' : ''}>
                          <td>
                            <code className="text-xs font-mono text-text-primary truncate max-w-[250px] block" title={r.value}>
                              {r.value}
                            </code>
                          </td>
                          <td>
                            {r.ioc_type ? <IOCBadge type={r.ioc_type} /> : <span className="text-xs text-text-muted font-mono">—</span>}
                          </td>
                          <td>
                            {r.risk_score !== undefined ? (
                              <span className={`font-mono text-xs font-bold ${
                                r.risk_score >= 75 ? 'text-danger' :
                                r.risk_score >= 50 ? 'text-warning' :
                                r.risk_score >= 25 ? 'text-blue-400' : 'text-accent-green'
                              }`}>
                                {Math.round(r.risk_score)}
                              </span>
                            ) : r.error ? (
                              <span className="text-xs text-danger font-mono">Error</span>
                            ) : <span className="text-xs text-text-muted font-mono">—</span>}
                          </td>
                          <td>
                            {r.risk_level ? (
                              <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${RISK_BADGE[r.risk_level] ?? RISK_BADGE.clean}`}>
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

            {/* Still running placeholder */}
            {(job.status === 'running' || job.status === 'pending') && job.processed < job.total && (
              <div className="sentinel-card text-center py-6">
                <Clock className="w-6 h-6 text-text-muted mx-auto mb-2 animate-spin" />
                <p className="text-xs text-text-muted font-mono">Processing... results appear as they complete</p>
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
