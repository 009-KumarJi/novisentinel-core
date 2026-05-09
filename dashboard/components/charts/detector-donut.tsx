'use client'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const COLORS = ['#3b82f6', '#f97316', '#ef4444', '#a855f7']

interface Props {
  data: { name: string; value: number }[]
}

export default function DetectorDonut({ data }: Props) {
  const total = data.reduce((s, d) => s + d.value, 0)
  if (total === 0) return (
    <div className="flex items-center justify-center h-full text-[#8b949e] text-sm">
      No detections yet
    </div>
  )

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((d, i) => (
            <Cell key={d.name} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 6 }}
          labelStyle={{ color: '#e6edf3' }}
          itemStyle={{ color: '#8b949e' }}
        />
        <Legend
          formatter={(value) => <span style={{ color: '#8b949e', fontSize: 12 }}>{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
