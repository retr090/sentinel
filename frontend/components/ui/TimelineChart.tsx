'use client'

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'

interface TimelineChartProps {
  data: { date: string; count: number; category?: string }[]
  color?: string
  height?: number
  label?: string
}

export default function TimelineChart({
  data,
  color = '#00ff88',
  height = 160,
  label = 'Events',
}: TimelineChartProps) {
  const formatted = data.map((d) => ({
    ...d,
    date: d.date ? format(new Date(d.date), 'MMM d') : '',
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={formatted} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
        <defs>
          <linearGradient id={`gradient-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.2} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2730" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'JetBrains Mono' }}
          axisLine={{ stroke: '#1e2730' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'JetBrains Mono' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: '#111518',
            border: '1px solid #1e2730',
            borderRadius: 6,
            fontSize: 12,
            fontFamily: 'JetBrains Mono',
          }}
          labelStyle={{ color: '#e2e8f0' }}
          itemStyle={{ color }}
          formatter={(value) => [value, label]}
        />
        <Area
          type="monotone"
          dataKey="count"
          stroke={color}
          strokeWidth={2}
          fill={`url(#gradient-${color.replace('#', '')})`}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
