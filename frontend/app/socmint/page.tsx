'use client'

import { useEffect, useState, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import { ExternalLink, MessageSquare, Plus, RefreshCw, Edit2, Check, X, Bell, Trash2 } from 'lucide-react'
import { formatRelativeTime, cn } from '@/lib/utils'

const SENTIMENT_COLORS: Record<string, string> = {
  positive: 'text-accent-green', negative: 'text-danger', neutral: 'text-text-muted',
}

const PLATFORMS = [
  { id: 'reddit', label: 'Reddit', color: 'text-orange-400' },
  { id: 'youtube', label: 'YouTube', color: 'text-red-400' },
  { id: 'telegram', label: 'Telegram', color: 'text-blue-400' },
  { id: 'bluesky', label: 'Bluesky', color: 'text-sky-400' },
  { id: 'mastodon', label: 'Mastodon', color: 'text-purple-400' },
]

export default function SocmintPage() {
  const [posts, setPosts] = useState<any[]>([])
  const [keywords, setKeywords] = useState<any[]>([])
  const [alerts, setAlerts] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'posts' | 'keywords' | 'alerts'>('posts')
  const [showAdd, setShowAdd] = useState(false)
  const [editingKw, setEditingKw] = useState<any>(null)
  const [newKeyword, setNewKeyword] = useState('')
  const [newPlatforms, setNewPlatforms] = useState<string[]>(['reddit'])
  const [newSubreddits, setNewSubreddits] = useState('')
  const [newThreshold, setNewThreshold] = useState(50)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [postsRes, kwRes, statsRes, alertsRes] = await Promise.all([
        api.get('/socmint/posts?page_size=50&since_hours=72'),
        api.get('/socmint/keywords'),
        api.get('/socmint/stats'),
        api.get('/socmint/alerts?page_size=20'),
      ])
      setPosts(postsRes.data.items)
      setKeywords(kwRes.data)
      setStats(statsRes.data)
      setAlerts(alertsRes.data.items || [])
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const addKeyword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKeyword.trim()) return
    const platforms = newPlatforms.map(p => {
      if (p === 'reddit' && newSubreddits.trim()) {
        return newSubreddits.split(',').map(s => `reddit:${s.trim()}`).join(',')
      }
      return p
    }).flatMap(p => p.includes(',') ? p.split(',') : [p])
    try {
      await api.post('/socmint/keywords', { keyword: newKeyword, platforms, spike_threshold: newThreshold })
      setNewKeyword(''); setNewPlatforms(['reddit']); setNewSubreddits(''); setNewThreshold(50); setShowAdd(false)
      fetchData()
    } catch {}
  }

  const updateKeyword = async (kw: any) => {
    try {
      await api.patch(`/socmint/keywords/${kw.id}`, {
        keyword: kw.keyword,
        platforms: kw.platforms,
        alert_on_spike: kw.alert_on_spike,
        spike_threshold: kw.spike_threshold,
        is_active: kw.is_active,
      })
      setEditingKw(null)
      fetchData()
    } catch {}
  }

  const toggleKeyword = async (kw: any) => {
    try {
      await api.patch(`/socmint/keywords/${kw.id}`, { is_active: !kw.is_active })
      fetchData()
    } catch {}
  }

  const deleteKeyword = async (kwId: number) => {
    try {
      await api.delete(`/socmint/keywords/${kwId}`)
      fetchData()
    } catch {}
  }

  const acknowledgeAlert = async (alertId: number) => {
    try {
      await api.post(`/socmint/alerts/${alertId}/acknowledge`)
      fetchData()
    } catch {}
  }

  return (
    <AppLayout title="SENTINEL / SOCMINT">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-warning" /> Social Media Intelligence
            </h1>
            <p className="text-xs text-text-muted mt-0.5">Monitor social media for intelligence signals</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => api.post('/socmint/scan-now').catch(() => {})}
              className="flex items-center gap-1.5 text-xs border border-border rounded px-3 py-1.5 hover:bg-surface transition-colors text-text-muted">
              <RefreshCw className="w-3.5 h-3.5" /> Scan Now
            </button>
            <button onClick={() => setShowAdd(true)}
              className="flex items-center gap-1.5 text-xs bg-warning/20 border border-warning/30 rounded px-3 py-1.5 text-warning hover:bg-warning/30 transition-colors">
              <Plus className="w-3.5 h-3.5" /> Add Keyword
            </button>
          </div>
        </div>

        {stats && (
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Total Posts', value: stats.total_posts },
              { label: 'Posts (24h)', value: stats.posts_24h },
              { label: 'Active Keywords', value: stats.keywords_active },
              { label: 'Active Alerts', value: alerts.filter((a: any) => !a.is_acknowledged).length },
            ].map((s) => (
              <div key={s.label} className="sentinel-card text-center">
                <div className="text-xl font-bold font-mono text-warning">{s.value}</div>
                <div className="text-xs text-text-muted mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {showAdd && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="sentinel-card w-full max-w-md mx-4">
              <h3 className="text-sm font-semibold mb-3 font-mono">ADD SOCIAL KEYWORD</h3>
              <div className="space-y-3">
                <input type="text" value={newKeyword} onChange={e => setNewKeyword(e.target.value)}
                  className="sentinel-input" placeholder="e.g. cyber security, ransomware" autoFocus
                  onKeyDown={(e) => { if (e.key === 'Enter') addKeyword({ preventDefault: () => {} } as React.FormEvent) }} />
                <div>
                  <label className="text-xs text-text-muted mb-1 block">Platforms</label>
                  <div className="flex flex-wrap gap-2">
                    {PLATFORMS.map(p => (
                      <label key={p.id} className="flex items-center gap-1.5 text-xs cursor-pointer">
                        <input type="checkbox" checked={newPlatforms.includes(p.id)}
                          onChange={e => setNewPlatforms(prev => e.target.checked ? [...prev, p.id] : prev.filter(x => x !== p.id))}
                          className="rounded border-border" />
                        <span className={p.color}>{p.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
                {newPlatforms.includes('reddit') && (
                  <div>
                    <label className="text-xs text-text-muted mb-1 block">Subreddits (comma-separated, e.g. srilanka, cybersecurity)</label>
                    <input type="text" value={newSubreddits} onChange={e => setNewSubreddits(e.target.value)}
                      className="sentinel-input" placeholder="e.g. srilanka, worldnews" />
                  </div>
                )}
                <div>
                  <label className="text-xs text-text-muted mb-1 block">Spike Threshold (mentions/hour)</label>
                  <input type="number" value={newThreshold} onChange={e => setNewThreshold(parseInt(e.target.value) || 50)}
                    className="sentinel-input w-24" min={1} />
                </div>
                <div className="flex gap-2 justify-end">
                  <button type="button" onClick={() => setShowAdd(false)} className="text-xs border border-border rounded px-3 py-1.5 hover:bg-surface">Cancel</button>
                  <button type="button" onClick={() => addKeyword({ preventDefault: () => {} } as React.FormEvent)} className="text-xs bg-warning text-background rounded px-3 py-1.5 hover:bg-warning/90 font-bold">Add</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {editingKw && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="sentinel-card w-full max-w-md mx-4">
              <h3 className="text-sm font-semibold mb-3 font-mono">EDIT KEYWORD</h3>
              <div className="space-y-3">
                <input type="text" value={editingKw.keyword} onChange={e => setEditingKw({ ...editingKw, keyword: e.target.value })}
                  className="sentinel-input" />
                <div>
                  <label className="text-xs text-text-muted mb-1 block">Platforms</label>
                  <div className="flex flex-wrap gap-2">
                    {PLATFORMS.map(p => (
                      <label key={p.id} className="flex items-center gap-1.5 text-xs cursor-pointer">
                        <input type="checkbox" checked={(editingKw.platforms || []).includes(p.id)}
                          onChange={e => {
                            const platforms = editingKw.platforms || []
                            setEditingKw({ ...editingKw, platforms: e.target.checked ? [...platforms, p.id] : platforms.filter((x: string) => x !== p.id) })
                          }}
                          className="rounded border-border" />
                        <span className={p.color}>{p.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div>
                    <label className="text-xs text-text-muted mb-1 block">Spike Threshold</label>
                    <input type="number" value={editingKw.spike_threshold} onChange={e => setEditingKw({ ...editingKw, spike_threshold: parseInt(e.target.value) || 50 })}
                      className="sentinel-input w-24" min={1} />
                  </div>
                  <label className="flex items-center gap-2 text-xs cursor-pointer mt-4">
                    <input type="checkbox" checked={editingKw.alert_on_spike}
                      onChange={e => setEditingKw({ ...editingKw, alert_on_spike: e.target.checked })}
                      className="rounded border-border" />
                    <span className="text-text-muted">Alert on spike</span>
                  </label>
                </div>
                <div className="flex gap-2 justify-end">
                  <button type="button" onClick={() => setEditingKw(null)} className="text-xs border border-border rounded px-3 py-1.5 hover:bg-surface">Cancel</button>
                  <button type="button" onClick={() => updateKeyword(editingKw)} className="text-xs bg-accent-green text-background rounded px-3 py-1.5 hover:bg-accent-green/90 font-bold flex items-center gap-1"><Check className="w-3 h-3" /> Save</button>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="flex gap-1 border-b border-border">
          {(['posts', 'keywords', 'alerts'] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 text-xs font-mono uppercase tracking-wider transition-colors ${tab === t ? 'text-accent-green border-b-2 border-accent-green' : 'text-text-muted hover:text-text-primary'}`}>
              {t} {t === 'alerts' && alerts.filter((a: any) => !a.is_acknowledged).length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 bg-danger/20 text-danger rounded text-[10px]">
                  {alerts.filter((a: any) => !a.is_acknowledged).length}
                </span>
              )}
            </button>
          ))}
        </div>

        {tab === 'posts' && (
          <div className="space-y-2">
            {loading && <div className="text-center text-text-muted font-mono text-xs py-8">LOADING...</div>}
            {!loading && posts.length === 0 && <div className="text-center text-text-muted font-mono text-xs py-8">NO POSTS — ADD KEYWORDS AND TRIGGER A SCAN</div>}
            {posts.map((post) => (
              <div key={post.id} className="sentinel-card hover:bg-background/60 transition-colors">
                <div className="flex items-start gap-3">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 bg-accent-blue/20 text-accent-blue rounded border border-accent-blue/20 uppercase flex-shrink-0 mt-0.5">
                    {post.platform}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      {post.keyword_matched && (
                        <code className="text-[10px] font-mono text-warning bg-warning/10 px-1 rounded">{post.keyword_matched}</code>
                      )}
                      {post.raw_data?.subreddit && (
                        <span className="text-[10px] font-mono text-accent-blue">r/{post.raw_data.subreddit}</span>
                      )}
                      {post.raw_data?.author && (
                        <span className="text-[10px] font-mono text-text-muted">u/{post.raw_data.author}</span>
                      )}
                      {post.sentiment_label && (
                        <span className={cn('text-[10px] font-mono', SENTIMENT_COLORS[post.sentiment_label] || 'text-text-muted')}>
                          {post.sentiment_label}
                        </span>
                      )}
                      <span className="text-[10px] text-text-muted ml-auto font-mono">{formatRelativeTime(post.posted_at)}</span>
                    </div>
                    <p className="text-sm text-text-primary whitespace-pre-line line-clamp-4">{post.content}</p>
                    <div className="flex items-center gap-3 mt-1.5 text-[10px] text-text-muted font-mono">
                      <span>👍 {post.likes}</span>
                      <span>💬 {post.comments}</span>
                      {post.url && (
                        <a href={post.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-accent-blue hover:text-accent-blue/80">
                          Open <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'keywords' && (
          <div className="sentinel-card">
            <div className="overflow-x-auto">
              <table className="sentinel-table min-w-full">
                <thead><tr><th>Keyword</th><th>Platforms</th><th>Status</th><th>Spike</th><th>Last Scanned</th><th>Actions</th></tr></thead>
                <tbody>
                  {keywords.map((kw) => (
                    <tr key={kw.id}>
                      <td><code className="text-xs font-mono text-warning">{kw.keyword}</code></td>
                      <td>
                        <div className="flex gap-1">
                          {(kw.platforms || []).map((p: string) => (
                            <span key={p} className="text-[10px] font-mono px-1 py-0.5 bg-accent-blue/10 text-accent-blue rounded">{p}</span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <button onClick={() => toggleKeyword(kw)} className={`text-xs font-mono ${kw.is_active ? 'text-accent-green' : 'text-danger'}`}>
                          {kw.is_active ? 'ACTIVE' : 'INACTIVE'}
                        </button>
                      </td>
                      <td>
                        <span className="text-[10px] font-mono text-text-muted">
                          {kw.spike_threshold}/hr {kw.alert_on_spike ? '🔔' : ''}
                        </span>
                      </td>
                      <td><span className="text-xs text-text-muted font-mono">{formatRelativeTime(kw.last_scanned)}</span></td>
                      <td>
                        <div className="flex gap-1">
                          <button onClick={() => setEditingKw({ ...kw })} className="p-1 hover:bg-surface rounded" title="Edit">
                            <Edit2 className="w-3 h-3 text-text-muted" />
                          </button>
                          <button onClick={() => deleteKeyword(kw.id)} className="p-1 hover:bg-surface rounded" title="Delete">
                            <Trash2 className="w-3 h-3 text-danger" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tab === 'alerts' && (
          <div className="space-y-2">
            {loading && <div className="text-center text-text-muted font-mono text-xs py-8">LOADING...</div>}
            {!loading && alerts.length === 0 && <div className="text-center text-text-muted font-mono text-xs py-8">NO ALERTS</div>}
            {alerts.map((alert) => (
              <div key={alert.id} className={cn('sentinel-card', alert.is_acknowledged ? 'opacity-60' : '')}>
                <div className="flex items-center gap-3">
                  <Bell className={cn('w-4 h-4', alert.severity === 'HIGH' ? 'text-danger' : 'text-warning')} />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <code className="text-xs font-mono text-warning">{alert.keyword}</code>
                      <span className="text-[10px] font-mono text-text-muted">{alert.platform}</span>
                      <span className={cn('text-[10px] font-mono px-1.5 py-0.5 rounded', alert.severity === 'HIGH' ? 'bg-danger/20 text-danger' : 'bg-warning/20 text-warning')}>
                        {alert.severity}
                      </span>
                      <span className="text-[10px] font-mono text-text-muted">{alert.mention_count} mentions in {alert.window_hours}h</span>
                    </div>
                    <span className="text-[10px] text-text-muted font-mono">{formatRelativeTime(alert.triggered_at)}</span>
                  </div>
                  {!alert.is_acknowledged && (
                    <button onClick={() => acknowledgeAlert(alert.id)}
                      className="text-[10px] font-mono px-2 py-1 border border-border rounded hover:bg-surface text-text-muted flex items-center gap-1">
                      <Check className="w-3 h-3" /> Ack
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
