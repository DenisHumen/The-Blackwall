import { useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import type { TrafficPoint } from '../types'

interface Props {
  data: TrafficPoint[]
}

const RX_COLOR = '#e63946'
const TX_COLOR = '#22c55e'

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
      <motion.div
        className="h-[300px] flex items-center justify-center text-gray-600"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <div className="text-center">
          <motion.svg
            className="w-12 h-12 mx-auto mb-3 text-gray-700"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={0.8}
            animate={{ opacity: [0.3, 0.6, 0.3] }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
          </motion.svg>
          <p className="text-sm">Ожидание данных о трафике...</p>
          <p className="text-xs text-gray-700 mt-1">Данные появятся автоматически</p>
        </div>
      </motion.div>
    )
  }

  // Compute totals for summary
  const lastPoint = chartData[chartData.length - 1]

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.8 }}
    >
      {/* Mini summary above chart */}
      <div className="flex items-center gap-6 mb-4">
        <div className="flex items-center gap-2">
          <span className="w-3 h-1 bg-accent rounded-full" />
          <span className="text-xs text-gray-400">Входящий</span>
          {lastPoint && (
            <span className="text-xs font-semibold text-accent ml-1">{lastPoint.rx} {unit}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-1 bg-green-500 rounded-full" />
          <span className="text-xs text-gray-400">Исходящий</span>
          {lastPoint && (
            <span className="text-xs font-semibold text-green-500 ml-1">{lastPoint.tx} {unit}</span>
          )}
        </div>
      </div>

      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="rxGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={RX_COLOR} stopOpacity={0.25} />
                <stop offset="50%" stopColor={RX_COLOR} stopOpacity={0.08} />
                <stop offset="100%" stopColor={RX_COLOR} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="txGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={TX_COLOR} stopOpacity={0.2} />
                <stop offset="50%" stopColor={TX_COLOR} stopOpacity={0.06} />
                <stop offset="100%" stopColor={TX_COLOR} stopOpacity={0} />
              </linearGradient>
              {/* Glow filters */}
              <filter id="glow-rx">
                <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <filter id="glow-tx">
                <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a1b23" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="transparent"
              tick={{ fill: '#3a3b47', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              stroke="transparent"
              tick={{ fill: '#3a3b47', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}`}
              label={{ value: unit, position: 'insideTopLeft', fill: '#3a3b47', fontSize: 10, dy: -10 }}
              width={45}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#111218',
                border: '1px solid #23242e',
                borderRadius: '12px',
                color: '#e5e5e5',
                fontSize: 12,
                boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
                padding: '10px 14px',
              }}
              formatter={(value: number, name: string) => [
                `${value.toFixed(2)} ${unit}`,
                name === 'rx' ? '↓ Входящий' : '↑ Исходящий'
              ]}
              cursor={{ stroke: '#2c2d3a', strokeWidth: 1 }}
            />
            <Area
              type="monotone"
              dataKey="rx"
              stroke={RX_COLOR}
              strokeWidth={2}
              fill="url(#rxGrad)"
              name="rx"
              dot={false}
              activeDot={{ r: 4, fill: RX_COLOR, stroke: '#0b0c10', strokeWidth: 2 }}
              animationDuration={1200}
              animationEasing="ease-in-out"
            />
            <Area
              type="monotone"
              dataKey="tx"
              stroke={TX_COLOR}
              strokeWidth={2}
              fill="url(#txGrad)"
              name="tx"
              dot={false}
              activeDot={{ r: 4, fill: TX_COLOR, stroke: '#0b0c10', strokeWidth: 2 }}
              animationDuration={1200}
              animationEasing="ease-in-out"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  )
}
