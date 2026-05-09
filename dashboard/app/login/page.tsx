'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Shield, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [baseUrl, setBaseUrl] = useState('http://localhost:8000')
  const [masterKey, setMasterKey] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${baseUrl.replace(/\/$/, '')}/v1/stats`, {
        headers: { 'x-master-key': masterKey },
      })
      if (!res.ok) throw new Error(res.status === 401 ? 'Invalid master key' : `Server returned ${res.status}`)
      sessionStorage.setItem('ns_base_url', baseUrl.replace(/\/$/, ''))
      sessionStorage.setItem('ns_master_key', masterKey)
      router.replace('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not connect')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0d1117] p-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-3 mb-8">
          <Shield size={28} className="text-blue-400" />
          <h1 className="text-xl font-semibold text-[#e6edf3]">NoviSentinel</h1>
        </div>

        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
          <h2 className="text-sm font-medium text-[#e6edf3] mb-1">Sign in</h2>
          <p className="text-xs text-[#8b949e] mb-5">Enter your API URL and master key</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-[#8b949e] mb-1.5">API URL</label>
              <input
                value={baseUrl}
                onChange={e => setBaseUrl(e.target.value)}
                placeholder="http://localhost:8000"
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-md px-3 py-2 text-sm text-[#e6edf3] placeholder-[#484f58] focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs text-[#8b949e] mb-1.5">Master Key</label>
              <input
                type="password"
                value={masterKey}
                onChange={e => setMasterKey(e.target.value)}
                placeholder="dev-master-key"
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-md px-3 py-2 text-sm text-[#e6edf3] placeholder-[#484f58] focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
                <AlertCircle size={13} />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !masterKey}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium py-2 rounded-md transition-colors"
            >
              {loading ? 'Connecting…' : 'Connect'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
