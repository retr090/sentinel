'use client'

import { useEffect, useState, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import TimelineChart from '@/components/ui/TimelineChart'
import { Newspaper, ExternalLink, RefreshCw } from 'lucide-react'
import { formatRelativeTime, cn } from '@/lib/utils'

interface Article {
  id: number; title: string; url: string; content_snippet: string;
  category: string; sentiment_label: string; sentiment_score: number;
  language: string; published_at: string; created_at: string
}

const SENTIMENT_COLORS: Record<string, string> = {
  positive: 'text-accent-green', negative: 'text-danger', neutral: 'text-text-muted',
}

const CATEGORIES = ['', 'regional', 'military', 'cyber', 'politics', 'general']

export default function NewsPage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [timeline, setTimeline] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('')
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const fetchArticles = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '20', since_hours: '72' })
      if (category) params.set('category', category)
      if (keyword) params.set('keyword', keyword)
      const [artRes, tlRes, statsRes] = await Promise.all([
        api.get(`/news/articles?${params}`),
        api.get('/news/timeline?days=7'),
        api.get('/news/stats'),
      ])
      setArticles(artRes.data.items)
      setTotal(artRes.data.total)
      setTimeline(tlRes.data)
      setStats(statsRes.data)
    } catch {}
    setLoading(false)
  }, [page, category, keyword])

  useEffect(() => { fetchArticles() }, [fetchArticles])

  return (
    <AppLayout title="SENTINEL / News Intelligence">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              <Newspaper className="w-5 h-5 text-accent-green" /> News Intelligence
            </h1>
            <p className="text-xs text-text-muted mt-0.5">Multi-source news aggregation and sentiment analysis</p>
          </div>
          <button onClick={() => { api.post('/news/fetch-now').catch(() => {}) }}
            className="flex items-center gap-1.5 text-xs border border-border rounded px-3 py-1.5 hover:bg-surface transition-colors text-text-muted">
            <RefreshCw className="w-3.5 h-3.5" /> Fetch Now
          </button>
        </div>

        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Total Articles', value: stats.total_articles },
              { label: 'Articles (24h)', value: stats.articles_24h },
              { label: 'Active Sources', value: stats.sources_active },
              { label: 'Open Alerts', value: stats.alerts_open },
            ].map((s) => (
              <div key={s.label} className="sentinel-card text-center">
                <div className="text-xl font-bold font-mono text-accent-green">{s.value}</div>
                <div className="text-xs text-text-muted mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Timeline */}
        <div className="sentinel-card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold font-mono">ARTICLE VOLUME — 7 DAYS</h2>
          </div>
          <TimelineChart data={timeline} color="#00ff88" label="Articles" height={140} />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2">
          <input type="text" value={keyword} onChange={e => { setKeyword(e.target.value); setPage(1) }}
            placeholder="Filter by keyword..." className="sentinel-input max-w-xs"
            autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
            data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other" />
          <div className="flex gap-1">
            {CATEGORIES.map((cat) => (
              <button key={cat} onClick={() => { setCategory(cat); setPage(1) }}
                className={`text-xs px-3 py-1.5 rounded font-mono transition-colors ${category === cat ? 'bg-accent-green/20 text-accent-green border border-accent-green/30' : 'border border-border text-text-muted hover:text-text-primary'}`}>
                {cat || 'ALL'}
              </button>
            ))}
          </div>
        </div>

        {/* Articles */}
        <div className="space-y-2">
          {loading && <div className="text-center text-text-muted font-mono text-xs py-8">LOADING...</div>}
          {!loading && articles.length === 0 && <div className="text-center text-text-muted font-mono text-xs py-8">NO ARTICLES FOUND</div>}
          {articles.map((article) => (
            <div key={article.id} className="sentinel-card hover:bg-background/60 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    {article.category && (
                      <span className="text-[9px] font-mono px-1.5 py-0.5 bg-accent-blue/20 text-accent-blue rounded border border-accent-blue/20 uppercase">
                        {article.category}
                      </span>
                    )}
                    {article.sentiment_label && (
                      <span className={cn('text-[10px] font-mono', SENTIMENT_COLORS[article.sentiment_label] || 'text-text-muted')}>
                        {article.sentiment_label} ({article.sentiment_score?.toFixed(2)})
                      </span>
                    )}
                    <span className="text-[10px] text-text-muted ml-auto font-mono">{formatRelativeTime(article.published_at)}</span>
                  </div>
                  <h3 className="text-sm font-medium text-text-primary line-clamp-2">{article.title}</h3>
                  {article.content_snippet && (
                    <p className="text-xs text-text-muted mt-1 line-clamp-2">{article.content_snippet}</p>
                  )}
                </div>
                {article.url && (
                  <a href={article.url} target="_blank" rel="noopener noreferrer"
                    className="text-text-muted hover:text-accent-blue flex-shrink-0 mt-0.5">
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>

        {total > 20 && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-muted font-mono">Showing {(page-1)*20+1}–{Math.min(page*20,total)} of {total}</span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1} className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30 hover:bg-surface">Prev</button>
              <button onClick={() => setPage(p => p+1)} disabled={page*20>=total} className="text-xs border border-border px-2 py-1 rounded disabled:opacity-30 hover:bg-surface">Next</button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
