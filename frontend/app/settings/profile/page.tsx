'use client'

import { useState, useRef } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import { useAuthStore } from '@/lib/store'
import { User, Camera, Save, CheckCircle, AlertCircle } from 'lucide-react'

export default function ProfilePage() {
  const { user, setUser } = useAuthStore()
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [avatar, setAvatar] = useState<string>(user?.avatar_url ?? '')
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const initials = (user?.full_name ?? user?.username ?? '??').slice(0, 2).toUpperCase()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('File must be an image (JPG, PNG, GIF, etc.)')
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      setError('Image must be under 2 MB')
      return
    }
    setError('')
    const reader = new FileReader()
    reader.onload = () => setAvatar(reader.result as string)
    reader.readAsDataURL(file)
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      const { data } = await api.put('/users/me', {
        full_name: fullName || undefined,
        email,
        avatar_url: avatar || null,
      })
      setUser(data)
      setSuccess('Profile updated successfully')
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  return (
    <AppLayout title="SENTINEL / Profile Settings">
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-lg font-bold flex items-center gap-2">
            <User className="w-5 h-5 text-accent-green" />
            Profile Settings
          </h1>
          <p className="text-xs text-text-muted mt-0.5">Update your personal information and profile photo</p>
        </div>

        <form onSubmit={handleSave} className="sentinel-card space-y-5">
          {/* Avatar */}
          <div className="flex items-center gap-5">
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="relative w-20 h-20 rounded-full overflow-hidden group flex-shrink-0 focus:outline-none"
            >
              {avatar ? (
                <img src={avatar} alt="avatar" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full bg-accent-green/20 border-2 border-accent-green/30 flex items-center justify-center">
                  <span className="text-2xl font-bold font-mono text-accent-green">{initials}</span>
                </div>
              )}
              <div className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity rounded-full">
                <Camera className="w-6 h-6 text-white" />
              </div>
            </button>

            <div className="space-y-1.5">
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="text-xs border border-border rounded px-3 py-1.5 hover:bg-background/50 text-text-muted transition-colors"
              >
                Change Photo
              </button>
              {avatar && (
                <button
                  type="button"
                  onClick={() => { setAvatar(''); if (fileRef.current) fileRef.current.value = '' }}
                  className="ml-2 text-xs text-danger hover:text-danger/80"
                >
                  Remove
                </button>
              )}
              <p className="text-[10px] text-text-muted font-mono">JPG, PNG or GIF — max 2 MB</p>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          {/* Fields */}
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-text-muted uppercase tracking-wider mb-1">
                Username
              </label>
              <input
                value={user?.username ?? ''}
                disabled
                className="sentinel-input opacity-50 cursor-not-allowed"
              />
              <p className="text-[10px] text-text-muted mt-1 font-mono">Username cannot be changed</p>
            </div>

            <div>
              <label className="block text-xs font-mono text-text-muted uppercase tracking-wider mb-1">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="sentinel-input"
                placeholder="Your full name"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-text-muted uppercase tracking-wider mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="sentinel-input"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-text-muted uppercase tracking-wider mb-1">
                Role
              </label>
              <div className="flex items-center gap-2 h-9">
                <span className="text-xs font-mono px-2 py-1 bg-accent-green/10 border border-accent-green/20 text-accent-green rounded uppercase">
                  {user?.role}
                </span>
                <span className="text-[10px] text-text-muted font-mono">Managed by administrators</span>
              </div>
            </div>
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
              disabled={saving}
              className="flex items-center gap-2 bg-accent-green text-background font-bold text-sm px-4 py-2 rounded hover:bg-accent-green/90 disabled:opacity-50 transition-colors"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </AppLayout>
  )
}
