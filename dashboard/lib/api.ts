import type { StatsResponse, LogEntry, ApiKeyRecord, CreateKeyResponse } from './types'

export function getCredentials() {
  if (typeof window === 'undefined') return { baseUrl: '', masterKey: '' }
  return {
    baseUrl: sessionStorage.getItem('ns_base_url') ?? 'http://localhost:8000',
    masterKey: sessionStorage.getItem('ns_master_key') ?? '',
  }
}

export function clearCredentials() {
  sessionStorage.removeItem('ns_master_key')
  sessionStorage.removeItem('ns_base_url')
}

async function mfetch<T>(path: string, options?: RequestInit): Promise<T> {
  const { baseUrl, masterKey } = getCredentials()
  const res = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      'x-master-key': masterKey,
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (body && typeof body.detail === 'string') detail = body.detail
    } catch { /* response wasn't JSON — keep statusText */ }
    throw new Error(`${res.status} ${detail}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  getStats: () => mfetch<StatsResponse>('/v1/stats'),

  getLogs: (params?: {
    action?: string
    risk_level?: string
    context?: string
    since?: string
    limit?: number
  }) => {
    const q = new URLSearchParams()
    if (params?.action) q.set('action', params.action)
    if (params?.risk_level) q.set('risk_level', params.risk_level)
    if (params?.context) q.set('context', params.context)
    if (params?.since) q.set('since', params.since)
    q.set('limit', String(params?.limit ?? 100))
    return mfetch<LogEntry[]>(`/v1/logs?${q}`)
  },

  getKeys: () => mfetch<ApiKeyRecord[]>('/v1/keys'),

  createKey: (name: string, owner: string) =>
    mfetch<CreateKeyResponse>('/v1/keys', {
      method: 'POST',
      body: JSON.stringify({ name, owner }),
    }),

  revokeKey: (keyId: string) =>
    mfetch<void>(`/v1/keys/${keyId}`, { method: 'DELETE' }),
}
