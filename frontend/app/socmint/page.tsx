'use client'

import { useEffect, useState, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import { ExternalLink, MessageSquare, Plus, RefreshCw } from 'lucide-react'
import { formatRelativeTime, cn } from '@/lib/utils'

const SENTIMENT_COLORS: Record<string, string> = {
  positive: 'text-accent-green', negative: 'text-danger', neutral: 'text-text-muted',
}

export default function SocmintPage() {
  const [posts, setPosts] = useState<any[]>([])
  const [keywords, setKeywords] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'posts' | 'keywords'>('posts')
  const [showAdd, setShowAdd] = useState(false)
  const [newKeyword, setNewKeyword] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [postsRes, kwRes, statsRes] = await Promise.all([
        api.get('/socmint/posts?page_size=30&since_hours=72'),
        api.get('/socmint/keywords'),
        api.get('/socmint/stats'),
      ])
      setPosts(postsRes.data.items)
      setKeywords(kwRes.data)
      setStats(statsRes.data)
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const addKeyword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKeyword.trim()) return
    try {
      await api.post('/socmint/keywords', { keyword: newKeyword, platforms: ['reddit'] })
      setNewKeyword(''); setShowAdd(false)
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
            <p className="text-xs text-text-muted mt-0.5">Monitor Reddit public posts for intelligence signals</p>
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
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Total Posts', value: stats.total_posts },
              { label: 'Posts (24h)', value: stats.posts_24h },
              { label: 'Active Keywords', value: stats.keywords_active },
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
                  className="sentinel-input" placeholder="e.g. Sri Lanka Air Force, SLAF" autoFocus
                  autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
                  data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other"
                  onKeyDown={(e) => { if (e.key === 'Enter') addKeyword({ preventDefault: () => {} } as React.FormEvent) }} />
                <div className="flex gap-2 justify-end">
                  <button type="button" onClick={() => setShowAdd(false)} className="text-xs border border-border rounded px-3 py-1.5 hover:bg-surface">Cancel</button>
                  <button type="button" onClick={() => addKeyword({ preventDefault: () => {} } as React.FormEvent)} className="text-xs bg-warning text-background rounded px-3 py-1.5 hover:bg-warning/90 font-bold">Add</button>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="flex gap-1 border-b border-border">
          {(['posts', 'keywords'] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 text-xs font-mono uppercase tracking-wider transition-colors ${tab === t ? 'text-accent-green border-b-2 border-accent-green' : 'text-text-muted hover:text-text-primary'}`}>
              {t}
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
              <thead><tr><th>Keyword</th><th>Platforms</th><th>Status</th><th>Last Scanned</th></tr></thead>
              <tbody>
                {keywords.map((kw) => (
                  <tr key={kw.id}>
                    <td><code className="text-xs font-mono text-warning">{kw.keyword}</code></td>
                    <td><span className="text-xs text-text-muted">{(kw.platforms || []).join(', ')}</span></td>
                    <td><span className={`text-xs font-mono ${kw.is_active ? 'text-accent-green' : 'text-danger'}`}>{kw.is_active ? 'ACTIVE' : 'INACTIVE'}</span></td>
                    <td><span className="text-xs text-text-muted font-mono">{formatRelativeTime(kw.last_scanned)}</span></td>
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
