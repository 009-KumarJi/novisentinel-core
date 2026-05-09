'use client'
import { useEffect, useState } from 'react'
import { Copy, Check, Trash2, Plus } from 'lucide-react'
import { api } from '@/lib/api'
import type { ApiKeyRecord } from '@/lib/types'

export default function SettingsPage() {
  const [keys, setKeys] = useState<ApiKeyRecord[]>([])
  const [name, setName] = useState('')
  const [owner, setOwner] = useState('')
  const [creating, setCreating] = useState(false)
  const [newKey, setNewKey] = useState('')
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')

  async function loadKeys() {
    try {
      setKeys(await api.getKeys())
    } catch {
      setError('Failed to load keys')
    }
  }

  useEffect(() => { loadKeys() }, [])

  async function createKey() {
    if (!name || !owner) return
    setCreating(true)
    setError('')
    try {
      const res = await api.createKey(name, owner)
      setNewKey(res.key)
      setName('')
      setOwner('')
      await loadKeys()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create key')
    } finally {
      setCreating(false)
    }
  }

  async function revokeKey(keyId: string) {
    if (!confirm('Revoke this key? It cannot be undone.')) return
    try {
      await api.revokeKey(keyId)
      await loadKeys()
    } catch {
      setError('Failed to revoke key')
    }
  }

  async function copyKey() {
    await navigator.clipboard.writeText(newKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="p-8 space-y-8 max-w-3xl">
      <h1 className="text-lg font-semibold text-[#e6edf3]">Settings</h1>

      {error && (
        <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {/* New key banner */}
      {newKey && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 space-y-3">
          <p className="text-sm font-medium text-green-400">Key created — copy it now</p>
          <p className="text-xs text-[#8b949e]">This key will not be shown again.</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-xs text-[#e6edf3] font-mono overflow-x-auto">
              {newKey}
            </code>
            <button
              onClick={copyKey}
              className="flex items-center gap-1.5 px-3 py-2 bg-[#21262d] hover:bg-[#30363d] rounded text-xs text-[#e6edf3] transition-colors shrink-0"
            >
              {copied ? <Check size={13} className="text-green-400" /> : <Copy size={13} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <button onClick={() => setNewKey('')} className="text-xs text-[#8b949e] hover:text-[#e6edf3]">
            Dismiss
          </button>
        </div>
      )}

      {/* Create Key */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
        <h2 className="text-sm font-medium text-[#e6edf3] mb-4">Create API Key</h2>
        <div className="flex gap-3 flex-wrap">
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Key name (e.g. my-app)"
            className="flex-1 min-w-32 bg-[#0d1117] border border-[#30363d] rounded-md px-3 py-2 text-sm text-[#e6edf3] placeholder-[#484f58] focus:outline-none focus:border-blue-500"
          />
          <input
            value={owner}
            onChange={e => setOwner(e.target.value)}
            placeholder="Owner"
            className="flex-1 min-w-32 bg-[#0d1117] border border-[#30363d] rounded-md px-3 py-2 text-sm text-[#e6edf3] placeholder-[#484f58] focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={createKey}
            disabled={creating || !name || !owner}
            className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-md transition-colors"
          >
            <Plus size={14} />
            {creating ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>

      {/* Keys Table */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[#30363d]">
          <h2 className="text-sm font-medium text-[#e6edf3]">API Keys</h2>
        </div>
        {keys.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-[#8b949e]">No keys yet</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#30363d]">
                {['Prefix', 'Name', 'Owner', 'Status', 'Created', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {keys.map(k => (
                <tr key={k.key_id} className="border-b border-[#21262d] hover:bg-[#1c2128]">
                  <td className="px-4 py-3 font-mono text-xs text-[#e6edf3]">{k.prefix}…</td>
                  <td className="px-4 py-3 text-xs text-[#e6edf3]">{k.name}</td>
                  <td className="px-4 py-3 text-xs text-[#8b949e]">{k.owner}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded border ${
                      k.is_active
                        ? 'bg-green-500/10 text-green-400 border-green-500/20'
                        : 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20'
                    }`}>
                      {k.is_active ? 'active' : 'revoked'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-[#8b949e]">
                    {new Date(k.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    {k.is_active && (
                      <button
                        onClick={() => revokeKey(k.key_id)}
                        className="text-[#8b949e] hover:text-red-400 transition-colors"
                        title="Revoke key"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
