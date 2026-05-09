interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  accent?: 'red' | 'orange' | 'green' | 'blue' | 'default'
}

const ACCENT: Record<string, string> = {
  red:     'text-red-400',
  orange:  'text-orange-400',
  green:   'text-green-400',
  blue:    'text-blue-400',
  default: 'text-[#e6edf3]',
}

export default function StatCard({ label, value, sub, accent = 'default' }: StatCardProps) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
      <p className="text-xs text-[#8b949e] uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-semibold ${ACCENT[accent]}`}>{value}</p>
      {sub && <p className="text-xs text-[#8b949e] mt-1">{sub}</p>}
    </div>
  )
}
