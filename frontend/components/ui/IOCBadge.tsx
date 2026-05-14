import { cn, iocTypeColors } from '@/lib/utils'

interface IOCBadgeProps {
  type: string
  value?: string
  className?: string
}

const TYPE_LABELS: Record<string, string> = {
  ip: 'IPv4',
  domain: 'DOMAIN',
  hash: 'HASH',
  hash_md5: 'MD5',
  hash_sha1: 'SHA1',
  hash_sha256: 'SHA256',
  url: 'URL',
  email: 'EMAIL',
  cve: 'CVE',
  asn: 'ASN',
}

export default function IOCBadge({ type, value, className }: IOCBadgeProps) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 max-w-full', className)}>
      <span
        className={cn(
          'flex-shrink-0 px-1.5 py-0.5 rounded text-[9px] font-bold font-mono uppercase tracking-widest',
          iocTypeColors[type] || 'bg-slate-700 text-slate-100'
        )}
      >
        {TYPE_LABELS[type] || type.toUpperCase()}
      </span>
      {value && (
        <code className="text-text-primary text-xs font-mono truncate max-w-[200px]" title={value}>
          {value}
        </code>
      )}
    </span>
  )
}
