import { cn, severityBorderColors, formatRelativeTime } from '@/lib/utils'
import SeverityBadge from './SeverityBadge'
import { AlertCircle, Shield, Globe, Newspaper, MapPin, User, MessageSquare, Monitor } from 'lucide-react'

const MODULE_ICONS: Record<string, React.ElementType> = {
  'threat-intel': Shield,
  'dark-web': Globe,
  'news': Newspaper,
  'geoint': MapPin,
  'profiles': User,
  'socmint': MessageSquare,
  'cyber-surface': Monitor,
}

interface AlertCardProps {
  alert: {
    id: number
    title: string
    description?: string
    severity: string
    module: string
    status: string
    triggered_at: string
  }
  compact?: boolean
  onAcknowledge?: (id: number) => void
}

export default function AlertCard({ alert, compact, onAcknowledge }: AlertCardProps) {
  const ModuleIcon = MODULE_ICONS[alert.module] || AlertCircle

  return (
    <div
      className={cn(
        'bg-surface border rounded-lg p-3 transition-all hover:bg-background/40',
        severityBorderColors[alert.severity] || 'border-border',
        alert.severity === 'CRITICAL' && 'glow-red'
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn('w-8 h-8 rounded flex items-center justify-center flex-shrink-0 mt-0.5',
          alert.severity === 'CRITICAL' ? 'bg-red-900/40' :
          alert.severity === 'HIGH' ? 'bg-orange-900/40' :
          'bg-surface'
        )}>
          <ModuleIcon className="w-4 h-4 text-text-muted" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <SeverityBadge severity={alert.severity} pulse={alert.severity === 'CRITICAL'} />
            <span className="text-[10px] font-mono text-text-muted uppercase">{alert.module}</span>
            <span className="text-[10px] text-text-muted ml-auto">{formatRelativeTime(alert.triggered_at)}</span>
          </div>
          <p className="text-sm text-text-primary mt-1 line-clamp-2 font-medium">{alert.title}</p>
          {!compact && alert.description && (
            <p className="text-xs text-text-muted mt-1 line-clamp-2">{alert.description}</p>
          )}
        </div>
      </div>

      {!compact && onAcknowledge && alert.status === 'open' && (
        <div className="mt-2 flex justify-end">
          <button
            onClick={() => onAcknowledge(alert.id)}
            className="text-xs text-text-muted hover:text-accent-blue transition-colors font-mono"
          >
            ACK →
          </button>
        </div>
      )}
    </div>
  )
}
