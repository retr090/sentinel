import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const severityColors: Record<string, string> = {
  CRITICAL: 'bg-red-600 text-white',
  HIGH: 'bg-orange-500 text-white',
  MEDIUM: 'bg-blue-500 text-white',
  LOW: 'bg-green-600 text-white',
  INFO: 'bg-slate-600 text-white',
}

export const severityBorderColors: Record<string, string> = {
  CRITICAL: 'border-red-600',
  HIGH: 'border-orange-500',
  MEDIUM: 'border-blue-500',
  LOW: 'border-green-600',
  INFO: 'border-slate-500',
}

export const iocTypeColors: Record<string, string> = {
  ip: 'bg-purple-700 text-purple-100',
  domain: 'bg-blue-700 text-blue-100',
  hash: 'bg-slate-700 text-slate-100',
  url: 'bg-yellow-700 text-yellow-100',
  email: 'bg-pink-700 text-pink-100',
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return 'N/A'
  return new Date(date).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function formatRelativeTime(date: string | null | undefined): string {
  if (!date) return 'N/A'
  const diff = Date.now() - new Date(date).getTime()
  const mins = Math.floor(diff / 60000)
  const hours = Math.floor(mins / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days}d ago`
  if (hours > 0) return `${hours}h ago`
  if (mins > 0) return `${mins}m ago`
  return 'just now'
}

export function riskScoreToColor(score: number): string {
  if (score >= 75) return '#ef4444'
  if (score >= 50) return '#f59e0b'
  if (score >= 25) return '#3b82f6'
  return '#10b981'
}
