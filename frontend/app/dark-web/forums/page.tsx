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
        { n: '4', t: 'Triage hits', d: 'Review results on the main Dark Web page. Mark items as reviewed or false positive, and add analyst notes.' },
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

// ── Main Page ─────────────────────────────────────────────────────────────────

type Tab = 'credentials' | 'scans'

export default function ForumsPage() {
  const [forums, setForums] = useState<Forum[]>([])
  const [scans, setScans] = useState<Scan[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('credentials')

  // Modals / actions
  const [showAdd, setShowAdd] = useState(false)
  const [updatePwForum, setUpdatePwForum] = useState<Forum | null>(null)
  const [loggingIn, setLoggingIn] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)
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

  const loadScans = useCallback(async () => {
    const res = await api.get('/darkweb/scans?limit=20')
    const all: Scan[] = Array.isArray(res.data) ? res.data : []
    setScans(all.filter(s => s.scan_type === 'forums'))
  }, [])

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      await Promise.allSettled([loadForums(), loadScans()])
    } finally {
      setLoading(false)
    }
  }, [loadForums, loadScans])

  useEffect(() => { loadAll() }, [loadAll])

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
              await loadScans()
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

  const removeForum = async (forumId: string, name: string) => {
    if (!confirm(`Remove ${name}?`)) return
    try {
      await api.delete(`/forums/remove/${forumId}`)
      loadForums()
    } catch (e: any) {
      showToast(false, e?.response?.data?.detail || 'Failed to remove')
    }
  }

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
    { id: 'credentials', label: 'Forum Sources', count: forums.length },
    { id: 'scans', label: 'Scan History', count: scans.length },
  ]

  return (
    <AppLayout>
      <div className="p-6 space-y-5">

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-mono text-text-primary uppercase tracking-widest">Forum Intel Settings</h1>
            <p className="text-xs text-text-muted mt-0.5">
              Manage forum credentials and view scan history
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
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[
            { label: 'Forums Active', value: `${authenticated}/${forums.length}`, sub: 'authenticated', vc: authenticated > 0 ? 'text-accent-green' : 'text-text-muted' },
            { label: 'Scan Schedule', value: 'Every 30min', sub: 'auto-scan enabled', vc: 'text-text-muted' },
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
