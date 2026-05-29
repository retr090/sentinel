'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import { formatRelativeTime, cn } from '@/lib/utils'
import {
  Newspaper, RefreshCw, ExternalLink, ChevronDown,
  Hash, AlertTriangle, Search, Brain, Target,
} from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Article {
  id: number
  source_id: number | null
  title: string
  url: string | null
  content_snippet: string | null
  full_text: string | null
  category: string | null
  sentiment_label: string | null
  sentiment_score: number | null
  keywords_matched: string[] | null
  language: string
  relevance_score: number | null
  relevance_label: string | null
  ai_analysis: NewsAiAnalysis | null
  published_at: string | null
  created_at: string
}

interface NewsAiAnalysis {
  category?: string
  risk_level?: string
  event_type?: string
  key_points?: string[]
  security_implications?: string[]
  entities?: string[]
  locations?: string[]
  watch_terms?: string[]
  recommended_action?: string
  confidence?: string
  generated_by?: string
  model?: string
}

interface NewsSource {
  id: number
  name: string
  url: string
  category: string
  language: string
  is_active: boolean
  last_fetched: string | null
}

interface Stats {
  total_articles: number
  articles_24h: number
  sources_active: number
  alerts_open: number
  category_counts: Record<string, number>
  language_counts: Record<string, number>
}

interface TrendingKeyword {
  keyword: string
  count: number
}

// ─── Constants ────────────────────────────────────────────────────────────────

const RELEVANCE_DOT: Record<string, string> = {
  high:   'bg-danger',
  medium: 'bg-accent-yellow',
  low:    'bg-border',
}

const RELEVANCE_BADGE: Record<string, string> = {
  high:       'bg-danger/15 text-danger border-danger/30',
  medium:     'bg-accent-yellow/15 text-accent-yellow border-accent-yellow/30',
  low:        'bg-surface text-text-muted border-border',
  irrelevant: 'bg-surface text-text-muted border-border opacity-50',
}

const SENTIMENT_COLOR: Record<string, string> = {
  positive: 'text-accent-green',
  negative: 'text-danger',
  neutral:  'text-text-muted',
}

const RISK_BADGE: Record<string, string> = {
  critical: 'bg-danger/15 text-danger border-danger/30',
  high:     'bg-danger/10 text-danger border-danger/25',
  medium:   'bg-accent-yellow/15 text-accent-yellow border-accent-yellow/30',
  low:      'bg-accent-blue/10 text-accent-blue border-accent-blue/20',
  none:     'bg-surface text-text-muted border-border',
}

const LANG_LABEL: Record<string, string> = { en: 'EN', si: 'SI', ta: 'TA' }

const CATEGORIES = ['regional', 'cyber', 'military', 'general', 'politics'] as const
const LANGUAGES  = ['en', 'si', 'ta'] as const
const RELEVANCES = ['high', 'medium', 'low'] as const
const TIME_OPTS  = [
  { label: '24 h',  value: 24 },
  { label: '72 h',  value: 72 },
  { label: '7 d',   value: 168 },
  { label: '30 d',  value: 720 },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function sourceFreshness(last_fetched: string | null): 'fresh' | 'stale' | 'dead' {
  if (!last_fetched) return 'dead'
  const hrs = (Date.now() - new Date(last_fetched).getTime()) / 3_600_000
  if (hrs < 4)  return 'fresh'
  if (hrs < 12) return 'stale'
  return 'dead'
}

const FRESH_DOT: Record<string, string> = {
  fresh: 'bg-accent-green',
  stale: 'bg-accent-yellow',
  dead:  'bg-danger',
}

// ─── Left Pane ────────────────────────────────────────────────────────────────

function LeftPane({
  stats, sources, trending,
  category, setCategory,
  language, setLanguage,
  relevance, setRelevance,
  keyword, setKeyword,
  onFetch,
}: {
  stats: Stats | null
  sources: NewsSource[]
  trending: TrendingKeyword[]
  category: string; setCategory: (v: string) => void
  language: string; setLanguage: (v: string) => void
  relevance: string; setRelevance: (v: string) => void
  keyword: string; setKeyword: (v: string) => void
  onFetch: () => void
}) {
  const [sourcesExpanded, setSourcesExpanded] = useState(false)
  const visibleSources = sourcesExpanded ? sources : sources.slice(0, 8)

  return (
    <div className="w-52 flex-shrink-0 border-r border-border flex flex-col overflow-hidden bg-surface/30">
      {/* Header */}
      <div className="px-3 pt-3 pb-2 border-b border-border flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <Newspaper className="w-3.5 h-3.5 text-accent-green" />
            <span className="text-[10px] font-mono font-bold text-accent-green uppercase tracking-widest">News Intel</span>
          </div>
          <button
            onClick={onFetch}
            title="Fetch now"
            className="p-1 text-text-muted hover:text-accent-green transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-text-muted pointer-events-none" />
          <input
            type="text"
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            placeholder="Search articles..."
            className="w-full bg-background border border-border rounded text-[11px] font-mono pl-6 pr-2 py-1.5 text-text-primary focus:outline-none focus:border-accent-green/50 placeholder:text-text-muted/50"
            autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false}
            data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other"
          />
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-4">

        {/* CATEGORY */}
        <div>
          <div className="text-[9px] font-mono text-text-muted/60 uppercase tracking-[0.2em] px-1 mb-1">Category</div>
          <button
            onClick={() => setCategory('')}
            className={cn('w-full text-left flex items-center justify-between px-2 py-1 rounded text-[11px] font-mono transition-colors',
              category === '' ? 'bg-accent-green/10 text-accent-green' : 'text-text-muted hover:text-text-primary hover:bg-background/50')}
          >
            <span>All</span>
            <span className="text-[10px] opacity-60">{stats?.articles_24h ?? 0}</span>
          </button>
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setCategory(cat === category ? '' : cat)}
              className={cn('w-full text-left flex items-center justify-between px-2 py-1 rounded text-[11px] font-mono transition-colors capitalize',
                category === cat ? 'bg-accent-green/10 text-accent-green' : 'text-text-muted hover:text-text-primary hover:bg-background/50')}
            >
              <span>{cat}</span>
              {stats?.category_counts?.[cat] ? (
                <span className="text-[10px] opacity-60">{stats.category_counts[cat]}</span>
              ) : null}
            </button>
          ))}
        </div>

        {/* LANGUAGE */}
        <div>
          <div className="text-[9px] font-mono text-text-muted/60 uppercase tracking-[0.2em] px-1 mb-1">Language</div>
          <button
            onClick={() => setLanguage('')}
            className={cn('w-full text-left flex items-center justify-between px-2 py-1 rounded text-[11px] font-mono transition-colors',
              language === '' ? 'bg-accent-green/10 text-accent-green' : 'text-text-muted hover:text-text-primary hover:bg-background/50')}
          >
            <span>All languages</span>
          </button>
          {LANGUAGES.map(lang => (
            <button
              key={lang}
              onClick={() => setLanguage(lang === language ? '' : lang)}
              className={cn('w-full text-left flex items-center justify-between px-2 py-1 rounded text-[11px] font-mono transition-colors',
                language === lang ? 'bg-accent-green/10 text-accent-green' : 'text-text-muted hover:text-text-primary hover:bg-background/50')}
            >
              <span>{LANG_LABEL[lang]}</span>
              {stats?.language_counts?.[lang] ? (
                <span className="text-[10px] opacity-60">{stats.language_counts[lang]}</span>
              ) : null}
            </button>
          ))}
        </div>

        {/* RELEVANCE */}
        <div>
          <div className="text-[9px] font-mono text-text-muted/60 uppercase tracking-[0.2em] px-1 mb-1">Relevance</div>
          <button
            onClick={() => setRelevance('')}
            className={cn('w-full text-left px-2 py-1 rounded text-[11px] font-mono transition-colors',
              relevance === '' ? 'bg-accent-green/10 text-accent-green' : 'text-text-muted hover:text-text-primary hover:bg-background/50')}
          >
            All
          </button>
          {RELEVANCES.map(rel => (
            <button
              key={rel}
              onClick={() => setRelevance(rel === relevance ? '' : rel)}
              className={cn('w-full text-left flex items-center gap-2 px-2 py-1 rounded text-[11px] font-mono transition-colors capitalize',
                relevance === rel ? 'bg-accent-green/10 text-accent-green' : 'text-text-muted hover:text-text-primary hover:bg-background/50')}
            >
              <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', RELEVANCE_DOT[rel])} />
              {rel}
            </button>
          ))}
        </div>

        {/* SOURCES */}
        {sources.length > 0 && (
          <div>
            <div className="text-[9px] font-mono text-text-muted/60 uppercase tracking-[0.2em] px-1 mb-1">
              Sources ({stats?.sources_active ?? sources.length} active)
            </div>
            <div className="space-y-0.5">
              {visibleSources.map(src => {
                const fresh = sourceFreshness(src.last_fetched)
                return (
                  <div key={src.id} className="flex items-center gap-2 px-2 py-1 rounded hover:bg-background/50 transition-colors">
                    <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', FRESH_DOT[fresh])} />
                    <span className="text-[10px] font-mono text-text-muted truncate flex-1" title={src.name}>{src.name}</span>
                    <span className="text-[9px] font-mono text-text-muted/40 uppercase flex-shrink-0">{src.language}</span>
                  </div>
                )
              })}
            </div>
            {sources.length > 8 && (
              <button
                onClick={() => setSourcesExpanded(e => !e)}
                className="flex items-center gap-1 px-2 pt-1 text-[10px] font-mono text-text-muted/60 hover:text-text-muted transition-colors"
              >
                <ChevronDown className={cn('w-3 h-3 transition-transform', sourcesExpanded && 'rotate-180')} />
                {sourcesExpanded ? 'Show less' : `+${sources.length - 8} more`}
              </button>
            )}
          </div>
        )}

        {/* TRENDING KEYWORDS */}
        {trending.length > 0 && (
          <div>
            <div className="text-[9px] font-mono text-text-muted/60 uppercase tracking-[0.2em] px-1 mb-1">Trending (24h)</div>
            <div className="space-y-0.5">
              {trending.map(t => (
                <button
                  key={t.keyword}
                  onClick={() => setKeyword(t.keyword === keyword ? '' : t.keyword)}
                  className={cn('w-full text-left flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-mono transition-colors',
                    keyword === t.keyword ? 'bg-accent-green/10 text-accent-green' : 'text-text-muted hover:text-text-primary hover:bg-background/50')}
                >
                  <Hash className="w-3 h-3 flex-shrink-0 opacity-50" />
                  <span className="truncate flex-1">{t.keyword}</span>
                  <span className="text-[10px] opacity-50 flex-shrink-0">{t.count}</span>
                </button>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* Alerts footer */}
      {(stats?.alerts_open ?? 0) > 0 && (
        <div className="px-3 py-2 border-t border-border flex-shrink-0">
          <div className="flex items-center gap-2 text-[10px] font-mono text-accent-yellow">
            <AlertTriangle className="w-3 h-3 flex-shrink-0" />
            {stats!.alerts_open} open alert{stats!.alerts_open !== 1 ? 's' : ''}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Center Pane ──────────────────────────────────────────────────────────────

function CenterPane({
  articles, loading, total, sinceHours, setSinceHours,
  selectedId, onSelect, onLoadMore, hasMore, sourceMap,
}: {
  articles: Article[]
  loading: boolean
  total: number
  sinceHours: number
  setSinceHours: (v: number) => void
  selectedId: number | null
  onSelect: (a: Article) => void
  onLoadMore: () => void
  hasMore: boolean
  sourceMap: Record<number, NewsSource>
}) {
  return (
    <div className="w-80 flex-shrink-0 border-r border-border flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2 border-b border-border flex items-center justify-between gap-2 flex-shrink-0 bg-surface/20">
        <span className="text-[11px] font-mono text-text-muted">
          {loading ? '...' : `${total.toLocaleString()} articles`}
        </span>
        <select
          value={sinceHours}
          onChange={e => setSinceHours(Number(e.target.value))}
          className="bg-background border border-border rounded px-1.5 py-0.5 text-[10px] font-mono text-text-muted focus:outline-none focus:border-accent-green/50"
        >
          {TIME_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {/* Article list */}
      <div className="flex-1 overflow-y-auto">
        {loading && articles.length === 0 && (
          <div className="space-y-px">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="px-3 py-3 animate-pulse border-b border-border/40">
                <div className="h-2.5 w-20 bg-border/40 rounded mb-2" />
                <div className="h-3 w-full bg-border/40 rounded mb-1" />
                <div className="h-3 w-4/5 bg-border/30 rounded" />
              </div>
            ))}
          </div>
        )}

        {!loading && articles.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center p-6">
            <Newspaper className="w-8 h-8 text-text-muted/30 mb-3" />
            <p className="text-xs text-text-muted font-mono">No articles found</p>
          </div>
        )}

        {articles.map(article => {
          const src = article.source_id ? sourceMap[article.source_id] : null
          const isSelected = article.id === selectedId
          const relDot = article.relevance_label ? RELEVANCE_DOT[article.relevance_label] : 'bg-border/40'

          return (
            <button
              key={article.id}
              onClick={() => onSelect(article)}
              className={cn(
                'w-full text-left px-3 py-2.5 border-b border-border/40 transition-colors',
                'hover:bg-surface/60',
                isSelected && 'bg-surface border-l-2 border-l-accent-green',
              )}
            >
              {/* Meta row */}
              <div className="flex items-center gap-1.5 mb-1">
                <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', relDot)} />
                <span className="text-[10px] font-mono text-text-muted truncate flex-1">
                  {src?.name ?? 'Unknown'}
                </span>
                {article.language !== 'en' && (
                  <span className="text-[9px] font-mono px-1 py-0.5 bg-accent-yellow/10 text-accent-yellow rounded flex-shrink-0">
                    {LANG_LABEL[article.language] ?? article.language}
                  </span>
                )}
                <span className="text-[10px] font-mono text-text-muted/50 flex-shrink-0">
                  {formatRelativeTime(article.published_at ?? article.created_at)}
                </span>
              </div>

              {/* Title */}
              <p className={cn(
                'text-[12px] font-medium leading-snug line-clamp-2',
                isSelected ? 'text-text-primary' : 'text-text-primary/90',
              )}>
                {article.title}
              </p>

              {/* Tags row */}
              <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                {article.category && (
                  <span className="text-[9px] font-mono px-1 py-0.5 bg-accent-blue/10 text-accent-blue/80 rounded uppercase">
                    {article.category}
                  </span>
                )}
                {(article.keywords_matched?.length ?? 0) > 0 && (
                  <span className="text-[9px] font-mono text-text-muted/50 flex items-center gap-0.5">
                    <Hash className="w-2.5 h-2.5" />{article.keywords_matched!.length}
                  </span>
                )}
              </div>
            </button>
          )
        })}

        {hasMore && (
          <button
            onClick={onLoadMore}
            disabled={loading}
            className="w-full py-3 text-[11px] font-mono text-text-muted hover:text-text-primary transition-colors border-t border-border/40 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Load more'}
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Right Pane ───────────────────────────────────────────────────────────────

function RightPane({ article, sourceMap }: { article: Article | null; sourceMap: Record<number, NewsSource> }) {
  if (!article) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-background/20">
        <div className="w-20 h-20 rounded-full border-2 border-dashed border-border/40 flex items-center justify-center mb-4">
          <Newspaper className="w-8 h-8 text-text-muted/30" />
        </div>
        <p className="text-sm font-mono text-text-muted">Select an article to read</p>
        <p className="text-xs font-mono text-text-muted/50 mt-1">Click any item in the list</p>
      </div>
    )
  }

  const src = article.source_id ? sourceMap[article.source_id] : null
  const relScore = article.relevance_score ?? 0
  const relPct = Math.round(relScore * 100)
  const ai = article.ai_analysis

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Reading area */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

        {/* Badges */}
        <div className="flex items-center gap-2 flex-wrap">
          {article.category && (
            <span className="text-[10px] font-mono px-2 py-0.5 bg-accent-blue/10 text-accent-blue border border-accent-blue/20 rounded uppercase tracking-wide">
              {article.category}
            </span>
          )}
          {article.relevance_label && (
            <span className={cn('text-[10px] font-mono px-2 py-0.5 rounded border uppercase tracking-wide', RELEVANCE_BADGE[article.relevance_label])}>
              {article.relevance_label}
            </span>
          )}
          {article.language !== 'en' && (
            <span className="text-[10px] font-mono px-2 py-0.5 bg-accent-yellow/10 text-accent-yellow border border-accent-yellow/20 rounded">
              {LANG_LABEL[article.language] ?? article.language}
            </span>
          )}
          {article.sentiment_label && (
            <span className={cn('text-[10px] font-mono', SENTIMENT_COLOR[article.sentiment_label] ?? 'text-text-muted')}>
              {article.sentiment_label}
              {article.sentiment_score != null && ` (${article.sentiment_score.toFixed(2)})`}
            </span>
          )}
        </div>

        {/* Title */}
        <h2 className="text-base font-bold text-text-primary leading-snug">{article.title}</h2>

        {/* Meta */}
        <div className="flex items-center gap-2 text-[11px] font-mono text-text-muted flex-wrap border-b border-border/40 pb-4">
          {src && <span className="text-accent-green/80">{src.name}</span>}
          {src && <span className="text-border">·</span>}
          <span>{formatRelativeTime(article.published_at ?? article.created_at)}</span>
          {article.published_at && (
            <span className="text-text-muted/40">
              {new Date(article.published_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
            </span>
          )}
        </div>

        {/* Relevance bar */}
        {article.relevance_score != null && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[10px] font-mono text-text-muted">
              <span>Relevance to Sri Lanka</span>
              <span className={cn(
                article.relevance_label === 'high' ? 'text-danger'
                : article.relevance_label === 'medium' ? 'text-accent-yellow'
                : 'text-text-muted'
              )}>{relPct}%</span>
            </div>
            <div className="h-1 bg-border rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all',
                  article.relevance_label === 'high' ? 'bg-danger'
                  : article.relevance_label === 'medium' ? 'bg-accent-yellow'
                  : 'bg-border')}
                style={{ width: `${relPct}%` }}
              />
            </div>
          </div>
        )}

        {/* AI analysis */}
        {ai && (
          <div className="rounded border border-accent-green/20 bg-accent-green/5 p-3 space-y-3">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                <Brain className="w-3.5 h-3.5 text-accent-green" />
                <span className="text-[10px] font-mono font-bold text-accent-green uppercase tracking-widest">AI Analysis</span>
              </div>
              <div className="flex items-center gap-1.5 flex-wrap">
                {ai.category && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-border text-text-muted uppercase">
                    {ai.category.replaceAll('_', ' ')}
                  </span>
                )}
                {ai.risk_level && (
                  <span className={cn('text-[10px] font-mono px-2 py-0.5 rounded border uppercase', RISK_BADGE[ai.risk_level] ?? RISK_BADGE.none)}>
                    {ai.risk_level}
                  </span>
                )}
                {ai.confidence && (
                  <span className="text-[10px] font-mono text-text-muted uppercase">
                    {ai.confidence} confidence
                  </span>
                )}
              </div>
            </div>

            {ai.event_type && (
              <div className="text-xs font-mono text-text-primary">
                <span className="text-text-muted">Event:</span> {ai.event_type}
              </div>
            )}

            {(ai.key_points?.length ?? 0) > 0 && (
              <div className="space-y-1.5">
                <div className="text-[10px] font-mono text-text-muted/60 uppercase tracking-widest">Key Signals</div>
                <ul className="space-y-1">
                  {ai.key_points!.slice(0, 4).map(point => (
                    <li key={point} className="text-xs text-text-primary/90 leading-relaxed flex gap-2">
                      <span className="text-accent-green mt-0.5">▸</span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {(ai.security_implications?.length ?? 0) > 0 && (
              <div className="space-y-1.5">
                <div className="text-[10px] font-mono text-text-muted/60 uppercase tracking-widest">Security Implications</div>
                <ul className="space-y-1">
                  {ai.security_implications!.slice(0, 3).map(item => (
                    <li key={item} className="text-xs text-text-primary/90 leading-relaxed flex gap-2">
                      <span className="text-accent-yellow mt-0.5">→</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {ai.recommended_action && (
              <div className="flex items-start gap-2 text-xs font-mono text-text-primary border-t border-border/40 pt-2">
                <Target className="w-3.5 h-3.5 text-accent-yellow mt-0.5 flex-shrink-0" />
                <span>{ai.recommended_action}</span>
              </div>
            )}

            {(ai.entities?.length ?? 0) > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {ai.entities!.slice(0, 8).map(entity => (
                  <span key={entity} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-background/60 border border-border text-text-muted">
                    {entity}
                  </span>
                ))}
              </div>
            )}

            {(ai.watch_terms?.length ?? 0) > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1 border-t border-border/40">
                {ai.watch_terms!.slice(0, 8).map(term => (
                  <span key={term} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent-blue/10 border border-accent-blue/20 text-accent-blue">
                    {term}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Matched keywords */}
        {(article.keywords_matched?.length ?? 0) > 0 && (
          <div className="space-y-2">
            <div className="text-[10px] font-mono text-text-muted/60 uppercase tracking-widest">Matched Keywords</div>
            <div className="flex flex-wrap gap-1.5">
              {article.keywords_matched!.map(kw => (
                <span key={kw} className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 bg-accent-green/10 text-accent-green border border-accent-green/20 rounded">
                  <Hash className="w-2.5 h-2.5 opacity-60" />{kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Article extract */}
        {(article.full_text || article.content_snippet) && (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-[10px] font-mono text-text-muted/60 uppercase tracking-widest">
                Article Extract
              </div>
              {article.full_text && (
                <span className="text-[10px] font-mono text-accent-green">
                  {Math.min(article.full_text.length, 8000).toLocaleString()} chars captured
                </span>
              )}
            </div>
            <div className="rounded border border-border bg-background/60 p-3 max-h-72 overflow-y-auto">
              <p className="text-sm text-text-primary/90 leading-relaxed whitespace-pre-line">
                {article.full_text || article.content_snippet}
              </p>
            </div>
          </div>
        )}

      </div>

      {/* Footer action */}
      {article.url && (
        <div className="px-6 py-3 border-t border-border flex-shrink-0 bg-surface/20">
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full py-2 bg-accent-green text-background font-bold text-sm rounded hover:bg-accent-green/90 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            Open Full Article
          </a>
        </div>
      )}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const PAGE_SIZE = 40

export default function NewsPage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [sources, setSources] = useState<NewsSource[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [trending, setTrending] = useState<TrendingKeyword[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)

  const [category, setCategory]   = useState('')
  const [language, setLanguage]   = useState('')
  const [relevance, setRelevance] = useState('')
  const [keyword, setKeyword]     = useState('')
  const [sinceHours, setSinceHours] = useState(72)

  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null)

  const sourceMap: Record<number, NewsSource> = Object.fromEntries(sources.map(s => [s.id, s]))

  const hasMore = articles.length < total

  const fetchArticles = useCallback(async (reset = false) => {
    setLoading(true)
    try {
      const p = reset ? 1 : page
      const params = new URLSearchParams({
        page: String(p), page_size: String(PAGE_SIZE), since_hours: String(sinceHours),
      })
      if (category) params.set('category', category)
      if (language) params.set('language', language)
      if (relevance) params.set('relevance', relevance)
      if (keyword)  params.set('keyword', keyword)
      const { data } = await api.get(`/news/articles?${params}`)
      setArticles(prev => reset ? data.items : [...prev, ...data.items])
      setTotal(data.total)
      if (reset) setPage(1)
    } catch {}
    setLoading(false)
  }, [page, category, language, relevance, keyword, sinceHours])

  const fetchMeta = useCallback(async () => {
    try {
      const [srcRes, statsRes, trendRes] = await Promise.allSettled([
        api.get('/news/sources'),
        api.get('/news/stats'),
        api.get('/news/trending-keywords'),
      ])
      if (srcRes.status === 'fulfilled')   setSources(srcRes.value.data)
      if (statsRes.status === 'fulfilled') setStats(statsRes.value.data)
      if (trendRes.status === 'fulfilled') setTrending(trendRes.value.data)
    } catch {}
  }, [])

  // Reset on filter change
  const filtersRef = useRef({ category, language, relevance, keyword, sinceHours })
  useEffect(() => {
    const prev = filtersRef.current
    const changed = prev.category !== category || prev.language !== language ||
      prev.relevance !== relevance || prev.keyword !== keyword || prev.sinceHours !== sinceHours
    if (changed) {
      filtersRef.current = { category, language, relevance, keyword, sinceHours }
      setArticles([])
      setPage(1)
      setSelectedArticle(null)
      fetchArticles(true)
    }
  }, [category, language, relevance, keyword, sinceHours]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchArticles(true); fetchMeta() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleLoadMore = useCallback(async () => {
    const nextPage = page + 1
    setPage(nextPage)
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: String(nextPage), page_size: String(PAGE_SIZE), since_hours: String(sinceHours),
      })
      if (category) params.set('category', category)
      if (language) params.set('language', language)
      if (relevance) params.set('relevance', relevance)
      if (keyword)  params.set('keyword', keyword)
      const { data } = await api.get(`/news/articles?${params}`)
      setArticles(prev => [...prev, ...data.items])
      setTotal(data.total)
    } catch {}
    setLoading(false)
  }, [page, category, language, relevance, keyword, sinceHours])

  const handleFetch = () => {
    api.post('/news/fetch-now').catch(() => {})
    setTimeout(() => { fetchMeta(); fetchArticles(true) }, 2000)
  }

  return (
    <AppLayout title="SENTINEL / News Intelligence">
      {/* Break out of AppLayout padding, fill remaining height */}
      <div
        className="-m-3 md:-m-4 lg:-m-6 flex overflow-hidden"
        style={{ height: 'calc(100vh - 3.5rem)' }}
      >
        <LeftPane
          stats={stats} sources={sources} trending={trending}
          category={category} setCategory={v => { setCategory(v); setSelectedArticle(null) }}
          language={language} setLanguage={v => { setLanguage(v); setSelectedArticle(null) }}
          relevance={relevance} setRelevance={v => { setRelevance(v); setSelectedArticle(null) }}
          keyword={keyword} setKeyword={v => { setKeyword(v); setSelectedArticle(null) }}
          onFetch={handleFetch}
        />

        <CenterPane
          articles={articles} loading={loading} total={total}
          sinceHours={sinceHours} setSinceHours={v => { setSinceHours(v); setSelectedArticle(null) }}
          selectedId={selectedArticle?.id ?? null}
          onSelect={setSelectedArticle}
          onLoadMore={handleLoadMore}
          hasMore={hasMore}
          sourceMap={sourceMap}
        />

        <RightPane article={selectedArticle} sourceMap={sourceMap} />
      </div>
    </AppLayout>
  )
}
