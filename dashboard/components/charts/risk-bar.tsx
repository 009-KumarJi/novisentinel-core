'use client'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const RISK_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high:     '#f97316',
  medium:   '#eab308',
  low:      '#3b82f6',
  none:     '#4b5563',
}

interface Props {
  data: { name: string; value: number }[]
}

export default function RiskBar({ data }: Props) {
  if (data.every(d => d.value === 0)) return (
    <div className="flex items-center justify-center h-full text-[#8b949e] text-sm">
      No data yet
    </div>
  )

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} barCategoryGap="30%">
        <XAxis
          dataKey="name"
          tick={{ fill: '#8b949e', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#8b949e', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
        />
        <Tooltip
          contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 6 }}
          labelStyle={{ color: '#e6edf3' }}
          itemStyle={{ color: '#8b949e' }}
          cursor={{ fill: 'rgba(255,255,255,0.03)' }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map(entry => (
            <Cell key={entry.name} fill={RISK_COLORS[entry.name] ?? '#4b5563'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
