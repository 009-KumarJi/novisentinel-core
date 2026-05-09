'use client'
import { useEffect, useState, useCallback } from 'react'
import { RefreshCw } from 'lucide-react'
import { api } from '@/lib/api'
import type { StatsResponse, LogEntry } from '@/lib/types'
import StatCard from '@/components/stat-card'
import { ActionBadge, RiskBadge, ContextBadge } from '@/components/action-badge'

export default function OverviewPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [feed, setFeed] = useState<LogEntry[]>([])
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    try {
      const [s, logs] = await Promise.all([
        api.getStats(),
        api.getLogs({ limit: 12 }),
      ])
      setStats(s)
      setFeed(logs)
      setLastUpdated(new Date())
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 10_000)
    return () => clearInterval(id)
  }, [refresh])

  const riskOrder = ['critical', 'high', 'medium', 'low', 'none']

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[#e6edf3]">Overview</h1>
          <p className="text-xs text-[#8b949e] mt-0.5">
            {lastUpdated ? `Updated ${Math.round((Date.now() - lastUpdated.getTime()) / 1000)}s ago` : 'Loading…'}
          </p>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-1.5 text-xs text-[#8b949e] hover:text-[#e6edf3] transition-colors"
        >
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {error && (
        <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Scans" value={stats?.total_scans ?? '—'} />
        <StatCard label="Blocked" value={stats?.blocked ?? '—'} accent="red"
          sub={stats ? `${(((stats.blocked ?? 0) / Math.max(stats.total_scans, 1)) * 100).toFixed(1)}% of total` : undefined} />
        <StatCard label="Flag Rate" value={stats ? `${((stats.flag_rate ?? 0) * 100).toFixed(1)}%` : '—'} accent="orange" />
        <StatCard label="Avg Latency" value={stats ? `${(stats.avg_scan_ms ?? 0).toFixed(0)}ms` : '—'} accent="blue" />
      </div>

      {/* Risk Breakdown Bar */}
      {stats && stats.total_scans > 0 && (
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
          <p className="text-xs text-[#8b949e] uppercase tracking-wider mb-3">Risk Level Distribution</p>
          <div className="flex h-3 rounded-full overflow-hidden gap-0.5">
            {riskOrder.map(level => {
              const count = stats.by_risk_level?.[level] ?? 0
              const pct = (count / stats.total_scans) * 100
              if (pct === 0) return null
              const colors: Record<string, string> = {
                critical: 'bg-red-500', high: 'bg-orange-500',
                medium: 'bg-yellow-500', low: 'bg-blue-500', none: 'bg-zinc-600',
              }
              return (
                <div
                  key={level}
                  style={{ width: `${pct}%` }}
                  className={`${colors[level]} transition-all`}
                  title={`${level}: ${count} (${pct.toFixed(1)}%)`}
                />
              )
            })}
          </div>
          <div className="flex gap-4 mt-3 flex-wrap">
            {riskOrder.map(level => {
              const count = stats.by_risk_level?.[level] ?? 0
              if (count === 0) return null
              return (
                <div key={level} className="flex items-center gap-1.5 text-xs text-[#8b949e]">
                  <RiskBadge value={level} />
                  <span>{count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Live Feed */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[#30363d]">
          <p className="text-sm font-medium text-[#e6edf3]">Live Feed</p>
        </div>
        {feed.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-[#8b949e]">No scans yet</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#30363d]">
                {['Time', 'Context', 'Risk', 'Action', 'Detections', 'Duration'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {feed.map((row, i) => (
                <tr key={row.scan_id} className={`border-b border-[#21262d] hover:bg-[#1c2128] transition-colors ${i === 0 ? 'bg-[#1c2128]/50' : ''}`}>
                  <td className="px-4 py-2.5 text-xs text-[#8b949e] font-mono whitespace-nowrap">
                    {new Date(row.created_at).toLocaleTimeString()}
                  </td>
                  <td className="px-4 py-2.5"><ContextBadge value={row.context} /></td>
                  <td className="px-4 py-2.5"><RiskBadge value={row.risk_level} /></td>
                  <td className="px-4 py-2.5"><ActionBadge value={row.action} /></td>
                  <td className="px-4 py-2.5 text-xs text-[#8b949e]">{row.total_detections}</td>
                  <td className="px-4 py-2.5 text-xs text-[#8b949e]">{row.scan_duration_ms}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
