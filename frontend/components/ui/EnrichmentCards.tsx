'use client'

import { useState, type ReactNode } from 'react'
import { ChevronDown, ChevronUp, Copy, Check, ExternalLink, MapPin } from 'lucide-react'

// ─── utilities ───────────────────────────────

function notEmpty(v: any): boolean {
  return v !== null && v !== undefined && v !== ''
}

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
            {copied ? <Check className="w-3 h-3 text-accent-green" /> : <Copy className="w-3 h-3" />}
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

function CardShell({
  title,
  children,
  data,
  error,
  headerColor = 'text-accent-green',
}: {
  title: string
  children?: ReactNode
  data: any
  error?: boolean
  headerColor?: string
}) {
  return (
    <div className="bg-surface rounded-lg p-3 border border-border/60">
      <div className={`text-[10px] font-mono uppercase mb-2 tracking-wider ${headerColor}`}>{title}</div>
      {error ? (
        <span className="text-xs text-text-muted font-mono">Source unavailable</span>
      ) : children}
      {data != null && <CopyRawJSON data={data} />}
    </div>
  )
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-2 text-xs py-0.5">
      <span className="text-text-muted font-mono w-22 shrink-0 text-[11px]">{label}</span>
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
  orange: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
}

function Badge({ label, variant = 'muted' }: { label: string; variant?: keyof typeof BADGE_VARIANTS }) {
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono rounded border ${BADGE_VARIANTS[variant] ?? BADGE_VARIANTS.muted}`}>
      {label}
    </span>
  )
}

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

// ─── source cards ──────────────────────────────

const CLASSIFICATION_COLORS: Record<string, string> = {
  malicious: 'bg-danger/20 text-danger border-danger/40',
  benign: 'bg-accent-green/10 text-accent-green border-accent-green/30',
  unknown: 'bg-border/50 text-text-muted border-border',
}

function GreyNoiseCard({ data }: { data: any }) {
  if (!data || data.error) return <CardShell title="GREYNOISE" data={data ?? null} error>{null}</CardShell>
  const cls = (data.classification ?? 'unknown').toLowerCase()
  return (
    <CardShell title="GREYNOISE" data={data}>
      <div className="space-y-2">
        {notEmpty(data.classification) && (
          <div className="flex items-center gap-2">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Classification</span>
            <span className={`px-2 py-0.5 text-[10px] font-mono rounded border ${CLASSIFICATION_COLORS[cls] ?? CLASSIFICATION_COLORS.unknown}`}>
              {data.classification.toUpperCase()}
            </span>
          </div>
        )}
        <div className="flex items-center gap-1.5 flex-wrap">
          {data.noise !== undefined && <Badge label={`NOISE: ${data.noise ? 'YES' : 'NO'}`} variant={data.noise ? 'red' : 'muted'} />}
          {data.riot !== undefined && <Badge label={`RIOT: ${data.riot ? 'YES' : 'NO'}`} variant={data.riot ? 'green' : 'muted'} />}
        </div>
        {notEmpty(data.name) && <Row label="Actor">{data.name}</Row>}
        {notEmpty(data.message) && <Row label="Message">{data.message}</Row>}
        {notEmpty(data.ip) && (
          <a href={`https://viz.greynoise.io/ip/${data.ip}`} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[10px] font-mono text-accent-blue hover:text-accent-blue/80 transition-colors mt-1">
            View on GreyNoise <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </CardShell>
  )
}

function IPInfoCard({ data }: { data: any }) {
  if (!data || data.error) return <CardShell title="IPINFO" data={data ?? null} error>{null}</CardShell>
  const [lat, lon] = (data.loc ?? '').split(',')
  const hasCoords = notEmpty(lat) && notEmpty(lon)
  return (
    <CardShell title="IPINFO" data={data}>
      <div className="space-y-0.5">
        {notEmpty(data.city) && <Row label="City">{data.city}</Row>}
        {notEmpty(data.region) && <Row label="Region">{data.region}</Row>}
        {notEmpty(data.country) && <Row label="Country">{data.country}</Row>}
        {notEmpty(data.org) && <Row label="ASN / Org">{data.org}</Row>}
        {notEmpty(data.timezone) && <Row label="Timezone">{data.timezone}</Row>}
        {hasCoords && (
          <div className="flex items-start gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Location</span>
            <a href={`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=10`} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-accent-blue hover:text-accent-blue/80 font-mono transition-colors">
              <MapPin className="w-3 h-3 shrink-0" />{lat}, {lon}
            </a>
          </div>
        )}
      </div>
    </CardShell>
  )
}

function AlienVaultCard({ data }: { data: any }) {
  if (!data || data.error) return <CardShell title="ALIENVAULT OTX" data={data ?? null} error>{null}</CardShell>
  const pulseCount: number | undefined = data.pulse_info?.count
  const reputation: number | undefined = data.reputation
  return (
    <CardShell title="ALIENVAULT OTX" data={data}>
      <div className="space-y-0.5">
        {notEmpty(data.indicator) && <Row label="Indicator">{data.indicator}</Row>}
        {notEmpty(data.type_title) && <Row label="Type">{data.type_title}</Row>}
        {reputation !== undefined && reputation !== null && (
          <div className="flex items-start gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Reputation</span>
            <span className={`font-mono font-bold text-[11px] ${reputation < 0 ? 'text-danger' : 'text-accent-green'}`}>{reputation}</span>
          </div>
        )}
        {pulseCount !== undefined && pulseCount !== null && (
          <div className="flex items-start gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Pulses</span>
            <span className="font-mono text-[11px] text-warning">{pulseCount}</span>
          </div>
        )}
        {notEmpty(data.whois) && (
          <div className="flex items-start gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">WHOIS</span>
            <a href={data.whois} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-accent-blue hover:text-accent-blue/80 font-mono transition-colors break-all">
              View WHOIS <ExternalLink className="w-3 h-3 shrink-0" />
            </a>
          </div>
        )}
      </div>
    </CardShell>
  )
}

function URLhausCard({ data }: { data: any }) {
  if (!data || data.error) return <CardShell title="URLHAUS" data={data ?? null} error>{null}</CardShell>
  if (data.query_status === 'no_results') {
    return (
      <CardShell title="URLHAUS" data={data}>
        <Badge label="✓ Clean — no results found" variant="green" />
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
          {notEmpty(data.url_status) && (
            <div className="flex items-center gap-2 py-0.5">
              <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Status</span>
              <Badge label={data.url_status.toUpperCase()} variant={data.url_status === 'online' ? 'red' : 'muted'} />
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {notEmpty(data.host) && <Row label="Host">{data.host}</Row>}
          {urls.length > 0 ? (
            <div>
              <span className="text-[10px] font-mono text-text-muted block mb-1">{urls.length} URL{urls.length !== 1 ? 's' : ''} associated</span>
              <div className="space-y-2 max-h-36 overflow-y-auto pr-1">
                {urls.slice(0, 5).map((u: any, i: number) => (
                  <div key={i} className="bg-background/60 rounded p-2 space-y-0.5">
                    {notEmpty(u.url) && <Row label="URL">{u.url}</Row>}
                    {notEmpty(u.threat) && <Row label="Threat">{u.threat}</Row>}
                    {notEmpty(u.url_status) && <Row label="Status">{u.url_status}</Row>}
                  </div>
                ))}
                {urls.length > 5 && <p className="text-[10px] text-text-muted font-mono pl-1">+{urls.length - 5} more in raw JSON</p>}
              </div>
            </div>
          ) : (
            <Badge label="✓ Clean — no results found" variant="green" />
          )}
        </div>
      )}
    </CardShell>
  )
}

function ShodanCard({ data }: { data: any }) {
  if (!data || data.error) return <CardShell title="SHODAN" data={data ?? null} error>{null}</CardShell>
  const ports: number[] = data.ports ?? []
  const hostnames: string[] = data.hostnames ?? []
  const tags: string[] = data.tags ?? []
  const vulns: string[] = data.vulns ?? []
  const cpes: string[] = data.cpes ?? []
  const isEmpty = ports.length === 0 && hostnames.length === 0 && tags.length === 0 && vulns.length === 0
  return (
    <CardShell title="SHODAN" data={data}>
      {isEmpty ? (
        <span className="text-xs text-text-muted font-mono">Not indexed</span>
      ) : (
        <div className="space-y-2.5">
          {ports.length > 0 && (
            <div>
              <span className="text-[10px] font-mono text-text-muted block mb-1">Open Ports</span>
              <div className="flex flex-wrap gap-1">{ports.map((p) => <Badge key={p} label={String(p)} variant="blue" />)}</div>
            </div>
          )}
          {hostnames.length > 0 && (
            <div>
              <span className="text-[10px] font-mono text-text-muted block mb-1">Hostnames</span>
              <ul className="space-y-0.5">{hostnames.map((h) => <li key={h} className="text-[11px] font-mono text-text-primary">{h}</li>)}</ul>
            </div>
          )}
          {tags.length > 0 && (
            <div>
              <span className="text-[10px] font-mono text-text-muted block mb-1">Tags</span>
              <div className="flex flex-wrap gap-1">{tags.map((t) => <Badge key={t} label={t} variant="muted" />)}</div>
            </div>
          )}
          {vulns.length > 0 && (
            <div>
              <span className="text-[10px] font-mono text-text-muted block mb-1">Vulnerabilities</span>
              <div className="flex flex-wrap gap-1">{vulns.map((v) => <Badge key={v} label={v} variant="red" />)}</div>
            </div>
          )}
          {cpes.length > 0 && (
            <div>
              <span className="text-[10px] font-mono text-text-muted block mb-1">CPEs</span>
              <ul className="space-y-0.5">{cpes.slice(0, 3).map((c) => <li key={c} className="text-[10px] font-mono text-text-muted">{c}</li>)}</ul>
            </div>
          )}
        </div>
      )}
    </CardShell>
  )
}

function MalwareBazaarCard({ data }: { data: any }) {
  if (!data || data.error) return <CardShell title="MALWAREBAZAAR" data={data ?? null} error>{null}</CardShell>
  if (data.query_status === 'no_results') {
    return (
      <CardShell title="MALWAREBAZAAR" data={data}>
        <Badge label="✓ Not in MalwareBazaar" variant="green" />
      </CardShell>
    )
  }
  const sample = (Array.isArray(data.data) ? data.data[0] : null) ?? {}
  const tags: string[] = sample.tags ?? []
  return (
    <CardShell title="MALWAREBAZAAR" data={data} headerColor="text-danger">
      <div className="space-y-0.5">
        {notEmpty(sample.file_type) && <Row label="File Type">{sample.file_type}</Row>}
        {notEmpty(sample.file_size) && <Row label="File Size">{Math.round(sample.file_size / 1024)} KB</Row>}
        {notEmpty(sample.signature) && (
          <div className="flex items-start gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Signature</span>
            <span className="font-mono font-bold text-[11px] text-danger">{sample.signature}</span>
          </div>
        )}
        {notEmpty(sample.first_seen) && <Row label="First Seen">{sample.first_seen?.split(' ')[0]}</Row>}
        {tags.length > 0 && (
          <div>
            <span className="text-[10px] font-mono text-text-muted block mb-1 mt-1">Tags</span>
            <div className="flex flex-wrap gap-1">{tags.map((t) => <Badge key={t} label={t} variant="orange" />)}</div>
          </div>
        )}
      </div>
    </CardShell>
  )
}

function ThreatFoxCard({ data }: { data: any }) {
  if (!data || data.error) return <CardShell title="THREATFOX" data={data ?? null} error>{null}</CardShell>
  if (data.query_status === 'no_results' || !data.data?.length) {
    return (
      <CardShell title="THREATFOX" data={data}>
        <Badge label="✓ Not found in ThreatFox" variant="green" />
      </CardShell>
    )
  }
  const entry = data.data[0] ?? {}
  const tags: string[] = entry.tags ?? []
  return (
    <CardShell title="THREATFOX" data={data} headerColor="text-warning">
      <div className="space-y-0.5">
        {notEmpty(entry.ioc_type) && <Row label="IOC Type">{entry.ioc_type}</Row>}
        {notEmpty(entry.threat_type) && <Row label="Threat">{entry.threat_type}</Row>}
        {notEmpty(entry.malware) && (
          <div className="flex items-start gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Malware</span>
            <span className="font-mono font-bold text-[11px] text-danger">{entry.malware}</span>
          </div>
        )}
        {entry.confidence_level !== undefined && (
          <div className="flex items-center gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Confidence</span>
            <div className="flex items-center gap-1.5">
              <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden">
                <div className="h-full bg-warning rounded-full" style={{ width: `${entry.confidence_level}%` }} />
              </div>
              <span className="text-[11px] font-mono text-warning">{entry.confidence_level}%</span>
            </div>
          </div>
        )}
        {notEmpty(entry.first_seen) && <Row label="First Seen">{entry.first_seen?.split(' ')[0]}</Row>}
        {tags.length > 0 && (
          <div>
            <span className="text-[10px] font-mono text-text-muted block mb-1 mt-1">Tags</span>
            <div className="flex flex-wrap gap-1">{tags.map((t) => <Badge key={t} label={t} variant="yellow" />)}</div>
          </div>
        )}
      </div>
    </CardShell>
  )
}

function VirusTotalCard({ data }: { data: any }) {
  if (!data || data.error) return <CardShell title="VIRUSTOTAL" data={data ?? null} error>{null}</CardShell>
  if (!data.last_analysis_stats && Object.keys(data).length === 0) {
    return <CardShell title="VIRUSTOTAL" data={data}><span className="text-xs text-text-muted font-mono">No key configured</span></CardShell>
  }
  const stats = data.last_analysis_stats ?? {}
  const malicious = stats.malicious ?? 0
  const suspicious = stats.suspicious ?? 0
  const harmless = (stats.harmless ?? 0) + (stats.undetected ?? 0)
  const total = malicious + suspicious + harmless + (stats.timeout ?? 0)
  const vtUrl = data.url ? `https://www.virustotal.com/gui/url/${encodeURIComponent(data.url)}` : undefined

  return (
    <CardShell title="VIRUSTOTAL" data={data} headerColor={malicious > 0 ? 'text-danger' : 'text-accent-green'}>
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Malicious</span>
          <span className={`font-mono font-bold text-[11px] ${malicious > 0 ? 'text-danger' : 'text-text-muted'}`}>
            {malicious} / {total} engines
          </span>
        </div>
        {suspicious > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Suspicious</span>
            <span className="font-mono text-[11px] text-warning">{suspicious} engines</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Clean</span>
          <span className="font-mono text-[11px] text-accent-green">{harmless} engines</span>
        </div>
        {data.reputation !== undefined && data.reputation !== null && (
          <div className="flex items-center gap-2">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Reputation</span>
            <span className={`font-mono font-bold text-[11px] ${data.reputation < 0 ? 'text-danger' : data.reputation > 0 ? 'text-accent-green' : 'text-text-muted'}`}>{data.reputation}</span>
          </div>
        )}
        {notEmpty(data.meaningful_name) && <Row label="Name">{data.meaningful_name}</Row>}
        {notEmpty(data.type_description) && <Row label="File Type">{data.type_description}</Row>}
        {notEmpty(data.country) && <Row label="Country">{data.country}</Row>}
        {vtUrl && (
          <a href={vtUrl} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[10px] font-mono text-accent-blue hover:text-accent-blue/80 transition-colors mt-1">
            View on VirusTotal <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </CardShell>
  )
}

const ABUSEIPDB_CATEGORIES: Record<number, string> = {
  3: 'Fraud', 4: 'DDoS', 5: 'FTP Brute-Force', 6: 'Ping of Death',
  7: 'Phishing', 8: 'Fraud VoIP', 9: 'Open Proxy', 10: 'Web Spam',
  11: 'Email Spam', 12: 'Blog Spam', 13: 'VPN IP', 14: 'Port Scan',
  15: 'Hacking', 16: 'SQL Injection', 17: 'Spoofing', 18: 'Brute-Force',
  19: 'Bad Web Bot', 20: 'Exploited Host', 21: 'Web App Attack',
  22: 'SSH Attack', 23: 'IoT Targeted',
}

function abuseConfidenceBadge(score: number): { label: string; variant: keyof typeof BADGE_VARIANTS } {
  if (score >= 80) return { label: 'HIGH RISK',   variant: 'red' }
  if (score >= 50) return { label: 'SUSPICIOUS',  variant: 'orange' }
  if (score >= 25) return { label: 'LOW RISK',    variant: 'yellow' }
  if (score > 0)   return { label: 'MINIMAL',     variant: 'blue' }
  return               { label: 'CLEAN',       variant: 'green' }
}

function AbuseIPDBCard({ data, ip }: { data: any; ip?: string }) {
  if (!data) return <CardShell title="ABUSEIPDB" data={null} error>{null}</CardShell>
  if (data.error === 'no_api_key') {
    return (
      <CardShell title="ABUSEIPDB" data={null} headerColor="text-text-muted">
        <span className="text-xs text-text-muted font-mono">
          API key not configured — add ABUSEIPDB_API_KEY to .env
        </span>
      </CardShell>
    )
  }
  if (data.error) return <CardShell title="ABUSEIPDB" data={data} error>{null}</CardShell>

  const confidence: number = data.abuse_confidence_score ?? 0
  const totalReports: number = data.total_reports ?? 0
  const { label: badgeLabel, variant: badgeVariant } = abuseConfidenceBadge(confidence)
  const reports: any[] = data.reports ?? []
  const lookupIp = data.ip_address ?? ip

  return (
    <CardShell title="ABUSEIPDB" data={data} headerColor={confidence >= 50 ? 'text-danger' : confidence >= 25 ? 'text-warning' : 'text-accent-green'}>
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Confidence</span>
          <div className="flex items-center gap-1.5">
            <span className="font-mono font-bold text-[11px]">{confidence}%</span>
            <Badge label={badgeLabel} variant={badgeVariant} />
          </div>
        </div>
        {totalReports === 0 ? (
          <Badge label="✓ No reports found" variant="green" />
        ) : (
          <>
            <Row label="Total Reports">{totalReports}</Row>
            {notEmpty(data.num_distinct_users) && <Row label="Distinct Users">{data.num_distinct_users}</Row>}
          </>
        )}
        {notEmpty(data.isp) && <Row label="ISP">{data.isp}</Row>}
        {notEmpty(data.usage_type) && <Row label="Usage Type">{data.usage_type}</Row>}
        {notEmpty(data.country_code) && <Row label="Country">{data.country_code}</Row>}
        {notEmpty(data.domain) && <Row label="Domain">{data.domain}</Row>}
        {data.is_whitelisted !== undefined && data.is_whitelisted !== null && (
          <div className="flex items-center gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Whitelisted</span>
            <Badge label={data.is_whitelisted ? 'YES' : 'NO'} variant={data.is_whitelisted ? 'green' : 'muted'} />
          </div>
        )}
        {notEmpty(data.last_reported_at) && <Row label="Last Reported">{new Date(data.last_reported_at).toLocaleString()}</Row>}

        {reports.length > 0 && (
          <div className="mt-1">
            <span className="text-[10px] font-mono text-text-muted block mb-1">Recent Reports</span>
            <ul className="space-y-1">
              {reports.map((r: any, i: number) => {
                const cats: number[] = r.categories ?? []
                const catLabels = cats.map((c) => ABUSEIPDB_CATEGORIES[c] ?? `Cat.${c}`).join(', ')
                const date = r.reportedAt ? new Date(r.reportedAt).toLocaleDateString() : ''
                return (
                  <li key={i} className="text-[10px] font-mono text-text-muted">
                    {date && <span className="text-text-primary">{date}</span>}
                    {date && catLabels && ' — '}
                    {catLabels}
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {lookupIp && (
          <a
            href={`https://www.abuseipdb.com/check/${lookupIp}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[10px] font-mono text-accent-blue hover:text-accent-blue/80 transition-colors mt-1"
          >
            View on AbuseIPDB <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </CardShell>
  )
}

function CVECard({ source, data }: { source: 'circl_cve' | 'nvd'; data: any }) {
  const title = source === 'circl_cve' ? 'CIRCL CVE' : 'NVD'
  if (!data || data.error) return <CardShell title={title} data={data ?? null} error>{null}</CardShell>
  if (Object.keys(data).length === 0) return null

  // CIRCL format: { summary, cvss, references, id }
  // NVD format: { descriptions, metrics, ... }
  const summary = data.summary || (data.descriptions?.find((d: any) => d.lang === 'en')?.value)
  const cvss = data.cvss || (
    data.metrics?.cvssMetricV31?.[0]?.cvssData?.baseScore
    ?? data.metrics?.cvssMetricV30?.[0]?.cvssData?.baseScore
    ?? data.metrics?.cvssMetricV2?.[0]?.cvssData?.baseScore
  )
  const refs: string[] = data.references ?? []

  let cvssColor = 'text-text-muted'
  if (cvss) {
    const n = parseFloat(String(cvss))
    if (n >= 9) cvssColor = 'text-danger'
    else if (n >= 7) cvssColor = 'text-warning'
    else if (n >= 4) cvssColor = 'text-yellow-400'
  }

  return (
    <CardShell title={title} data={data} headerColor="text-accent-blue">
      <div className="space-y-1.5">
        {cvss !== undefined && cvss !== null && (
          <div className="flex items-center gap-2">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">CVSS Score</span>
            <span className={`font-mono font-bold text-sm ${cvssColor}`}>{cvss}</span>
          </div>
        )}
        {summary && (
          <div className="mt-1">
            <span className="text-[10px] font-mono text-text-muted block mb-1">Summary</span>
            <p className="text-[11px] text-text-primary font-mono leading-relaxed line-clamp-4">{summary}</p>
          </div>
        )}
        {refs.length > 0 && (
          <div className="mt-1">
            <span className="text-[10px] font-mono text-text-muted block mb-1">References</span>
            <ul className="space-y-0.5">
              {refs.slice(0, 3).map((r: any, i) => {
                const url = typeof r === 'string' ? r : r.url
                return url ? (
                  <li key={i}>
                    <a href={url} target="_blank" rel="noopener noreferrer"
                      className="text-[10px] font-mono text-accent-blue hover:text-accent-blue/80 truncate block">
                      {url}
                    </a>
                  </li>
                ) : null
              })}
            </ul>
          </div>
        )}
      </div>
    </CardShell>
  )
}

function EmailDNSCard({ data }: { data: any }) {
  if (!data || data.error) return <CardShell title="EMAIL DNS" data={data ?? null} error>{null}</CardShell>
  return (
    <CardShell title="EMAIL / DNS" data={data}>
      <div className="space-y-0.5">
        {notEmpty(data.domain) && <Row label="Domain">{data.domain}</Row>}
        <div className="flex items-center gap-2 py-0.5">
          <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Has MX</span>
          <Badge label={data.has_mx ? 'YES' : 'NO'} variant={data.has_mx ? 'green' : 'red'} />
        </div>
        <div className="flex items-center gap-2 py-0.5">
          <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Disposable</span>
          <Badge label={data.disposable ? 'YES' : 'NO'} variant={data.disposable ? 'red' : 'green'} />
        </div>
        {(data.mx_records ?? []).length > 0 && (
          <div className="mt-1">
            <span className="text-[10px] font-mono text-text-muted block mb-1">MX Records</span>
            <ul className="space-y-0.5">{data.mx_records.map((r: string) => <li key={r} className="text-[10px] font-mono text-text-muted">{r}</li>)}</ul>
          </div>
        )}
      </div>
    </CardShell>
  )
}

function XposedOrNotCard({ data, email }: { data: any; email?: string }) {
  if (!data || data.error) return <CardShell title="XPOSEDORNOT" data={data ?? null} error headerColor="text-orange-400">{null}</CardShell>

  // Domain variant
  if (data.exposed_emails !== undefined) {
    return (
      <CardShell title="XPOSEDORNOT" data={data} headerColor={data.exposed ? 'text-danger' : 'text-accent-green'}>
        <div className="space-y-1.5">
          {data.exposed ? (
            <>
              <div className="flex flex-wrap gap-1.5 mb-2">
                <Badge label={`${data.breach_count} BREACHES`} variant="red" />
                <Badge label={`${data.exposed_emails.toLocaleString()} EXPOSED EMAILS`} variant="orange" />
              </div>
              {notEmpty(data.first_breach) && <Row label="First Breach">{data.first_breach}</Row>}
              {notEmpty(data.latest_breach) && <Row label="Latest Breach">{data.latest_breach}</Row>}
            </>
          ) : (
            <Badge label="✓ No domain breach exposure found" variant="green" />
          )}
        </div>
      </CardShell>
    )
  }

  // Email variant
  return (
    <CardShell title="XPOSEDORNOT" data={data} headerColor={data.exposed ? 'text-danger' : 'text-accent-green'}>
      <div className="space-y-1.5">
        {data.exposed ? (
          <>
            <div className="flex flex-wrap gap-1.5 mb-2">
              <Badge label={`${data.breach_count} BREACHES`} variant="red" />
              {data.paste_count > 0 && <Badge label={`${data.paste_count} PASTES`} variant="orange" />}
            </div>
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              {(data.breaches ?? []).map((b: any, i: number) => (
                <div key={i} className="bg-background/60 rounded p-2 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono font-bold text-text-primary">{b.name}</span>
                    {notEmpty(b.date) && <span className="text-[10px] text-text-muted font-mono">{b.date}</span>}
                  </div>
                  {b.records > 0 && (
                    <div className="text-[10px] text-text-muted font-mono">{b.records.toLocaleString()} records</div>
                  )}
                  {b.data_classes?.filter(Boolean).length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {b.data_classes.filter(Boolean).slice(0, 4).map((dc: string, j: number) => (
                        <span key={j} className="text-[9px] px-1.5 py-0.5 rounded bg-background border border-border text-text-muted font-mono">
                          {dc.trim()}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
            {email && (
              <a
                href={`https://xposedornot.com/xposed/#${encodeURIComponent(email)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[10px] font-mono text-accent-blue hover:text-accent-blue/80 transition-colors mt-1"
              >
                View on XposedOrNot <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </>
        ) : (
          <Badge label="✓ No breach exposure found" variant="green" />
        )}
      </div>
    </CardShell>
  )
}

function LeakCheckCard({ data }: { data: any }) {
  if (!data || data.error) return <CardShell title="LEAKCHECK" data={data ?? null} error headerColor="text-purple-400">{null}</CardShell>
  return (
    <CardShell title="LEAKCHECK" data={data} headerColor={data.found ? 'text-danger' : 'text-accent-green'}>
      <div className="space-y-1.5">
        {data.found ? (
          <>
            <Badge label={`${data.leak_count} LEAK SOURCES`} variant="red" />
            {(data.fields ?? []).length > 0 && (
              <div className="mt-1.5">
                <span className="text-[10px] font-mono text-text-muted block mb-1">Leaked Fields</span>
                <div className="flex flex-wrap gap-1">
                  {data.fields.map((field: string, i: number) => (
                    <span
                      key={i}
                      className={`text-[10px] px-1.5 py-0.5 rounded border font-mono ${
                        field.toLowerCase().includes('password')
                          ? 'bg-danger/20 text-danger border-danger/40'
                          : field.toLowerCase().includes('phone')
                          ? 'bg-orange-500/10 text-orange-400 border-orange-500/30'
                          : 'bg-border/50 text-text-muted border-border'
                      }`}
                    >
                      {field}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {(data.sources ?? []).length > 0 && (
              <div className="mt-1">
                <span className="text-[10px] font-mono text-text-muted block mb-1">Found In</span>
                <ul className="space-y-0.5 max-h-32 overflow-y-auto">
                  {data.sources.map((src: string, i: number) => (
                    <li key={i} className="flex items-center gap-1.5 text-[11px] font-mono text-text-primary">
                      <span className="text-danger text-[9px]">▸</span>{src}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : (
          <Badge label="✓ No credential leaks found" variant="green" />
        )}
      </div>
    </CardShell>
  )
}

function HunterCard({ data }: { data: any }) {
  if (!data || data.error || Object.keys(data).length === 0) return null
  return (
    <CardShell title="HUNTER.IO" data={data}>
      <div className="space-y-0.5">
        {notEmpty(data.status) && (
          <div className="flex items-center gap-2 py-0.5">
            <span className="text-text-muted font-mono text-[11px] w-22 shrink-0">Status</span>
            <Badge label={data.status.toUpperCase()} variant={data.status === 'valid' ? 'green' : data.status === 'invalid' ? 'red' : 'yellow'} />
          </div>
        )}
        {notEmpty(data.score) && <Row label="Score">{data.score}</Row>}
        {notEmpty(data.email) && <Row label="Email">{data.email}</Row>}
      </div>
    </CardShell>
  )
}

// ─── source → card mapping and ordering ──────

const SOURCES_BY_TYPE: Record<string, string[]> = {
  ip: ['shodan', 'greynoise', 'ipinfo', 'alienvault', 'urlhaus', 'threatfox', 'virustotal', 'abuseipdb'],
  domain: ['alienvault', 'urlhaus', 'threatfox', 'virustotal', 'xposedornot'],
  hash_md5: ['malwarebazaar', 'threatfox', 'alienvault', 'virustotal'],
  hash_sha1: ['malwarebazaar', 'threatfox', 'alienvault', 'virustotal'],
  hash_sha256: ['malwarebazaar', 'threatfox', 'alienvault', 'virustotal'],
  url: ['urlhaus', 'threatfox', 'virustotal'],
  email: ['dns', 'hunter', 'xposedornot', 'leakcheck'],
  cve: ['circl_cve', 'nvd'],
}

// ─── main export ──────────────────────────────

export default function EnrichmentCards({
  enrichments,
  loading,
  iocType,
}: {
  enrichments: Record<string, any>
  loading?: boolean
  iocType?: string
}) {
  const skeletonCount = iocType ? (SOURCES_BY_TYPE[iocType]?.length ?? 4) : 5

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 mt-3">
        {Array.from({ length: skeletonCount }).map((_, i) => <SkeletonCard key={i} />)}
      </div>
    )
  }

  // Order cards: use type-specific order when known, then append any extra sources
  const orderedSources = iocType
    ? [
        ...(SOURCES_BY_TYPE[iocType] ?? []).filter((s) => s in enrichments),
        ...Object.keys(enrichments).filter((s) => !(SOURCES_BY_TYPE[iocType] ?? []).includes(s)),
      ]
    : Object.keys(enrichments)

  const renderCard = (source: string) => {
    const data = enrichments[source]
    switch (source) {
      case 'greynoise':    return <GreyNoiseCard key={source} data={data} />
      case 'ipinfo':       return <IPInfoCard key={source} data={data} />
      case 'alienvault':   return <AlienVaultCard key={source} data={data} />
      case 'urlhaus':      return <URLhausCard key={source} data={data} />
      case 'shodan':       return <ShodanCard key={source} data={data} />
      case 'malwarebazaar':return <MalwareBazaarCard key={source} data={data} />
      case 'threatfox':    return <ThreatFoxCard key={source} data={data} />
      case 'virustotal':   return <VirusTotalCard key={source} data={data} />
      case 'abuseipdb':    return <AbuseIPDBCard key={source} data={data} ip={enrichments.abuseipdb?.ip_address} />
      case 'circl_cve':    return <CVECard key={source} source="circl_cve" data={data} />
      case 'nvd':          return <CVECard key={source} source="nvd" data={data} />
      case 'dns':          return <EmailDNSCard key={source} data={data} />
      case 'hunter':       return <HunterCard key={source} data={data} />
      case 'xposedornot':  return <XposedOrNotCard key={source} data={data} email={enrichments.dns?.domain ? undefined : undefined} />
      case 'leakcheck':    return <LeakCheckCard key={source} data={data} />
      default:
        if (!data || (data.error && Object.keys(data).length === 1)) return null
        return (
          <CardShell key={source} title={source.toUpperCase()} data={data}>
            <div className="space-y-0.5">
              {Object.entries(data)
                .filter(([, v]) => v !== null && v !== undefined && v !== '' && typeof v !== 'object')
                .map(([k, v]) => <Row key={k} label={k}>{String(v)}</Row>)}
            </div>
          </CardShell>
        )
    }
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 mt-3">
      {orderedSources.map(renderCard)}
    </div>
  )
}
