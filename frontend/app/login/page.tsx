'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import api from '@/lib/api'
import { Shield, Eye, EyeOff, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const router = useRouter()
  const setUser = useAuthStore((s) => s.setUser)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const { data } = await api.post('/auth/login', { username, password })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)

      const meRes = await api.get('/auth/me')
      setUser(meRes.data)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background grid */}
      <div className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: 'linear-gradient(#00ff88 1px, transparent 1px), linear-gradient(90deg, #00ff88 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      {/* Animated orbs */}
      <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-accent-green/5 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-accent-blue/5 rounded-full blur-3xl" />

      <div className="relative w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <div className="w-16 h-16 bg-surface border border-accent-green/30 rounded-full flex items-center justify-center glow-green">
              <Shield className="w-8 h-8 text-accent-green" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-accent-green font-mono tracking-widest">SENTINEL</h1>
          <p className="text-text-muted text-sm mt-1 font-mono">OSINT Intelligence Platform</p>
          <div className="mt-2 text-xs text-text-muted/60 font-mono">
            CLASSIFICATION: RESTRICTED
          </div>
        </div>

        {/* Login Card */}
        <div className="bg-surface border border-border rounded-lg p-8 shadow-2xl">
          <div className="flex items-center gap-2 mb-6 pb-4 border-b border-border">
            <div className="live-dot" />
            <span className="text-xs font-mono text-text-muted">SECURE AUTHENTICATION REQUIRED</span>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-text-muted mb-1 uppercase tracking-wider">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="sentinel-input font-mono"
                placeholder="operator_id"
                autoComplete="username"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-text-muted mb-1 uppercase tracking-wider">
                Passphrase
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="sentinel-input font-mono pr-10"
                  placeholder="••••••••••••"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-danger text-sm bg-danger/10 border border-danger/20 rounded px-3 py-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span className="font-mono text-xs">{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-accent-green text-background font-bold font-mono py-2.5 rounded
                         hover:bg-accent-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                         text-sm tracking-widest uppercase mt-2"
            >
              {loading ? 'AUTHENTICATING...' : 'AUTHENTICATE'}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-border text-center">
            <p className="text-xs text-text-muted/60 font-mono">
              All access attempts are logged and monitored
            </p>
          </div>
        </div>

        <div className="mt-4 text-center text-xs text-text-muted/40 font-mono">
          SENTINEL v1.0.0 | CYBER OPERATIONS CENTRE
        </div>
      </div>
    </div>
  )
}
