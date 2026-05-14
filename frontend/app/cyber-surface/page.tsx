'use client'

import { useEffect, useState, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import SeverityBadge from '@/components/ui/SeverityBadge'
import { Monitor, Plus, Scan } from 'lucide-react'
import { formatRelativeTime, cn } from '@/lib/utils'

const GRADE_COLORS: Record<string, string> = {
  A: 'text-accent-green', B: 'text-accent-blue', C: 'text-warning',
  D: 'text-orange-500', F: 'text-danger',
}

export default function CyberSurfacePage() {
  const [assets, setAssets] = useState<any[]>([])
  const [vulns, setVulns] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'assets' | 'vulns'>('assets')
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ name: '', asset_type: 'domain', value: '', organization: '' })

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [aRes, vRes, sRes] = await Promise.all([
        api.get('/cyber-surface/assets?page_size=50'),
        api.get('/cyber-surface/vulnerabilities?page_size=30'),
        api.get('/cyber-surface/stats'),
      ])
      setAssets(aRes.data.items)
      setVulns(vRes.data.items)
      setStats(sRes.data)
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const addAsset = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.post('/cyber-surface/assets', form)
      setShowAdd(false)
      setForm({ name: '', asset_type: 'domain', value: '', organization: '' })
      fetchData()
    } catch {}
  }

  const triggerScan = async (assetId: number) => {
    try { await api.post(`/cyber-surface/assets/${assetId}/scan`) } catch {}
  }

  return (
    <AppLayout title="SENTINEL / Cyber Surface Monitor">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              <Monitor className="w-5 h-5 text-accent-blue" /> Cyber Surface Monitor
            </h1>
            <p className="text-xs text-text-muted mt-0.5">Monitor digital attack surface — SSL, ports, services, and CVEs</p>
          </div>
          <button onClick={() => setShowAdd(true)}
            className="flex items-center gap-1.5 text-xs bg-accent-blue/20 border border-accent-blue/30 rounded px-3 py-1.5 text-accent-blue hover:bg-accent-blue/30 transition-colors">
            <Plus className="w-3.5 h-3.5" /> Add Asset
          </button>
        </div>

        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Assets', value: stats.assets, color: 'text-accent-blue' },
              { label: 'Critical Vulns', value: stats.critical_vulns, color: 'text-danger' },
              { label: 'High Vulns', value: stats.high_vulns, color: 'text-warning' },
              { label: 'Open Alerts', value: stats.alerts_open, color: 'text-warning' },
            ].map((s) => (
              <div key={s.label} className="sentinel-card text-center">
                <div className={`text-xl font-bold font-mono ${s.color}`}>{s.value}</div>
                <div className="text-xs text-text-muted mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {showAdd && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="sentinel-card w-full max-w-md mx-4">
              <h3 className="text-sm font-semibold mb-4 font-mono">ADD MONITORED ASSET</h3>
              <form onSubmit={addAsset} className="space-y-3">
                <input type="text" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="sentinel-input" placeholder="Asset name (e.g. Air Force Portal)" required />
                <select value={form.asset_type} onChange={e => setForm(f => ({ ...f, asset_type: e.target.value }))}
                  className="sentinel-input">
                  <option value="domain">Domain</option>
                  <option value="ip">IP Address</option>
                  <option value="ip_range">IP Range</option>
                </select>
                <input type="text" value={form.value} onChange={e => setForm(f => ({ ...f, value: e.target.value }))}
                  className="sentinel-input font-mono" placeholder="domain.lk or 192.168.1.1" required />
                <input type="text" value={form.organization} onChange={e => setForm(f => ({ ...f, organization: e.target.value }))}
                  className="sentinel-input" placeholder="Organisation (optional)" />
                <div className="flex gap-2 justify-end pt-2">
                  <button type="button" onClick={() => setShowAdd(false)} className="text-xs border border-border rounded px-3 py-1.5 hover:bg-surface">Cancel</button>
                  <button type="submit" className="text-xs bg-accent-blue text-white rounded px-3 py-1.5 hover:bg-accent-blue/90 font-bold">Add Asset</button>
                </div>
              </form>
            </div>
          </div>
        )}

        <div className="flex gap-1 border-b border-border">
          {(['assets', 'vulns'] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 text-xs font-mono uppercase tracking-wider transition-colors ${tab === t ? 'text-accent-green border-b-2 border-accent-green' : 'text-text-muted hover:text-text-primary'}`}>
              {t === 'assets' ? `Assets (${assets.length})` : `Vulnerabilities (${vulns.length})`}
            </button>
          ))}
        </div>

        {tab === 'assets' && (
          <div className="sentinel-card">
            <table className="sentinel-table">
              <thead><tr><th>Asset</th><th>Type</th><th>Grade</th><th>Risk</th><th>Organization</th><th>Last Scan</th><th></th></tr></thead>
              <tbody>
                {loading && <tr><td colSpan={7} className="text-center py-8 text-text-muted font-mono text-xs">LOADING...</td></tr>}
                {!loading && assets.length === 0 && <tr><td colSpan={7} className="text-center py-8 text-text-muted font-mono text-xs">NO ASSETS — ADD ONE TO BEGIN MONITORING</td></tr>}
                {assets.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <div>
                        <div className="text-sm font-medium">{a.name}</div>
                        <code className="text-[10px] text-text-muted font-mono">{a.value}</code>
                      </div>
                    </td>
                    <td><span className="text-xs font-mono text-text-muted uppercase">{a.asset_type}</span></td>
                    <td><span className={cn('text-lg font-bold font-mono', GRADE_COLORS[a.risk_grade] || 'text-text-muted')}>{a.risk_grade || '—'}</span></td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1.5 bg-border rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${a.risk_score}%`, background: a.risk_score >= 75 ? '#ef4444' : a.risk_score >= 50 ? '#f59e0b' : '#3b82f6' }} />
                        </div>
                        <span className="font-mono text-xs">{Math.round(a.risk_score)}</span>
                      </div>
                    </td>
                    <td><span className="text-xs text-text-muted">{a.organization || '—'}</span></td>
                    <td><span className="text-xs text-text-muted font-mono">{formatRelativeTime(a.last_scanned)}</span></td>
                    <td>
                      <button onClick={() => triggerScan(a.id)} className="text-xs text-text-muted hover:text-accent-blue font-mono flex items-center gap-1">
                        <Scan className="w-3 h-3" /> Scan
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'vulns' && (
          <div className="sentinel-card">
            <table className="sentinel-table">
              <thead><tr><th>CVE</th><th>Title</th><th>Severity</th><th>CVSS</th><th>Service</th><th>Discovered</th></tr></thead>
              <tbody>
                {loading && <tr><td colSpan={6} className="text-center py-8 text-text-muted font-mono text-xs">LOADING...</td></tr>}
                {!loading && vulns.length === 0 && <tr><td colSpan={6} className="text-center py-8 text-text-muted font-mono text-xs">NO VULNERABILITIES FOUND</td></tr>}
                {vulns.map((v) => (
                  <tr key={v.id}>
                    <td><code className="text-xs font-mono text-accent-blue">{v.cve_id || '—'}</code></td>
                    <td><span className="text-xs">{v.title || '—'}</span></td>
                    <td><SeverityBadge severity={v.severity || 'INFO'} /></td>
                    <td><span className="text-xs font-mono">{v.cvss_score?.toFixed(1) || '—'}</span></td>
                    <td><span className="text-xs text-text-muted font-mono">{v.service || '—'}:{v.port || ''}</span></td>
                    <td><span className="text-xs text-text-muted font-mono">{formatRelativeTime(v.discovered_at)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
