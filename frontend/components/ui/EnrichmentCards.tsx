'use client'

import { useState, type ReactNode } from 'react'
import { ChevronDown, ChevronUp, Copy, Check, ExternalLink, MapPin } from 'lucide-react'

// ---- Utilities ----

function notEmpty(v: any): boolean {
  return v !== null && v !== undefined && v !== ''
}

// ---- Copy Raw JSON toggle ----

function CopyRawJSON({ data }: { data: any }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="mt-3 border-t border-border/50 pt-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-[10px] text-text-muted hover:text-text-primary font-mono transition-colors"
      >
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        Raw JSON
      </button>
      {open && (
        <div className="relative mt-2">
          <button
            onClick={copy}
            className="absolute top-1 right-1 z-10 flex items-center gap-1 text-[9px] text-text-muted hover:text-text-primary font-mono px-1.5 py-0.5 bg-background rounded border border-border transition-colors"
          >
            {copied ? (
              <Check className="w-3 h-3 text-accent-green" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <pre className="text-[9px] text-text-muted font-mono bg-background/60 rounded p-2 overflow-x-auto max-h-48 pr-14">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

// ---- Card shell ----

function CardShell({
  title,
  children,
  data,
  error,
}: {
  title: string
  children?: ReactNode
  data: any
  error?: boolean
}) {
  return (
    <div className="bg-surface rounded-lg p-3 border border-border/60">
      <div className="text-[10px] font-mono text-accent-green uppercase mb-2 tracking-wider">
        {title}
      </div>
      {error ? (
        <span className="text-xs text-text-muted font-mono">Source unavailable</span>
      ) : (
        children
      )}
      {data != null && <CopyRawJSON data={data} />}
    </div>
  )
}

// ---- Shared sub-components ----

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-2 text-xs py-0.5">
      <span className="text-text-muted font-mono w-20 shrink-0 text-[11px]">{label}</span>
      <span className="text-text-primary font-mono break-all text-[11px]">{children}</span>
    </div>
  )
}

const BADGE_VARIANTS: Record<string, string> = {
  green: 'bg-accent-green/10 text-accent-green border-accent-green/30',
  red: 'bg-danger/20 text-danger border-danger/40',
  blue: 'bg-accent-blue/10 text-accent-blue border-accent-blue/30',
  yellow: 'bg-warning/10 text-warning border-warning/30',
  muted: 'bg-border/50 text-text-muted border-border',
}

function Badge({
  label,
  variant = 'muted',
}: {
  label: string
  variant?: keyof typeof BADGE_VARIANTS
}) {
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono rounded border ${
        BADGE_VARIANTS[variant] ?? BADGE_VARIANTS.muted
      }`}
    >
      {label}
    </span>
  )
}

// ---- GreyNoise card ----

const CLASSIFICATION_COLORS: Record<string, string> = {
  malicious: 'bg-danger/20 text-danger border-danger/40',
  benign: 'bg-accent-green/10 text-accent-green border-accent-green/30',
  unknown: 'bg-border/50 text-text-muted border-border',
}

function GreyNoiseCard({ data }: { data: any }) {
  if (!data || data.error) {
    return (
      <CardShell title="GREYNOISE" data={data ?? null} error>
        {null}
      </CardShell>
    )
  }

  const cls = (data.classification ?? 'unknown').toLowerCase()
  const ip = data.ip

  return (
    <CardShell title="GREYNOISE" data={data}>
      <div className="space-y-2">
        {notEmpty(data.classification) && (
          <div className="flex items-center gap-2">
            <span className="text-text-muted font-mono text-[11px] w-20 shrink-0">
              Classification
            </span>
            <span
              className={`px-2 py-0.5 text-[10px] font-mono rounded border ${
                CLASSIFICATION_COLORS[cls] ?? CLASSIFICATION_COLORS.unknown
              }`}
            >
              {data.classification.toUpperCase()}
            </span>
          </div>
        )}
        <div className="flex items-center gap-1.5 flex-wrap">
          {data.noise !== undefined && (
            <Badge
              label={`NOISE: ${data.noise ? 'YES' : 'NO'}`}
              variant={data.noise ? 'red' : 'muted'}
            />
          )}
          {data.riot !== undefined && (
            <Badge
              label={`RIOT: ${data.riot ? 'YES' : 'NO'}`}
              variant={data.riot ? 'green' : 'muted'}
            />
          )}
        </div>
        {notEmpty(data.name) && <Row label="Name">{data.name}</Row>}
        {notEmpty(data.message) && <Row label="Message">{data.message}</Row>}
        {notEmpty(ip) && (
          <a
            href={`https://viz.greynoise.io/ip/${ip}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[10px] font-mono text-accent-blue hover:text-accent-blue/80 transition-colors mt-1"
          >
            View in GreyNoise <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </CardShell>
  )
}

// ---- IPInfo card ----

function IPInfoCard({ data }: { data: any }) {
  if (!data || data.error) {
    return (
      <CardShell title="IPINFO" data={data ?? null} error>
        {null}
      </CardShell>
    )
  }

  const [lat, lon] = (data.loc ?? '').split(',')
  const hasCoords = notEmpty(lat) && notEmpty(lon)

  return (
    <CardShell title="IPINFO" data={data}>
      <div className="space-y-0.5">
        {notEmpty(data.ip) && <Row label="IP">{data.ip}</Row>}
        {notEmpty(data.city) && <Row label="City">{data.city}</Row>}
        {notEmpty(data.region) && <Row label="Region">{data.region}</Row>}
        {notEmpty(data.country) && <Row label="Country">{data.country}</Row>}
        {notEmpty(data.org) && <Row label="ASN / Org">{data.org}</Row>}
        {hasCoords && (
          <div className="flex items-start gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-20 shrink-0">Location</span>
            <a
              href={`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=10`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-accent-blue hover:text-accent-blue/80 font-mono transition-colors"
            >
              <MapPin className="w-3 h-3 shrink-0" />
              {lat}, {lon}
            </a>
          </div>
        )}
      </div>
    </CardShell>
  )
}

// ---- AlienVault OTX card ----

function AlienVaultCard({ data }: { data: any }) {
  if (!data || data.error) {
    return (
      <CardShell title="ALIENVAULT OTX" data={data ?? null} error>
        {null}
      </CardShell>
    )
  }

  const pulseCount: number | undefined = data.pulse_info?.count
  const reputation: number | undefined = data.reputation

  return (
    <CardShell title="ALIENVAULT OTX" data={data}>
      <div className="space-y-0.5">
        {notEmpty(data.indicator) && <Row label="Indicator">{data.indicator}</Row>}
        {notEmpty(data.type) && <Row label="Type">{data.type}</Row>}
        {notEmpty(data.type_title) && <Row label="Type Title">{data.type_title}</Row>}
        {reputation !== undefined && reputation !== null && (
          <div className="flex items-start gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-20 shrink-0">Reputation</span>
            <span
              className={`font-mono font-bold text-[11px] ${
                reputation < 0 ? 'text-danger' : 'text-accent-green'
              }`}
            >
              {reputation}
            </span>
          </div>
        )}
        {pulseCount !== undefined && pulseCount !== null && (
          <div className="flex items-start gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-20 shrink-0">Pulses</span>
            <span className="font-mono text-[11px] text-warning">{pulseCount}</span>
          </div>
        )}
        {notEmpty(data.whois) && (
          <div className="flex items-start gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-20 shrink-0">WHOIS</span>
            <a
              href={data.whois}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-accent-blue hover:text-accent-blue/80 font-mono transition-colors break-all"
            >
              View WHOIS <ExternalLink className="w-3 h-3 shrink-0" />
            </a>
          </div>
        )}
      </div>
    </CardShell>
  )
}

// ---- URLhaus card ----

function URLhausCard({ data }: { data: any }) {
  if (!data || data.error) {
    return (
      <CardShell title="URLHAUS" data={data ?? null} error>
        {null}
      </CardShell>
    )
  }

  if (data.query_status === 'no_results') {
    return (
      <CardShell title="URLHAUS" data={data}>
        <Badge label="Clean — no results" variant="green" />
      </CardShell>
    )
  }

  const urls: any[] = data.urls ?? []
  const isSingleUrl = notEmpty(data.url)

  return (
    <CardShell title="URLHAUS" data={data}>
      {isSingleUrl ? (
        <div className="space-y-0.5">
          <Row label="URL">{data.url}</Row>
          {notEmpty(data.threat) && <Row label="Threat">{data.threat}</Row>}
          {notEmpty(data.date_added) && <Row label="Added">{data.date_added}</Row>}
          {notEmpty(data.url_status) && (
            <div className="flex items-center gap-2 py-0.5">
              <span className="text-text-muted font-mono text-[11px] w-20 shrink-0">Status</span>
              <Badge
                label={data.url_status.toUpperCase()}
                variant={data.url_status === 'online' ? 'red' : 'muted'}
              />
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {notEmpty(data.host) && <Row label="Host">{data.host}</Row>}
          {urls.length > 0 ? (
            <div>
              <span className="text-[10px] font-mono text-text-muted block mb-1">
                {urls.length} URL{urls.length !== 1 ? 's' : ''} associated
              </span>
              <div className="space-y-2 max-h-36 overflow-y-auto pr-1">
                {urls.slice(0, 5).map((u: any, i: number) => (
                  <div key={i} className="bg-background/60 rounded p-2 space-y-0.5">
                    {notEmpty(u.url) && <Row label="URL">{u.url}</Row>}
                    {notEmpty(u.threat) && <Row label="Threat">{u.threat}</Row>}
                    {notEmpty(u.date_added) && <Row label="Added">{u.date_added}</Row>}
                  </div>
                ))}
                {urls.length > 5 && (
                  <p className="text-[10px] text-text-muted font-mono pl-1">
                    +{urls.length - 5} more in raw JSON
                  </p>
                )}
              </div>
            </div>
          ) : (
            <Badge label="Clean — no results" variant="green" />
          )}
        </div>
      )}
    </CardShell>
  )
}

// ---- Shodan InternetDB card ----

function ShodanCard({ data }: { data: any }) {
  if (!data || data.error) {
    return (
      <CardShell title="SHODAN" data={data ?? null} error>
        {null}
      </CardShell>
    )
  }

  const ports: number[] = data.ports ?? []
  const hostnames: string[] = data.hostnames ?? []
  const tags: string[] = data.tags ?? []
  const vulns: string[] = data.vulns ?? []
  const isEmpty =
    ports.length === 0 && hostnames.length === 0 && tags.length === 0 && vulns.length === 0

  return (
    <CardShell title="SHODAN" data={data}>
      {isEmpty ? (
        <span className="text-xs text-text-muted font-mono">Not indexed</span>
      ) : (
        <div className="space-y-2.5">
          {notEmpty(data.ip) && <Row label="IP">{data.ip}</Row>}
          {ports.length > 0 && (
            <div>
              <span className="text-[10px] font-mono text-text-muted block mb-1">Open Ports</span>
              <div className="flex flex-wrap gap-1">
                {ports.map((p) => (
                  <Badge key={p} label={String(p)} variant="blue" />
                ))}
              </div>
            </div>
          )}
          {hostnames.length > 0 && (
            <div>
              <span className="text-[10px] font-mono text-text-muted block mb-1">Hostnames</span>
              <ul className="space-y-0.5">
                {hostnames.map((h) => (
                  <li key={h} className="text-[11px] font-mono text-text-primary">
                    {h}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {tags.length > 0 && (
            <div>
              <span className="text-[10px] font-mono text-text-muted block mb-1">Tags</span>
              <div className="flex flex-wrap gap-1">
                {tags.map((t) => (
                  <Badge key={t} label={t} variant="muted" />
                ))}
              </div>
            </div>
          )}
          {vulns.length > 0 && (
            <div>
              <span className="text-[10px] font-mono text-text-muted block mb-1">
                Vulnerabilities
              </span>
              <div className="flex flex-wrap gap-1">
                {vulns.map((v) => (
                  <Badge key={v} label={v} variant="red" />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </CardShell>
  )
}

// ---- Generic flat card for unknown sources (e.g. malwarebazaar, dns, hunter, nvd, ripe) ----

function GenericCard({ title, data }: { title: string; data: any }) {
  if (!data || data.error) {
    return (
      <CardShell title={title} data={data ?? null} error>
        {null}
      </CardShell>
    )
  }

  const entries = Object.entries(data).filter(([, v]) => {
    if (v === null || v === undefined || v === '') return false
    if (typeof v === 'object') return false // skip nested objects/arrays in generic view
    return true
  })

  return (
    <CardShell title={title} data={data}>
      {entries.length === 0 ? (
        <span className="text-xs text-text-muted font-mono">No data available</span>
      ) : (
        <div className="space-y-0.5">
          {entries.map(([k, v]) => (
            <Row key={k} label={k}>
              {String(v)}
            </Row>
          ))}
        </div>
      )}
    </CardShell>
  )
}

// ---- Skeleton ----

function SkeletonCard() {
  return (
    <div className="bg-surface rounded-lg p-3 border border-border/60 animate-pulse">
      <div className="h-2 w-16 bg-border/60 rounded mb-3" />
      <div className="space-y-2">
        <div className="h-2 w-full bg-border/40 rounded" />
        <div className="h-2 w-3/4 bg-border/40 rounded" />
        <div className="h-2 w-1/2 bg-border/40 rounded" />
      </div>
    </div>
  )
}

// ---- Main export ----

const KNOWN_SOURCES = ['greynoise', 'ipinfo', 'alienvault', 'urlhaus', 'shodan']

export default function EnrichmentCards({
  enrichments,
  loading,
}: {
  enrichments: Record<string, any>
  loading?: boolean
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 mt-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    )
  }

  const otherSources = Object.keys(enrichments).filter((k) => !KNOWN_SOURCES.includes(k))

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 mt-3">
      {enrichments.greynoise !== undefined && (
        <GreyNoiseCard data={enrichments.greynoise} />
      )}
      {enrichments.ipinfo !== undefined && <IPInfoCard data={enrichments.ipinfo} />}
      {enrichments.alienvault !== undefined && (
        <AlienVaultCard data={enrichments.alienvault} />
      )}
      {enrichments.urlhaus !== undefined && <URLhausCard data={enrichments.urlhaus} />}
      {enrichments.shodan !== undefined && <ShodanCard data={enrichments.shodan} />}
      {otherSources.map((source) => (
        <GenericCard
          key={source}
          title={source.toUpperCase()}
          data={enrichments[source]}
        />
      ))}
    </div>
  )
}
