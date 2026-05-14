'use client'

import { useState } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import { useAuthStore } from '@/lib/store'
import { KeyRound, Eye, EyeOff, CheckCircle, AlertCircle } from 'lucide-react'

export default function PasswordPage() {
  const { user, setUser } = useAuthStore()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNext, setShowNext] = useState(false)
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    if (next.length < 8) {
      setError('New password must be at least 8 characters')
      return
    }
    if (next !== confirm) {
      setError('New passwords do not match')
      return
    }
    setSaving(true)
    try {
      await api.put('/users/me/password', { current_password: current, new_password: next })
      // Clear force_password_change flag in local store
      if (user) setUser({ ...user, force_password_change: false })
      setSuccess('Password changed successfully')
      setCurrent('')
      setNext('')
      setConfirm('')
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Failed to change password')
    } finally {
      setSaving(false)
    }
  }

  const strength = next.length === 0 ? 0 : next.length < 8 ? 1 : next.length < 12 ? 2 : 3
  const strengthLabel = ['', 'Weak', 'Fair', 'Strong']
  const strengthColor = ['', 'bg-danger', 'bg-warning', 'bg-accent-green']

  return (
    <AppLayout title="SENTINEL / Change Password">
      <div className="max-w-lg mx-auto space-y-6">
        <div>
          <h1 className="text-lg font-bold flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-accent-green" />
            Change Password
          </h1>
          <p className="text-xs text-text-muted mt-0.5">Update your account password</p>
          {user?.force_password_change && (
            <div className="mt-2 text-xs bg-warning/10 border border-warning/30 text-warning rounded px-3 py-2 font-mono">
              ⚠ You are required to change your password before continuing
            </div>
          )}
        </div>

        <form onSubmit={handleSave} className="sentinel-card space-y-4">
          {/* Current password */}
          <div>
            <label className="block text-xs font-mono text-text-muted uppercase tracking-wider mb-1">
              Current Password
            </label>
            <div className="relative">
              <input
                type={showCurrent ? 'text' : 'password'}
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                className="sentinel-input pr-10"
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowCurrent(!showCurrent)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
              >
                {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* New password */}
          <div>
            <label className="block text-xs font-mono text-text-muted uppercase tracking-wider mb-1">
              New Password
            </label>
            <div className="relative">
              <input
                type={showNext ? 'text' : 'password'}
                value={next}
                onChange={(e) => setNext(e.target.value)}
                className="sentinel-input pr-10"
                required
                autoComplete="new-password"
                minLength={8}
              />
              <button
                type="button"
                onClick={() => setShowNext(!showNext)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
              >
                {showNext ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {/* Strength bar */}
            {next.length > 0 && (
              <div className="mt-1.5 flex items-center gap-2">
                <div className="flex gap-1 flex-1">
                  {[1, 2, 3].map((s) => (
                    <div
                      key={s}
                      className={`h-1 flex-1 rounded-full transition-colors ${strength >= s ? strengthColor[strength] : 'bg-border'}`}
                    />
                  ))}
                </div>
                <span className="text-[10px] font-mono text-text-muted">{strengthLabel[strength]}</span>
              </div>
            )}
            <p className="text-[10px] text-text-muted mt-1 font-mono">Minimum 8 characters</p>
          </div>

          {/* Confirm */}
          <div>
            <label className="block text-xs font-mono text-text-muted uppercase tracking-wider mb-1">
              Confirm New Password
            </label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className={`sentinel-input ${confirm && confirm !== next ? 'border-danger focus:border-danger' : ''}`}
              required
              autoComplete="new-password"
            />
            {confirm && confirm !== next && (
              <p className="text-[10px] text-danger font-mono mt-1">Passwords do not match</p>
            )}
          </div>

          {error && (
            <div className="flex items-center gap-2 text-danger text-xs bg-danger/10 border border-danger/20 rounded px-3 py-2">
              <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="font-mono">{error}</span>
            </div>
          )}
          {success && (
            <div className="flex items-center gap-2 text-accent-green text-xs bg-accent-green/10 border border-accent-green/20 rounded px-3 py-2">
              <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="font-mono">{success}</span>
            </div>
          )}

          <div className="flex justify-end pt-1">
            <button
              type="submit"
              disabled={saving || (!!confirm && confirm !== next)}
              className="flex items-center gap-2 bg-accent-green text-background font-bold text-sm px-4 py-2 rounded hover:bg-accent-green/90 disabled:opacity-50 transition-colors"
            >
              <KeyRound className="w-4 h-4" />
              {saving ? 'Updating...' : 'Update Password'}
            </button>
          </div>
        </form>
      </div>
    </AppLayout>
  )
}
