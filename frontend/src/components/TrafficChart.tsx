import { useMemo } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import type { TrafficPoint } from '../types'

interface Props {
  data: TrafficPoint[]
}

// UniFi-style colors
const RX_COLOR = '#e63946'  // Red accent for download
const TX_COLOR = '#22c55e'  // Green for upload

export default function TrafficChart({ data }: Props) {
  const { chartData, unit } = useMemo(() => {
    if (!data.length) return { chartData: [], unit: 'KB/s', divider: 1024 }

    const maxVal = Math.max(
      ...data.map(d => Math.max(d.rx_rate, d.tx_rate))
    )

    let unit: string
    let divider: number

    if (maxVal >= 1024 * 1024 * 1024) {
      unit = 'GB/s'; divider = 1024 ** 3
    } else if (maxVal >= 1024 * 1024) {
      unit = 'MB/s'; divider = 1024 ** 2
    } else if (maxVal >= 1024) {
      unit = 'KB/s'; divider = 1024
    } else {
      unit = 'B/s'; divider = 1
    }

    const chartData = data.map(d => ({
      time: new Date(d.timestamp).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
      rx: +(d.rx_rate / divider).toFixed(2),
      tx: +(d.tx_rate / divider).toFixed(2),
    }))

    return { chartData, unit, divider }
  }, [data])

  if (!chartData.length) {
    return (
      <div className="h-[300px] flex items-center justify-center text-gray-600">
        <div className="text-center">
          <svg className="w-10 h-10 mx-auto mb-2 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
          </svg>
          Нет данных о трафике
        </div>
      </div>
    )
  }

  return (
    <div className="h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="rxGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={RX_COLOR} stopOpacity={0.2} />
              <stop offset="95%" stopColor={RX_COLOR} stopOpacity={0} />
            </linearGradient>
            <linearGradient id="txGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={TX_COLOR} stopOpacity={0.15} />
              <stop offset="95%" stopColor={TX_COLOR} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#23242e" vertical={false} />
          <XAxis
            dataKey="time"
            stroke="transparent"
            tick={{ fill: '#4a4b59', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="transparent"
            tick={{ fill: '#4a4b59', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${v}`}
            label={{ value: unit, position: 'insideTopLeft', fill: '#4a4b59', fontSize: 10, dy: -10 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1b23',
              border: '1px solid #2c2d3a',
              borderRadius: '12px',
              color: '#e5e5e5',
              fontSize: 12,
              boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
            }}
            formatter={(value: number, name: string) => [
              `${value.toFixed(2)} ${unit}`,
              name === 'rx' ? '↓ Входящий' : '↑ Исходящий'
            ]}
          />
          <Area
            type="monotone"
            dataKey="rx"
            stroke={RX_COLOR}
            strokeWidth={2}
            fill="url(#rxGrad)"
            name="rx"
            dot={false}
            activeDot={{ r: 3, fill: RX_COLOR }}
          />
          <Area
            type="monotone"
            dataKey="tx"
            stroke={TX_COLOR}
            strokeWidth={2}
            fill="url(#txGrad)"
            name="tx"
            dot={false}
            activeDot={{ r: 3, fill: TX_COLOR }}
          />
        </AreaChart>
      </ResponsiveContainer>
      <div className="flex justify-center gap-6 mt-3 text-xs text-gray-500">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-accent rounded" /> Входящий
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-green-500 rounded" /> Исходящий
        </span>
      </div>
    </div>
  )
}
