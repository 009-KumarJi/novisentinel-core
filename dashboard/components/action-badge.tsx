const ACTION_STYLES: Record<string, string> = {
  block:  'bg-red-500/15 text-red-400 border-red-500/30',
  redact: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  warn:   'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  allow:  'bg-green-500/15 text-green-400 border-green-500/30',
}

const RISK_STYLES: Record<string, string> = {
  critical: 'bg-red-500/15 text-red-400 border-red-500/30',
  high:     'bg-orange-500/15 text-orange-400 border-orange-500/30',
  medium:   'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  low:      'bg-blue-500/15 text-blue-400 border-blue-500/30',
  none:     'bg-zinc-500/15 text-zinc-400 border-zinc-500/30',
}

export function ActionBadge({ value }: { value: string }) {
  const cls = ACTION_STYLES[value] ?? 'bg-zinc-500/15 text-zinc-400 border-zinc-500/30'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`}>
      {value}
    </span>
  )
}

export function RiskBadge({ value }: { value: string }) {
  const cls = RISK_STYLES[value] ?? 'bg-zinc-500/15 text-zinc-400 border-zinc-500/30'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`}>
      {value}
    </span>
  )
}

export function ContextBadge({ value }: { value: string | null }) {
  if (!value) return <span className="text-zinc-600 text-xs">—</span>
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-700/50 text-zinc-300 border border-zinc-600/30">
      {value}
    </span>
  )
}
