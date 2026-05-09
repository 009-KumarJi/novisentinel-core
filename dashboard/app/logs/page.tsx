'use client'
import { Fragment, useCallback, useEffect, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { api } from '@/lib/api'
import type { LogEntry } from '@/lib/types'
import { ActionBadge, RiskBadge, ContextBadge } from '@/components/action-badge'

const ACTIONS = ['', 'allow', 'warn', 'redact', 'block']
const RISKS   = ['', 'none', 'low', 'medium', 'high', 'critical']
const CONTEXTS = ['', 'input', 'output']

function Select({ value, onChange, options, label }: {
  value: string
  onChange: (v: string) => void
  options: string[]
  label: string
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="bg-[#161b22] border border-[#30363d] rounded-md px-3 py-1.5 text-sm text-[#e6edf3] focus:outline-none focus:border-blue-500 appearance-none pr-7"
    >
      <option value="">{label}</option>
      {options.filter(Boolean).map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  )
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [action, setAction] = useState('')
  const [riskLevel, setRiskLevel] = useState('')
  const [context, setContext] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getLogs({
        action: action || undefined,
        risk_level: riskLevel || undefined,
        context: context || undefined,
        limit: 200,
      })
      setLogs(data)
    } finally {
      setLoading(false)
    }
  }, [action, riskLevel, context])

  useEffect(() => { load() }, [load])

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-[#e6edf3]">Scan Logs</h1>
        <p className="text-xs text-[#8b949e] mt-0.5">{logs.length} results</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <Select value={action} onChange={setAction} options={ACTIONS} label="All actions" />
        <Select value={riskLevel} onChange={setRiskLevel} options={RISKS} label="All risk levels" />
        <Select value={context} onChange={setContext} options={CONTEXTS} label="All contexts" />
        {(action || riskLevel || context) && (
          <button
            onClick={() => { setAction(''); setRiskLevel(''); setContext('') }}
            className="text-xs text-[#8b949e] hover:text-[#e6edf3] transition-colors underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#30363d]">
              {['', 'Time', 'Context', 'Risk', 'Action', 'Detections', 'Duration'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-[#8b949e]">Loading…</td></tr>
            ) : logs.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-[#8b949e]">No logs found</td></tr>
            ) : logs.map(row => (
              <Fragment key={row.scan_id}>
                <tr
                  onClick={() => setExpanded(expanded === row.scan_id ? null : row.scan_id)}
                  className="border-b border-[#21262d] hover:bg-[#1c2128] cursor-pointer transition-colors"
                >
                  <td className="pl-4 py-3 text-[#8b949e]">
                    {expanded === row.scan_id ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                  </td>
                  <td className="px-4 py-3 text-xs text-[#8b949e] font-mono whitespace-nowrap">
                    {new Date(row.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3"><ContextBadge value={row.context} /></td>
                  <td className="px-4 py-3"><RiskBadge value={row.risk_level} /></td>
                  <td className="px-4 py-3"><ActionBadge value={row.action} /></td>
                  <td className="px-4 py-3 text-xs text-[#8b949e]">{row.total_detections}</td>
                  <td className="px-4 py-3 text-xs text-[#8b949e]">{row.scan_duration_ms}ms</td>
                </tr>
                {expanded === row.scan_id && (
                  <tr className="bg-[#1c2128] border-b border-[#21262d]">
                    <td colSpan={7} className="px-6 py-4">
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                        {[
                          { label: 'Scan ID', value: row.scan_id.slice(0, 8) + '…' },
                          { label: 'PII', value: row.pii_count },
                          { label: 'Injection', value: row.injection_count },
                          { label: 'Secrets', value: row.secrets_count },
                          { label: 'Toxicity', value: row.toxicity_count },
                          { label: 'Total', value: row.total_detections },
                          { label: 'Safe', value: row.safe ? '✓ Yes' : '✗ No' },
                          { label: 'Duration', value: `${row.scan_duration_ms}ms` },
                        ].map(({ label, value }) => (
                          <div key={label}>
                            <p className="text-[#8b949e] mb-0.5">{label}</p>
                            <p className="text-[#e6edf3] font-mono">{value}</p>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
