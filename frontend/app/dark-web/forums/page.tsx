'use client'
import { useState, useEffect, useCallback, useRef } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Forum {
  forum_id: string
  forum_name: string
  forum_url: string
  username: string | null
  forum_software: string | null
  auto_login: boolean
  is_active: boolean
  has_password: boolean
  has_cookies: boolean
  login_attempts: number
  last_successful_login: string | null
  last_used: string | null
  notes: string | null
}

interface AiAnalysis {
  is_breach: boolean
  confidence: number
  data_types: string[]
  record_count: string | null
  summary: string
}

interface Mention {
  id: string
  title: string
  source: string
  source_url: string | null
  keyword_matched: string
  severity: string
  category: string | null
  snippet: string | null
  threat_actor: string | null
  is_reviewed: boolean
  analyst_notes: string | null
  discovered_at: string
  raw_data?: { ai_analysis?: AiAnalysis }
}

interface MentionStats {
  total: number
  critical_high: number
  unreviewed: number
  by_source: Record<string, number>
}

interface Scan {
  id: string
  scan_type: string
  source: string | null
  status: string
  keywords_scanned: number
  mentions_found: number
  new_mentions: number
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  created_at: string
}

// ── Severity badge ────────────────────────────────────────────────────────────

const SEV: Record<string, string> = {
  CRITICAL: 'bg-red-950 text-red-400 border-red-900',
  HIGH: 'bg-orange-950 text-orange-400 border-orange-900',
  MEDIUM: 'bg-yellow-950 text-yellow-400 border-yellow-900',
  LOW: 'bg-gray-900 text-gray-400 border-gray-700',
}
const SevBadge = ({ s }: { s: string }) => (
  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${SEV[s] || SEV.LOW}`}>{s}</span>
)

// ── Forum status badge ────────────────────────────────────────────────────────

const ForumStatus = ({ forum }: { forum: Forum }) => {
  if (!forum.is_active) return <span className="text-[10px] font-mono px-2 py-0.5 rounded border bg-gray-900 text-gray-400 border-gray-700">Inactive</span>
  if (forum.has_cookies && forum.last_successful_login) return <span className="text-[10px] font-mono px-2 py-0.5 rounded border bg-green-950 text-green-400 border-green-900">Authenticated</span>
  if (forum.has_password) return <span className="text-[10px] font-mono px-2 py-0.5 rounded border bg-yellow-950 text-yellow-400 border-yellow-900">Ready</span>
  return <span className="text-[10px] font-mono px-2 py-0.5 rounded border bg-orange-950 text-orange-400 border-orange-900">No Credentials</span>
}

// ── Add Forum Modal ───────────────────────────────────────────────────────────

const SOFTWARE_OPTIONS = [
  { value: 'xenforo', label: 'XenForo (Breached.st, BreachForums)' },
  { value: 'mybb', label: 'MyBB (HackForums)' },
  { value: 'phpbb', label: 'phpBB' },
  { value: 'custom', label: 'Custom' },
]

const AddForumModal = ({ onClose, onSave }: { onClose: () => void; onSave: () => void }) => {
  const [form, setForm] = useState({
    forum_id: '', forum_name: '', forum_url: '', username: '',
    password: '', login_url: '', forum_software: 'xenforo',
    search_url_pattern: '', result_selector: '', auto_login: true, notes: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const set = (k: string, v: string | boolean) => setForm(p => ({ ...p, [k]: v }))

  const handleSave = async () => {
    if (!form.forum_id.trim() || !form.forum_name.trim() || !form.forum_url.trim()) {
      setError('Forum ID, name, and URL are required'); return
    }
    setSaving(true); setError('')
    try {
      await api.post('/forums/add', {
        forum_id: form.forum_id.trim(), forum_name: form.forum_name.trim(),
        forum_url: form.forum_url.trim(), username: form.username || null,
        password: form.password || null, login_url: form.login_url || null,
        forum_software: form.forum_software,
        search_url_pattern: form.search_url_pattern || null,
        result_selector: form.result_selector || null,
        auto_login: form.auto_login, notes: form.notes || null,
      })
      onSave(); onClose()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to add forum')
    } finally { setSaving(false) }
  }

  const tf = (k: string, label: string, ph: string, type = 'text') => (
    <div>
      <label className="text-[10px] font-mono text-text-muted uppercase tracking-widest block mb-1">{label}</label>
      <input type={type} value={(form as any)[k]} onChange={e => set(k, e.target.value)}
        placeholder={ph} className="w-full bg-background border border-border rounded px-3 py-2 text-xs font-mono text-text-primary focus:border-accent-green focus:outline-none" />
    </div>
  )

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-surface border border-border rounded-lg p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-sm font-mono text-text-primary uppercase tracking-widest">Add Forum Source</h3>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">✕</button>
        </div>
        <div className="space-y-3">
          {tf('forum_id', 'Forum ID (unique slug)', 'breached_st')}
          {tf('forum_name', 'Display Name', 'Breached.st')}
          {tf('forum_url', 'Base URL', 'https://breached.st')}
          {tf('username', 'Username / Email', 'your@email.com')}
          {tf('password', 'Password', 'Forum password', 'password')}
          {tf('login_url', 'Login URL (optional — auto-detected)', 'https://forum.com/login')}
          <div>
            <label className="text-[10px] font-mono text-text-muted uppercase tracking-widest block mb-1">Forum Software</label>
            <select value={form.forum_software} onChange={e => set('forum_software', e.target.value)}
              className="w-full bg-background border border-border rounded px-3 py-2 text-xs font-mono text-text-primary focus:border-accent-green focus:outline-none">
              {SOFTWARE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          {tf('notes', 'Notes (optional)', 'Primary threat intel source')}
          <div className="flex items-center justify-between border border-border rounded p-3">
            <div>
              <div className="text-xs font-mono text-text-primary">Auto-Login</div>
              <div className="text-[10px] text-text-muted">Re-authenticate automatically when session expires</div>
            </div>
            <button onClick={() => set('auto_login', !form.auto_login)}
              className={`w-10 h-5 rounded-full border relative transition-all ${form.auto_login ? 'border-accent-green' : 'border-border'}`}>
              <div className={`absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all ${form.auto_login ? 'left-[1.35rem] bg-accent-green' : 'left-0.5 bg-gray-500'}`} />
            </button>
          </div>
        </div>
        {error && <div className="text-red-400 text-xs font-mono mt-3">{error}</div>}
        <div className="flex gap-3 mt-5">
          <button onClick={handleSave} disabled={saving}
            className="flex-1 bg-accent-green text-black text-xs font-mono py-2 rounded hover:opacity-90 disabled:opacity-50">
            {saving ? 'Adding...' : 'Add Forum'}
          </button>
          <button onClick={onClose} className="px-4 text-xs font-mono text-text-muted border border-border rounded hover:border-text-muted">Cancel</button>
        </div>
      </div>
    </div>
  )
}

// ── Update Password Modal ─────────────────────────────────────────────────────

const UpdatePasswordModal = ({ forum, onClose, onSave }: { forum: Forum; onClose: () => void; onSave: () => void }) => {
  const [password, setPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async () => {
    if (!password.trim()) { setError('Password required'); return }
    setSaving(true); setError('')
    try {
      await api.put(`/forums/update-password/${forum.forum_id}`, { password })
      onSave(); onClose()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed')
    } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-surface border border-border rounded-lg p-6 w-full max-w-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-mono text-text-primary uppercase tracking-widest">Update Password</h3>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">✕</button>
        </div>
        <div className="text-xs text-text-muted font-mono mb-3">{forum.forum_name}</div>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)}
          placeholder="New password" autoFocus
          className="w-full bg-background border border-border rounded px-3 py-2 text-xs font-mono text-text-primary focus:border-accent-green focus:outline-none mb-3" />
        {error && <div className="text-red-400 text-xs font-mono mb-3">{error}</div>}
        <div className="flex gap-3">
          <button onClick={handleSave} disabled={saving}
            className="flex-1 bg-accent-green text-black text-xs font-mono py-2 rounded hover:opacity-90 disabled:opacity-50">
            {saving ? 'Saving...' : 'Update Password'}
          </button>
          <button onClick={onClose} className="px-4 text-xs font-mono text-text-muted border border-border rounded hover:border-text-muted">Cancel</button>
        </div>
      </div>
    </div>
  )
}

// ── Setup Guide ───────────────────────────────────────────────────────────────

const SetupGuide = ({ onAddForum }: { onAddForum: () => void }) => (
  <div className="border border-border rounded-lg p-6 space-y-4">
    <div className="text-sm font-mono text-text-primary uppercase tracking-widest">Forum Intelligence Setup</div>
    <p className="text-xs text-text-muted font-mono leading-relaxed">
      SENTINEL monitors breach forums by authenticating directly and searching for your keyword watchlist.
      Sessions are validated before each scan and renewed automatically.
    </p>
    <div className="space-y-3">
      {[
        { n: '1', t: 'Add forum credentials', d: 'Provide your forum username and password. The password is AES-encrypted before storage — never stored in plaintext.' },
        { n: '2', t: 'Test authentication', d: 'Click "Login Now" to authenticate and store session cookies. Verify you see xf_user in the returned cookies.' },
        { n: '3', t: 'Trigger a scan', d: 'Run "Scan Now" or wait for the hourly scheduled scan. SENTINEL searches using your active keyword watchlist.' },
        { n: '4', t: 'Triage hits', d: 'Review results in the Hits tab. Mark items as reviewed or false positive, and add analyst notes per hit.' },
      ].map(({ n, t, d }) => (
        <div key={n} className="flex gap-3">
          <div className="w-6 h-6 rounded-full border border-accent-green flex-shrink-0 flex items-center justify-center text-[10px] font-mono text-accent-green">{n}</div>
          <div>
            <div className="text-xs font-mono text-text-primary">{t}</div>
            <div className="text-[10px] text-text-muted mt-0.5">{d}</div>
          </div>
        </div>
      ))}
    </div>
    <button onClick={onAddForum} className="mt-2 bg-accent-green text-black text-xs font-mono px-6 py-2 rounded hover:opacity-90">
      Add First Forum (Breached.st)
    </button>
  </div>
)

// ── Mention row + expanded detail ─────────────────────────────────────────────

interface MentionRowProps {
  m: Mention
  isExpanded: boolean
  onToggle: () => void
  onReview: (id: string, updates: Partial<Mention>) => void
  reviewing: boolean
}

const MentionRow = ({ m, isExpanded, onToggle, onReview, reviewing }: MentionRowProps) => {
  const [notes, setNotes] = useState(m.analyst_notes || '')

  const domain = m.source_url ? (() => { try { return new URL(m.source_url!).hostname } catch { return m.source_url } })() : null

  return (
    <>
      <tr
        className={`border-b border-border cursor-pointer transition-colors ${isExpanded ? 'bg-surface/80' : 'hover:bg-surface/50'}`}
        onClick={onToggle}
      >
        <td className="px-4 py-3 w-4">
          <span className={`text-[10px] font-mono text-text-muted transition-transform inline-block ${isExpanded ? 'rotate-90' : ''}`}>›</span>
        </td>
        <td className="px-4 py-3"><SevBadge s={m.severity} /></td>
        <td className="px-4 py-3 max-w-xs">
          <div className="text-xs font-mono text-text-primary truncate" title={m.title}>{m.title || '(no title)'}</div>
          {m.snippet && <div className="text-[10px] text-text-muted mt-0.5 line-clamp-1">{m.snippet}</div>}
        </td>
        <td className="px-4 py-3 text-[10px] font-mono text-text-muted">{m.keyword_matched}</td>
        <td className="px-4 py-3 text-[10px] font-mono text-text-muted whitespace-nowrap">
          {new Date(m.discovered_at).toLocaleDateString()}
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
            : <span className="text-[10px] font-mono text-yellow-600">pending</span>}
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
              {m.source_url && (
                <div>
                  <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">Forum Thread</div>
                  <a
                    href={m.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={e => e.stopPropagation()}
                    className="inline-flex items-center gap-1.5 text-xs font-mono text-accent-green hover:underline break-all"
                  >
                    {m.source_url}
                    <svg className="w-3 h-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
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

// ── Main Page ─────────────────────────────────────────────────────────────────

type Tab = 'hits' | 'credentials' | 'scans'

const PAGE_LIMIT = 20

export default function ForumsPage() {
  const [forums, setForums] = useState<Forum[]>([])
  const [mentions, setMentions] = useState<Mention[]>([])
  const [mentionStats, setMentionStats] = useState<MentionStats>({ total: 0, critical_high: 0, unreviewed: 0, by_source: {} })
  const [scans, setScans] = useState<Scan[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('hits')

  // Filters
  const [filterSeverity, setFilterSeverity] = useState('')
  const [filterSearch, setFilterSearch] = useState('')
  const [filterDays, setFilterDays] = useState(30)
  const [page, setPage] = useState(1)

  // Modals / actions
  const [showAdd, setShowAdd] = useState(false)
  const [updatePwForum, setUpdatePwForum] = useState<Forum | null>(null)
  const [loggingIn, setLoggingIn] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [reviewingId, setReviewingId] = useState<string | null>(null)
  const [toast, setToast] = useState<{ ok: boolean; msg: string } | null>(null)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const showToast = (ok: boolean, msg: string) => {
    setToast({ ok, msg })
    setTimeout(() => setToast(null), 6000)
  }

  const loadForums = useCallback(async () => {
    const res = await api.get('/forums/list')
    setForums(res.data)
  }, [])

  const loadMentions = useCallback(async () => {
    const params = new URLSearchParams({
      days: String(filterDays),
      page: String(page),
      limit: String(PAGE_LIMIT),
    })
    if (filterSeverity) params.set('severity', filterSeverity)
    if (filterSearch) params.set('keyword', filterSearch)

    const res = await api.get(`/darkweb/forum-mentions?${params}`)
    setMentions(res.data.mentions ?? [])
    setMentionStats(res.data.stats ?? { total: 0, critical_high: 0, unreviewed: 0, by_source: {} })
  }, [filterDays, page, filterSeverity, filterSearch])

  const loadScans = useCallback(async () => {
    const res = await api.get('/darkweb/scans?limit=20')
    const all: Scan[] = Array.isArray(res.data) ? res.data : []
    setScans(all.filter(s => s.scan_type === 'forums'))
  }, [])

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      await Promise.allSettled([loadForums(), loadMentions(), loadScans()])
    } finally {
      setLoading(false)
    }
  }, [loadForums, loadMentions, loadScans])

  useEffect(() => { loadAll() }, [loadAll])

  // Re-fetch mentions when filters/page change (without full reload)
  useEffect(() => {
    loadMentions()
  }, [filterSeverity, filterSearch, filterDays, page, loadMentions])

  // Clean up poll on unmount
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const loginNow = async (forumId: string) => {
    setLoggingIn(forumId)
    try {
      const res = await api.post(`/forums/login-now/${forumId}`)
      const d = res.data
      if (d.success) {
        showToast(true, `Login successful — ${d.cookies_obtained} cookies: ${(d.cookie_names || []).join(', ')}`)
        loadForums()
      } else {
        showToast(false, `Login failed: ${d.error}`)
      }
    } catch (e: any) {
      showToast(false, e?.response?.data?.detail || 'Request failed')
    } finally { setLoggingIn(null) }
  }

  const triggerScan = async () => {
    setScanning(true)
    try {
      await api.post('/darkweb/scan/trigger?scan_type=forums')
      showToast(true, 'Forum scan queued — polling for results...')

      const startedAt = Date.now()
      pollRef.current = setInterval(async () => {
        // Stop after 3 minutes
        if (Date.now() - startedAt > 3 * 60 * 1000) {
          clearInterval(pollRef.current!)
          setScanning(false)
          showToast(false, 'Scan is taking longer than expected — check Scan History')
          return
        }
        try {
          const res = await api.get('/darkweb/scans?limit=5')
          const forumScans: Scan[] = (Array.isArray(res.data) ? res.data : []).filter((s: Scan) => s.scan_type === 'forums')
          const latest = forumScans[0]
          if (latest && ['completed', 'failed'].includes(latest.status)) {
            clearInterval(pollRef.current!)
            setScanning(false)
            await Promise.allSettled([loadMentions(), loadScans()])
            if (latest.status === 'completed') {
              showToast(true, `Scan complete — ${latest.new_mentions} new hit${latest.new_mentions !== 1 ? 's' : ''}`)
            } else {
              showToast(false, `Scan failed: ${latest.error_message || 'unknown error'}`)
            }
          }
        } catch { /* keep polling */ }
      }, 4000)
    } catch (e: any) {
      setScanning(false)
      showToast(false, e?.response?.data?.detail || 'Failed to trigger scan')
    }
  }

  const reviewMention = async (id: string, updates: object) => {
    setReviewingId(id)
    try {
      await api.patch(`/darkweb/mentions/${id}`, updates)
      setMentions(prev => prev.map(m => m.id === id ? { ...m, ...updates } : m))
      // Refresh unreviewed count
      loadMentions()
    } catch {
      showToast(false, 'Failed to update mention')
    } finally { setReviewingId(null) }
  }

  const removeForum = async (forumId: string, name: string) => {
    if (!confirm(`Remove ${name}?`)) return
    try {
      await api.delete(`/forums/remove/${forumId}`)
      loadForums()
    } catch (e: any) {
      showToast(false, e?.response?.data?.detail || 'Failed to remove')
    }
  }

  const totalPages = Math.ceil(mentionStats.total / PAGE_LIMIT)
  const authenticated = forums.filter(f => f.has_cookies && f.last_successful_login).length
  const lastScan = scans[0]

  const relativeTime = (iso: string | null) => {
    if (!iso) return 'never'
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    return `${Math.floor(diff / 3600)}h ago`
  }

  const nextScanIn = () => {
    if (!lastScan?.completed_at) return null
    const next = new Date(lastScan.completed_at).getTime() + 1800 * 1000
    const remaining = Math.floor((next - Date.now()) / 1000)
    if (remaining <= 0) return 'any moment'
    if (remaining < 60) return `${remaining}s`
    return `~${Math.floor(remaining / 60)}m`
  }

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: 'hits', label: 'Hits', count: mentionStats.total },
    { id: 'credentials', label: 'Forum Sources', count: forums.length },
    { id: 'scans', label: 'Scan History', count: scans.length },
  ]

  return (
    <AppLayout>
      <div className="p-6 space-y-5">

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-mono text-text-primary uppercase tracking-widest">Forum Intelligence</h1>
            <p className="text-xs text-text-muted mt-0.5">
              Authenticated breach forum monitoring · scans every 30 min
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button onClick={triggerScan} disabled={scanning || forums.length === 0}
              className="text-xs font-mono px-4 py-2 border border-border rounded text-text-muted hover:border-accent-green hover:text-accent-green disabled:opacity-40 transition-colors">
              {scanning ? (
                <span className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-accent-green animate-pulse inline-block" />
                  Scanning...
                </span>
              ) : 'Scan Now'}
            </button>
            <button onClick={() => { setShowAdd(true); setActiveTab('credentials') }}
              className="text-xs font-mono px-4 py-2 bg-accent-green text-black rounded hover:opacity-90">
              + Add Forum
            </button>
          </div>
        </div>

        {/* Scan status strip */}
        {lastScan && (
          <div className={`flex items-center gap-3 px-4 py-2 rounded border text-[10px] font-mono ${
            lastScan.status === 'completed' ? 'border-green-900 bg-green-950/30 text-green-400'
            : lastScan.status === 'running' ? 'border-blue-900 bg-blue-950/30 text-blue-400'
            : 'border-red-900 bg-red-950/30 text-red-400'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
              lastScan.status === 'completed' ? 'bg-green-400'
              : lastScan.status === 'running' ? 'bg-blue-400 animate-pulse'
              : 'bg-red-400'
            }`} />
            <span>
              Last scan: <strong>{relativeTime(lastScan.completed_at)}</strong>
              {lastScan.status === 'completed' && ` · ${lastScan.mentions_found} matched · ${lastScan.new_mentions} new`}
              {lastScan.status === 'failed' && ` · ${lastScan.error_message || 'error'}`}
              {lastScan.status === 'running' && ' · scan in progress...'}
            </span>
            {nextScanIn() && lastScan.status !== 'running' && (
              <span className="ml-auto text-text-muted">next in {nextScanIn()}</span>
            )}
          </div>
        )}

        {/* Toast */}
        {toast && (
          <div className={`border rounded p-3 text-xs font-mono flex items-start gap-3 ${toast.ok ? 'border-green-800 bg-green-950 text-green-400' : 'border-red-800 bg-red-950 text-red-400'}`}>
            <span className="flex-1">{toast.msg}</span>
            <button onClick={() => setToast(null)} className="opacity-60 hover:opacity-100 flex-shrink-0">✕</button>
          </div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Forums Active', value: `${authenticated}/${forums.length}`, sub: 'authenticated', vc: authenticated > 0 ? 'text-accent-green' : 'text-text-muted' },
            { label: 'Total Hits', value: mentionStats.total, sub: 'all time', vc: mentionStats.total > 0 ? 'text-orange-400' : 'text-text-muted' },
            { label: 'Unreviewed', value: mentionStats.unreviewed, sub: 'need triage', vc: mentionStats.unreviewed > 0 ? 'text-red-400' : 'text-text-muted' },
            { label: 'Last Scan', value: lastScan ? relativeTime(lastScan.completed_at) : '—', sub: nextScanIn() ? `next in ${nextScanIn()}` : 'no scan yet', vc: lastScan?.status === 'completed' ? 'text-accent-green' : lastScan?.status === 'failed' ? 'text-red-400' : 'text-text-muted' },
          ].map(({ label, value, sub, vc }) => (
            <div key={label} className="bg-surface border border-border rounded-lg p-3">
              <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">{label}</div>
              <div className={`text-xl font-bold font-mono ${vc}`}>{value}</div>
              <div className="text-[10px] text-text-muted mt-0.5">{sub}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border">
          {tabs.map(t => (
            <button key={t.id} onClick={() => setActiveTab(t.id)}
              className={`text-xs font-mono px-4 py-2 border-b-2 transition-colors ${activeTab === t.id ? 'border-accent-green text-accent-green' : 'border-transparent text-text-muted hover:text-text-primary'}`}>
              {t.label}
              {t.count !== undefined && t.count > 0 && (
                <span className="ml-1.5 text-[10px] bg-surface border border-border rounded px-1">{t.count}</span>
              )}
            </button>
          ))}
        </div>

        {/* ── HITS TAB ──────────────────────────────────────────────────────── */}
        {activeTab === 'hits' && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex flex-wrap gap-2 items-center">
              <input
                type="text"
                placeholder="title, org, gov.lk, srilanka..."
                value={filterSearch}
                onChange={e => { setFilterSearch(e.target.value); setPage(1) }}
                className="bg-surface border border-border rounded px-3 py-1.5 text-xs font-mono text-text-primary focus:border-accent-green focus:outline-none w-56"
              />
              <select
                value={filterSeverity}
                onChange={e => { setFilterSeverity(e.target.value); setPage(1) }}
                className="bg-surface border border-border rounded px-3 py-1.5 text-xs font-mono text-text-primary focus:border-accent-green focus:outline-none">
                <option value="">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
              <select
                value={filterDays}
                onChange={e => { setFilterDays(Number(e.target.value)); setPage(1) }}
                className="bg-surface border border-border rounded px-3 py-1.5 text-xs font-mono text-text-primary focus:border-accent-green focus:outline-none">
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={365}>Last year</option>
              </select>
              {(filterSeverity || filterSearch) && (
                <button
                  onClick={() => { setFilterSeverity(''); setFilterSearch(''); setPage(1) }}
                  className="text-[10px] font-mono text-text-muted hover:text-text-primary border border-border rounded px-2 py-1.5">
                  Clear filters
                </button>
              )}
            </div>

            {loading ? (
              <div className="py-12 text-center text-xs text-text-muted font-mono">Loading...</div>
            ) : mentions.length === 0 ? (
              <div className="border border-dashed border-border rounded-lg py-12 text-center space-y-2">
                <div className="text-sm font-mono text-text-muted">No forum hits yet</div>
                <div className="text-xs text-text-muted">
                  {forums.length === 0
                    ? 'Configure Breached.st credentials in Forum Sources, then run a scan'
                    : filterSeverity || filterSearch
                      ? 'No hits match your filters — try clearing them'
                      : 'Trigger a scan — results appear here when keyword matches are found'}
                </div>
                {forums.length === 0 ? (
                  <button onClick={() => { setShowAdd(true); setActiveTab('credentials') }}
                    className="mt-3 text-xs font-mono text-accent-green hover:underline">
                    Add Forum Source →
                  </button>
                ) : !filterSeverity && !filterSearch ? (
                  <button onClick={triggerScan} disabled={scanning}
                    className="mt-3 text-xs font-mono text-accent-green hover:underline disabled:opacity-40">
                    {scanning ? 'Scanning...' : 'Trigger Scan →'}
                  </button>
                ) : null}
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border">
                        {['', 'Severity', 'Thread / Match', 'Keyword', 'Discovered', 'Source', 'Status'].map(h => (
                          <th key={h} className="text-left text-[10px] font-mono text-text-muted uppercase tracking-widest px-4 pb-2">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {mentions.map(m => (
                        <MentionRow
                          key={m.id}
                          m={m}
                          isExpanded={expandedId === m.id}
                          onToggle={() => setExpandedId(prev => prev === m.id ? null : m.id)}
                          onReview={reviewMention}
                          reviewing={reviewingId === m.id}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between text-[10px] font-mono text-text-muted pt-2">
                    <span>Page {page} of {totalPages} · {mentionStats.total} total</span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page <= 1}
                        className="px-3 py-1 border border-border rounded hover:border-text-muted disabled:opacity-30">
                        ← Prev
                      </button>
                      <button
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page >= totalPages}
                        className="px-3 py-1 border border-border rounded hover:border-text-muted disabled:opacity-30">
                        Next →
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── CREDENTIALS TAB ───────────────────────────────────────────────── */}
        {activeTab === 'credentials' && (
          <div className="space-y-4">
            {forums.length === 0 ? (
              <SetupGuide onAddForum={() => setShowAdd(true)} />
            ) : (
              <div className="bg-surface border border-border rounded-lg overflow-hidden">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr className="border-b border-border">
                      {['Forum', 'Software', 'Account', 'Status', 'Last Auth', 'Actions'].map(h => (
                        <th key={h} className="text-left text-[10px] text-text-muted uppercase tracking-widest px-4 py-3">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {forums.map(f => (
                      <tr key={f.forum_id} className="border-b border-border hover:bg-background/40">
                        <td className="px-4 py-3">
                          <div className="text-text-primary font-medium">{f.forum_name}</div>
                          <div className="text-[10px] text-text-muted">{f.forum_url}</div>
                        </td>
                        <td className="px-4 py-3 text-text-muted uppercase text-[10px]">{f.forum_software || 'mybb'}</td>
                        <td className="px-4 py-3">
                          <div className="text-text-muted">{f.username || '—'}</div>
                          {f.has_password && <div className="text-accent-green text-[10px] mt-0.5">⚡ password stored</div>}
                          {f.auto_login && <div className="text-blue-400 text-[10px]">↺ auto-login on</div>}
                        </td>
                        <td className="px-4 py-3">
                          <ForumStatus forum={f} />
                          {f.login_attempts > 2 && (
                            <div className="text-orange-400 text-[10px] mt-0.5">{f.login_attempts} attempts</div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-text-muted text-[10px]">
                          {f.last_successful_login ? new Date(f.last_successful_login).toLocaleDateString() : '—'}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col gap-1">
                            <button onClick={() => loginNow(f.forum_id)}
                              disabled={loggingIn === f.forum_id || !f.has_password}
                              className="text-yellow-400 hover:underline disabled:opacity-40 text-left">
                              {loggingIn === f.forum_id ? 'Logging in...' : 'Login Now'}
                            </button>
                            <button onClick={() => setUpdatePwForum(f)} className="text-blue-400 hover:underline text-left">
                              Update Password
                            </button>
                            <button onClick={() => removeForum(f.forum_id, f.forum_name)} className="text-red-400 hover:underline text-left">
                              Remove
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ── SCANS TAB ─────────────────────────────────────────────────────── */}
        {activeTab === 'scans' && (
          <div>
            {scans.length === 0 ? (
              <div className="border border-dashed border-border rounded-lg py-12 text-center text-xs text-text-muted font-mono">
                No forum scans yet. Trigger one using &quot;Scan Now&quot; or wait for the 30-minute schedule.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr className="border-b border-border">
                      {['Status', 'Started', 'Duration', 'Keywords', 'Found', 'New', 'Error'].map(h => (
                        <th key={h} className="text-left text-[10px] text-text-muted uppercase tracking-widest px-4 pb-2">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {scans.map(s => (
                      <tr key={s.id} className="border-b border-border">
                        <td className="px-4 py-3">
                          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                            s.status === 'completed' ? 'bg-green-950 text-green-400 border-green-900'
                            : s.status === 'running' ? 'bg-blue-950 text-blue-400 border-blue-900'
                            : s.status === 'failed' ? 'bg-red-950 text-red-400 border-red-900'
                            : 'bg-gray-900 text-gray-400 border-gray-700'
                          }`}>{s.status}</span>
                        </td>
                        <td className="px-4 py-3 text-text-muted whitespace-nowrap">
                          {s.started_at ? new Date(s.started_at).toLocaleString() : '—'}
                        </td>
                        <td className="px-4 py-3 text-text-muted">
                          {s.duration_seconds != null ? `${s.duration_seconds.toFixed(1)}s` : '—'}
                        </td>
                        <td className="px-4 py-3 text-text-muted">{s.keywords_scanned}</td>
                        <td className="px-4 py-3 text-text-muted">{s.mentions_found}</td>
                        <td className={`px-4 py-3 font-medium ${s.new_mentions > 0 ? 'text-orange-400' : 'text-text-muted'}`}>{s.new_mentions}</td>
                        <td className="px-4 py-3 text-red-400 text-[10px] max-w-xs truncate" title={s.error_message || ''}>
                          {s.error_message || ''}
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

      {showAdd && <AddForumModal onClose={() => setShowAdd(false)} onSave={loadAll} />}
      {updatePwForum && <UpdatePasswordModal forum={updatePwForum} onClose={() => setUpdatePwForum(null)} onSave={loadAll} />}
    </AppLayout>
  )
}
