'use client'

import { useEffect, useState, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import AlertCard from '@/components/ui/AlertCard'
import SeverityBadge from '@/components/ui/SeverityBadge'
import { Bell, FileText, RefreshCw, Plus, Download } from 'lucide-react'
import { formatDate } from '@/lib/utils'

const MODULES = ['', 'threat-intel', 'dark-web', 'news', 'geoint', 'profiles', 'socmint', 'cyber-surface']
const SEVERITIES = ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']
const STATUSES = ['', 'open', 'acknowledged', 'resolved']

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([])
  const [reports, setReports] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'alerts' | 'reports'>('alerts')
  const [severity, setSeverity] = useState('')
  const [module, setModule] = useState('')
  const [status, setStatus] = useState('open')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showReportForm, setShowReportForm] = useState(false)
  const [reportForm, setReportForm] = useState({ title: '', report_type: 'sitrep', modules: [] as string[] })

  const fetchAlerts = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '30', since_hours: '168' })
      if (severity) params.set('severity', severity)
      if (module) params.set('module', module)
      if (status) params.set('status', status)
      const [alertsRes, statsRes, reportsRes] = await Promise.all([
        api.get(`/alerts?${params}`),
        api.get('/alerts/stats'),
        api.get('/alerts/reports'),
      ])
      setAlerts(alertsRes.data.items)
      setTotal(alertsRes.data.total)
      setStats(statsRes.data)
      setReports(reportsRes.data)
    } catch {}
    setLoading(false)
  }, [page, severity, module, status])

  useEffect(() => { fetchAlerts() }, [fetchAlerts])

  const acknowledgeAlert = async (id: number) => {
    try {
      await api.post(`/alerts/${id}/acknowledge`)
      setAlerts(a => a.map(x => x.id === id ? { ...x, status: 'acknowledged' } : x))
    } catch {}
  }

  const createReport = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.post('/alerts/reports', { ...reportForm, date_from: null, date_to: null })
      setShowReportForm(false)
      fetchAlerts()
    } catch {}
  }

  return (
    <AppLayout title="SENTINEL / Alerts & Reporting">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              <Bell className="w-5 h-5 text-warning" /> Alerts & Reporting
            </h1>
            <p className="text-xs text-text-muted mt-0.5">Unified alert feed and intelligence report generation</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowReportForm(true)}
              className="flex items-center gap-1.5 text-xs bg-accent-green/20 border border-accent-green/30 rounded px-3 py-1.5 text-accent-green hover:bg-accent-green/30 transition-colors">
              <FileText className="w-3.5 h-3.5" /> Generate Report
            </button>
          </div>
        </div>

        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'CRITICAL', value: stats.open_by_severity?.critical, color: 'text-danger' },
              { label: 'HIGH', value: stats.open_by_severity?.high, color: 'text-warning' },
              { label: 'MEDIUM', value: stats.open_by_severity?.medium, color: 'text-accent-blue' },
              { label: 'TOTAL OPEN', value: stats.total_open, color: 'text-text-primary' },
            ].map((s) => (
              <div key={s.label} className="sentinel-card text-center">
                <div className={`text-xl font-bold font-mono ${s.color}`}>{s.value ?? 0}</div>
                <SeverityBadge severity={s.label} className="mt-1" />
              </div>
            ))}
          </div>
        )}

        {/* Report form modal */}
        {showReportForm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="sentinel-card w-full max-w-md mx-4">
              <h3 className="text-sm font-semibold mb-4 font-mono">GENERATE INTELLIGENCE REPORT</h3>
              <form onSubmit={createReport} className="space-y-3">
                <input type="text" value={reportForm.title} onChange={e => setReportForm(f => ({ ...f, title: e.target.value }))}
                  className="sentinel-input" placeholder="Report title" required />
                <select value={reportForm.report_type} onChange={e => setReportForm(f => ({ ...f, report_type: e.target.value }))}
                  className="sentinel-input">
                  <option value="sitrep">SITREP</option>
                  <option value="incident">Incident Report</option>
                  <option value="threat_assessment">Threat Assessment</option>
                </select>
                <div className="flex gap-2 justify-end pt-2">
                  <button type="button" onClick={() => setShowReportForm(false)} className="text-xs border border-border rounded px-3 py-1.5 hover:bg-surface">Cancel</button>
                  <button type="submit" className="text-xs bg-accent-green text-background rounded px-3 py-1.5 hover:bg-accent-green/90 font-bold">Generate</button>
                </div>
              </form>
            </div>
          </div>
        )}

        <div className="flex gap-1 border-b border-border">
          {(['alerts', 'reports'] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 text-xs font-mono uppercase tracking-wider transition-colors ${tab === t ? 'text-accent-green border-b-2 border-accent-green' : 'text-text-muted hover:text-text-primary'}`}>
              {t}
            </button>
          ))}
        </div>

        {tab === 'alerts' && (
          <>
            {/* Filters */}
            <div className="flex flex-wrap gap-2">
              <select value={severity} onChange={e => { setSeverity(e.target.value); setPage(1) }} className="bg-background border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none">
                <option value="">All Severities</option>
                {SEVERITIES.slice(1).map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <select value={module} onChange={e => { setModule(e.target.value); setPage(1) }} className="bg-background border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none">
                <option value="">All Modules</option>
                {MODULES.slice(1).map(m => <option key={m} value={m}>{m}</option>)}
              </select>
              <select value={status} onChange={e => { setStatus(e.target.value); setPage(1) }} className="bg-background border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none">
                <option value="">All Statuses</option>
                {STATUSES.slice(1).map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <div className="space-y-2">
              {loading && <div className="text-center text-text-muted font-mono text-xs py-8">LOADING...</div>}
              {!loading && alerts.length === 0 && <div className="text-center text-text-muted font-mono text-xs py-8">NO ALERTS FOUND</div>}
              {alerts.map((alert) => (
                <AlertCard key={alert.id} alert={alert} onAcknowledge={acknowledgeAlert} />
              ))}
            </div>

            {total > 30 && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted font-mono">Showing {(page-1)*30+1}–{Math.min(page*30,total)} of {total}</span>
                <div className="flex gap-2">
                  <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1} className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30">Prev</button>
                  <button onClick={() => setPage(p => p+1)} disabled={page*30>=total} className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30">Next</button>
                </div>
              </div>
            )}
          </>
        )}

        {tab === 'reports' && (
          <div className="sentinel-card">
            <div className="overflow-x-auto">
            <table className="sentinel-table min-w-full">
              <thead><tr><th>Title</th><th>Type</th><th>Status</th><th>Generated</th><th></th></tr></thead>
              <tbody>
                {reports.length === 0 && <tr><td colSpan={5} className="text-center py-8 text-text-muted font-mono text-xs">NO REPORTS GENERATED YET</td></tr>}
                {reports.map((r: any) => (
                  <tr key={r.id}>
                    <td><span className="text-sm font-medium">{r.title}</span></td>
                    <td><span className="text-xs font-mono text-text-muted uppercase">{r.report_type}</span></td>
                    <td>
                      <span className={`text-xs font-mono ${r.status === 'ready' ? 'text-accent-green' : r.status === 'failed' ? 'text-danger' : 'text-warning'}`}>
                        {r.status?.toUpperCase()}
                      </span>
                    </td>
                    <td><span className="text-xs text-text-muted font-mono">{formatDate(r.generated_at)}</span></td>
                    <td>
                      {r.status === 'ready' && r.file_path && (
                        <button className="text-xs text-text-muted hover:text-accent-blue font-mono flex items-center gap-1">
                          <Download className="w-3 h-3" /> PDF
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
    </AppLayout>
  )
}
