'use client'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

interface Props {
  data: { date: string; scans: number; flagged: number }[]
}

export default function ScansOverTime({ data }: Props) {
  if (data.every(d => d.scans === 0)) return (
    <div className="flex items-center justify-center h-full text-[#8b949e] text-sm">
      No data yet
    </div>
  )

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#8b949e', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#8b949e', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
        />
        <Tooltip
          contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 6 }}
          labelStyle={{ color: '#e6edf3' }}
          itemStyle={{ color: '#8b949e' }}
        />
        <Line type="monotone" dataKey="scans" stroke="#3b82f6" strokeWidth={2} dot={false} name="Total" />
        <Line type="monotone" dataKey="flagged" stroke="#ef4444" strokeWidth={2} dot={false} name="Flagged" />
      </LineChart>
    </ResponsiveContainer>
  )
}
