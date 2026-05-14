'use client'

import { useEffect, useState, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import { useAuthStore } from '@/lib/store'
import { useRouter } from 'next/navigation'
import { Users, Plus, Edit2, Trash2, KeyRound, ToggleLeft, ToggleRight, X, AlertCircle, CheckCircle } from 'lucide-react'
import { formatRelativeTime } from '@/lib/utils'

interface UserRecord {
  id: number
  username: string
  email: string
  full_name?: string
  role: string
  is_active: boolean
  force_password_change: boolean
  last_login?: string
  created_at: string
}

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-accent-green/10 text-accent-green border-accent-green/20',
  analyst: 'bg-accent-blue/10 text-accent-blue border-accent-blue/20',
  viewer: 'bg-border/50 text-text-muted border-border',
}

function Initials({ name, username }: { name?: string; username: string }) {
  const text = (name ?? username).slice(0, 2).toUpperCase()
  return (
    <div className="w-8 h-8 bg-accent-green/20 border border-accent-green/30 rounded-full flex items-center justify-center flex-shrink-0">
      <span className="text-[10px] font-bold font-mono text-accent-green">{text}</span>
    </div>
  )
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="sentinel-card w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold font-mono">{title}</h3>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

function FieldError({ msg }: { msg: string }) {
  return (
    <div className="flex items-center gap-2 text-danger text-xs bg-danger/10 border border-danger/20 rounded px-3 py-2 mt-2">
      <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
      <span className="font-mono">{msg}</span>
    </div>
  )
}

export default function AdminUsersPage() {
  const { user: me } = useAuthStore()
  const router = useRouter()
  const [users, setUsers] = useState<UserRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [modalErr, setModalErr] = useState('')

  // Modals
  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<UserRecord | null>(null)
  const [resetTarget, setResetTarget] = useState<UserRecord | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<UserRecord | null>(null)

  // Create form
  const [createForm, setCreateForm] = useState({
    username: '', email: '', password: '', full_name: '', role: 'viewer', force_password_change: true,
  })
  // Edit form
  const [editForm, setEditForm] = useState({
    full_name: '', email: '', role: 'viewer', is_active: true, force_password_change: false,
  })
  // Reset form
  const [resetPassword, setResetPassword] = useState('')

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/admin/users')
      setUsers(data)
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => {
    if (me?.role !== 'admin') {
      router.push('/dashboard')
      return
    }
    fetchUsers()
  }, [me, router, fetchUsers])

  const openEdit = (u: UserRecord) => {
    setEditForm({ full_name: u.full_name ?? '', email: u.email, role: u.role, is_active: u.is_active, force_password_change: u.force_password_change })
    setEditTarget(u)
    setModalErr('')
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setModalErr('')
    try {
      await api.post('/admin/users', createForm)
      setCreateOpen(false)
      setCreateForm({ username: '', email: '', password: '', full_name: '', role: 'viewer', force_password_change: true })
      fetchUsers()
    } catch (err: any) {
      setModalErr(err.response?.data?.detail ?? 'Failed to create user')
    }
  }

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editTarget) return
    setModalErr('')
    try {
      await api.put(`/admin/users/${editTarget.id}`, editForm)
      setEditTarget(null)
      fetchUsers()
    } catch (err: any) {
      setModalErr(err.response?.data?.detail ?? 'Failed to update user')
    }
  }

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!resetTarget) return
    setModalErr('')
    if (resetPassword.length < 8) { setModalErr('Password must be at least 8 characters'); return }
    try {
      await api.put(`/admin/users/${resetTarget.id}/reset-password`, { new_password: resetPassword })
      setResetTarget(null)
      setResetPassword('')
    } catch (err: any) {
      setModalErr(err.response?.data?.detail ?? 'Failed to reset password')
    }
  }

  const handleToggleStatus = async (u: UserRecord) => {
    try {
      await api.patch(`/admin/users/${u.id}/status`, { is_active: !u.is_active })
      fetchUsers()
    } catch {}
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await api.delete(`/admin/users/${deleteTarget.id}`)
      setDeleteTarget(null)
      fetchUsers()
    } catch {}
  }

  const totalActive = users.filter((u) => u.is_active).length

  return (
    <AppLayout title="SENTINEL / User Management">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              <Users className="w-5 h-5 text-accent-green" /> User Management
            </h1>
            <p className="text-xs text-text-muted mt-0.5">Create and manage operator accounts</p>
          </div>
          <button
            onClick={() => { setModalErr(''); setCreateOpen(true) }}
            className="flex items-center gap-1.5 text-xs bg-accent-green/20 border border-accent-green/30 rounded px-3 py-1.5 text-accent-green hover:bg-accent-green/30 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" /> Create User
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Total Users', value: users.length, color: 'text-text-primary' },
            { label: 'Active', value: totalActive, color: 'text-accent-green' },
            { label: 'Disabled', value: users.length - totalActive, color: 'text-danger' },
          ].map((s) => (
            <div key={s.label} className="sentinel-card text-center py-2">
              <div className={`text-xl font-bold font-mono ${s.color}`}>{s.value}</div>
              <div className="text-[10px] text-text-muted mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Table */}
        <div className="sentinel-card">
          <div className="overflow-x-auto">
            <table className="sentinel-table min-w-full">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Last Login</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={6} className="text-center py-8 text-text-muted font-mono text-xs">LOADING...</td></tr>
                )}
                {!loading && users.length === 0 && (
                  <tr><td colSpan={6} className="text-center py-8 text-text-muted font-mono text-xs">NO USERS FOUND</td></tr>
                )}
                {users.map((u) => (
                  <tr key={u.id} className={!u.is_active ? 'opacity-50' : ''}>
                    <td>
                      <div className="flex items-center gap-2.5">
                        <Initials name={u.full_name} username={u.username} />
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-text-primary truncate">{u.full_name || u.username}</div>
                          <div className="text-[10px] text-text-muted font-mono truncate">{u.email}</div>
                          {u.id === me?.id && (
                            <span className="text-[9px] font-mono text-accent-blue">(you)</span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border uppercase ${ROLE_COLORS[u.role] ?? ROLE_COLORS.viewer}`}>
                        {u.role}
                      </span>
                    </td>
                    <td>
                      <div className="flex flex-col gap-0.5">
                        <span className={`text-xs font-mono ${u.is_active ? 'text-accent-green' : 'text-danger'}`}>
                          {u.is_active ? 'ACTIVE' : 'DISABLED'}
                        </span>
                        {u.force_password_change && (
                          <span className="text-[9px] font-mono text-warning">MUST CHANGE PWD</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className="text-xs text-text-muted font-mono">
                        {u.last_login ? formatRelativeTime(u.last_login) : 'Never'}
                      </span>
                    </td>
                    <td>
                      <span className="text-xs text-text-muted font-mono">{formatRelativeTime(u.created_at)}</span>
                    </td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => openEdit(u)}
                          className="p-1 rounded text-text-muted hover:text-accent-blue hover:bg-accent-blue/10 transition-colors"
                          title="Edit"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => { setResetTarget(u); setResetPassword(''); setModalErr('') }}
                          className="p-1 rounded text-text-muted hover:text-warning hover:bg-warning/10 transition-colors"
                          title="Reset Password"
                        >
                          <KeyRound className="w-3.5 h-3.5" />
                        </button>
                        {u.id !== me?.id && (
                          <>
                            <button
                              onClick={() => handleToggleStatus(u)}
                              className="p-1 rounded text-text-muted hover:text-accent-green hover:bg-accent-green/10 transition-colors"
                              title={u.is_active ? 'Disable' : 'Enable'}
                            >
                              {u.is_active
                                ? <ToggleRight className="w-3.5 h-3.5 text-accent-green" />
                                : <ToggleLeft className="w-3.5 h-3.5" />}
                            </button>
                            <button
                              onClick={() => setDeleteTarget(u)}
                              className="p-1 rounded text-text-muted hover:text-danger hover:bg-danger/10 transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Create User Modal ── */}
      {createOpen && (
        <Modal title="CREATE USER" onClose={() => setCreateOpen(false)}>
          <form onSubmit={handleCreate} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-text-muted block mb-1">Username *</label>
                <input type="text" required value={createForm.username}
                  onChange={(e) => setCreateForm((f) => ({ ...f, username: e.target.value }))}
                  className="sentinel-input font-mono" placeholder="operator_id" />
              </div>
              <div>
                <label className="text-xs text-text-muted block mb-1">Role</label>
                <select value={createForm.role}
                  onChange={(e) => setCreateForm((f) => ({ ...f, role: e.target.value }))}
                  className="sentinel-input">
                  <option value="viewer">Viewer</option>
                  <option value="analyst">Analyst</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs text-text-muted block mb-1">Full Name</label>
              <input type="text" value={createForm.full_name}
                onChange={(e) => setCreateForm((f) => ({ ...f, full_name: e.target.value }))}
                className="sentinel-input" placeholder="Display name" />
            </div>
            <div>
              <label className="text-xs text-text-muted block mb-1">Email *</label>
              <input type="email" required value={createForm.email}
                onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
                className="sentinel-input font-mono" />
            </div>
            <div>
              <label className="text-xs text-text-muted block mb-1">Temporary Password *</label>
              <input type="password" required minLength={8} value={createForm.password}
                onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
                className="sentinel-input font-mono" placeholder="Min 8 characters" />
            </div>
            <label className="flex items-center gap-2 text-xs text-text-muted cursor-pointer">
              <input type="checkbox" checked={createForm.force_password_change}
                onChange={(e) => setCreateForm((f) => ({ ...f, force_password_change: e.target.checked }))}
                className="rounded" />
              Force password change on first login
            </label>
            {modalErr && <FieldError msg={modalErr} />}
            <div className="flex gap-2 justify-end pt-2">
              <button type="button" onClick={() => setCreateOpen(false)}
                className="text-xs border border-border rounded px-3 py-1.5 hover:bg-surface text-text-muted">Cancel</button>
              <button type="submit"
                className="text-xs bg-accent-green text-background rounded px-3 py-1.5 hover:bg-accent-green/90 font-bold">
                Create User
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* ── Edit User Modal ── */}
      {editTarget && (
        <Modal title={`EDIT: ${editTarget.username.toUpperCase()}`} onClose={() => setEditTarget(null)}>
          <form onSubmit={handleEdit} className="space-y-3">
            <div>
              <label className="text-xs text-text-muted block mb-1">Full Name</label>
              <input type="text" value={editForm.full_name}
                onChange={(e) => setEditForm((f) => ({ ...f, full_name: e.target.value }))}
                className="sentinel-input" />
            </div>
            <div>
              <label className="text-xs text-text-muted block mb-1">Email *</label>
              <input type="email" required value={editForm.email}
                onChange={(e) => setEditForm((f) => ({ ...f, email: e.target.value }))}
                className="sentinel-input font-mono" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-text-muted block mb-1">Role</label>
                <select value={editForm.role}
                  onChange={(e) => setEditForm((f) => ({ ...f, role: e.target.value }))}
                  className="sentinel-input">
                  <option value="viewer">Viewer</option>
                  <option value="analyst">Analyst</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-text-muted block mb-1">Status</label>
                <select value={editForm.is_active ? '1' : '0'}
                  onChange={(e) => setEditForm((f) => ({ ...f, is_active: e.target.value === '1' }))}
                  className="sentinel-input"
                  disabled={editTarget.id === me?.id}>
                  <option value="1">Active</option>
                  <option value="0">Disabled</option>
                </select>
              </div>
            </div>
            <label className="flex items-center gap-2 text-xs text-text-muted cursor-pointer">
              <input type="checkbox" checked={editForm.force_password_change}
                onChange={(e) => setEditForm((f) => ({ ...f, force_password_change: e.target.checked }))}
                className="rounded" />
              Require password change on next login
            </label>
            {modalErr && <FieldError msg={modalErr} />}
            <div className="flex gap-2 justify-end pt-2">
              <button type="button" onClick={() => setEditTarget(null)}
                className="text-xs border border-border rounded px-3 py-1.5 hover:bg-surface text-text-muted">Cancel</button>
              <button type="submit"
                className="text-xs bg-accent-blue text-white rounded px-3 py-1.5 hover:bg-accent-blue/90 font-bold">
                Save Changes
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* ── Reset Password Modal ── */}
      {resetTarget && (
        <Modal title={`RESET PASSWORD: ${resetTarget.username.toUpperCase()}`} onClose={() => setResetTarget(null)}>
          <form onSubmit={handleReset} className="space-y-3">
            <p className="text-xs text-text-muted font-mono">
              Set a new temporary password for <span className="text-text-primary">{resetTarget.username}</span>.
              The user will be required to change it on next login.
            </p>
            <div>
              <label className="text-xs text-text-muted block mb-1">New Password *</label>
              <input type="password" required minLength={8} value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
                className="sentinel-input font-mono" placeholder="Min 8 characters" />
            </div>
            {modalErr && <FieldError msg={modalErr} />}
            <div className="flex gap-2 justify-end pt-2">
              <button type="button" onClick={() => setResetTarget(null)}
                className="text-xs border border-border rounded px-3 py-1.5 hover:bg-surface text-text-muted">Cancel</button>
              <button type="submit"
                className="text-xs bg-warning text-background rounded px-3 py-1.5 hover:bg-warning/90 font-bold">
                Reset Password
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* ── Delete Confirmation Modal ── */}
      {deleteTarget && (
        <Modal title="CONFIRM DELETE" onClose={() => setDeleteTarget(null)}>
          <div className="space-y-4">
            <p className="text-sm text-text-muted">
              Permanently delete user{' '}
              <span className="font-mono text-danger font-bold">{deleteTarget.username}</span>?
              This action cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDeleteTarget(null)}
                className="text-xs border border-border rounded px-3 py-1.5 hover:bg-surface text-text-muted">Cancel</button>
              <button onClick={handleDelete}
                className="text-xs bg-danger text-white rounded px-3 py-1.5 hover:bg-danger/80 font-bold">
                Delete User
              </button>
            </div>
          </div>
        </Modal>
      )}
    </AppLayout>
  )
}
