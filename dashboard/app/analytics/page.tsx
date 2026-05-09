'use client'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { StatsResponse, LogEntry } from '@/lib/types'
import StatCard from '@/components/stat-card'
import DetectorDonut from '@/components/charts/detector-donut'
import RiskBar from '@/components/charts/risk-bar'
import ScansOverTime from '@/components/charts/scans-over-time'

function getDayKey(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function last7Days() {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - (6 - i))
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  })
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.getStats(), api.getLogs({ limit: 1000 })])
      .then(([s, l]) => {
        setStats(s)
        setLogs(l)
        setError('')
      })
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load analytics'))
  }, [])

  const detectorData = [
    { name: 'PII',       value: logs.reduce((s, l) => s + l.pii_count, 0) },
    { name: 'Injection', value: logs.reduce((s, l) => s + l.injection_count, 0) },
    { name: 'Secrets',   value: logs.reduce((s, l) => s + l.secrets_count, 0) },
    { name: 'Toxicity',  value: logs.reduce((s, l) => s + l.toxicity_count, 0) },
  ]

  const riskData = ['none', 'low', 'medium', 'high', 'critical'].map(r => ({
    name: r,
    value: stats?.by_risk_level?.[r] ?? 0,
  }))

  const days = last7Days()
  const countsByDay: Record<string, { scans: number; flagged: number }> = {}
  days.forEach(d => { countsByDay[d] = { scans: 0, flagged: 0 } })
  logs.forEach(l => {
    const key = getDayKey(l.created_at)
    if (countsByDay[key]) {
      countsByDay[key].scans++
      if (!l.safe) countsByDay[key].flagged++
    }
  })
  const timelineData = days.map(d => ({ date: d, ...countsByDay[d] }))

  const topDetector = detectorData.reduce((a, b) => b.value > a.value ? b : a, detectorData[0])
  const cleanPct = stats ? ((1 - (stats.flag_rate ?? 0)) * 100).toFixed(1) : '—'

  return (
    <div className="p-8 space-y-8">
      <h1 className="text-lg font-semibold text-[#e6edf3]">Analytics</h1>

      {error && (
        <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          label="Total Detections"
          value={detectorData.reduce((s, d) => s + d.value, 0)}
        />
        <StatCard
          label="Top Threat"
          value={topDetector.value > 0 ? topDetector.name : 'None'}
          sub={topDetector.value > 0 ? `${topDetector.value} detections` : undefined}
          accent="orange"
        />
        <StatCard
          label="Clean Scan Rate"
          value={`${cleanPct}%`}
          accent="green"
        />
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
          <p className="text-sm font-medium text-[#e6edf3] mb-1">Detections by Detector</p>
          <p className="text-xs text-[#8b949e] mb-4">Which safety layer is firing most</p>
          <div className="h-56">
            <DetectorDonut data={detectorData} />
          </div>
        </div>

        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
          <p className="text-sm font-medium text-[#e6edf3] mb-1">Risk Level Distribution</p>
          <p className="text-xs text-[#8b949e] mb-4">Scan count by risk severity</p>
          <div className="h-56">
            <RiskBar data={riskData} />
          </div>
        </div>
      </div>

      {/* Charts row 2 — timeline */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
        <p className="text-sm font-medium text-[#e6edf3] mb-1">Scans Over Time</p>
        <p className="text-xs text-[#8b949e] mb-4">Last 7 days — total vs flagged</p>
        <div className="h-48">
          <ScansOverTime data={timelineData} />
        </div>
      </div>

      {/* Detector breakdown table */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[#30363d]">
          <p className="text-sm font-medium text-[#e6edf3]">Detector Activity</p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#30363d]">
              {['Detector', 'Total Detections', 'Share'].map(h => (
                <th key={h} className="px-5 py-3 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {detectorData.map(({ name, value }) => {
              const total = detectorData.reduce((s, d) => s + d.value, 0)
              const pct = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0'
              return (
                <tr key={name} className="border-b border-[#21262d] hover:bg-[#1c2128]">
                  <td className="px-5 py-3 text-[#e6edf3]">{name}</td>
                  <td className="px-5 py-3 text-[#8b949e]">{value}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-[#21262d] rounded-full h-1.5 max-w-24">
                        <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-[#8b949e]">{pct}%</span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
