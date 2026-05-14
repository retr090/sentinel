import { cn, severityColors } from '@/lib/utils'

interface SeverityBadgeProps {
  severity: string
  className?: string
  pulse?: boolean
}

export default function SeverityBadge({ severity, className, pulse }: SeverityBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase tracking-wider',
        severityColors[severity] || 'bg-slate-700 text-slate-100',
        pulse && severity === 'CRITICAL' && 'badge-pulse',
        className
      )}
    >
      {severity === 'CRITICAL' && <span className="mr-1">⚠</span>}
      {severity}
    </span>
  )
}
