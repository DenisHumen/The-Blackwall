import { motion } from 'framer-motion'
import clsx from 'clsx'

interface Props {
  title: string
  value: string
  subtitle?: string
  percent: number
  icon: React.ReactNode
  color?: 'accent' | 'success' | 'warning' | 'danger' | 'cyan'
  delay?: number
}

const colorMap = {
  accent: { stroke: '#e63946', glow: 'rgba(230, 57, 70, 0.3)', bg: 'bg-accent/10', text: 'text-accent' },
  success: { stroke: '#22c55e', glow: 'rgba(34, 197, 94, 0.3)', bg: 'bg-success/10', text: 'text-success' },
  warning: { stroke: '#f59e0b', glow: 'rgba(245, 158, 11, 0.3)', bg: 'bg-warning/10', text: 'text-warning' },
  danger: { stroke: '#ef4444', glow: 'rgba(239, 68, 68, 0.3)', bg: 'bg-danger/10', text: 'text-danger' },
  cyan: { stroke: '#22d3ee', glow: 'rgba(34, 211, 238, 0.3)', bg: 'bg-cyan-400/10', text: 'text-cyan-400' },
}

function getAutoColor(percent: number): 'accent' | 'success' | 'warning' | 'danger' {
  if (percent > 90) return 'danger'
  if (percent > 70) return 'warning'
  return 'accent'
}

export default function GaugeCard({ title, value, subtitle, percent, icon, color, delay = 0 }: Props) {
  const resolvedColor = color ?? getAutoColor(percent)
  const c = colorMap[resolvedColor]
  const radius = 40
  const circumference = 2 * Math.PI * radius
  const dashOffset = circumference - (Math.min(percent, 100) / 100) * circumference

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="card-hover group relative"
    >
      <div className="flex items-center gap-4">
        {/* SVG Gauge */}
        <div className="relative flex-shrink-0">
          <svg width="96" height="96" viewBox="0 0 96 96" className="transform -rotate-90">
            {/* Background ring */}
            <circle
              cx="48" cy="48" r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth="6"
              className="text-dark-700/50"
            />
            {/* Animated ring */}
            <motion.circle
              cx="48" cy="48" r={radius}
              fill="none"
              stroke={c.stroke}
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: dashOffset }}
              transition={{ duration: 1.2, delay: delay + 0.2, ease: [0.4, 0, 0.2, 1] }}
              style={{ filter: `drop-shadow(0 0 6px ${c.glow})` }}
            />
          </svg>
          {/* Center icon */}
          <div className={clsx('absolute inset-0 flex items-center justify-center', c.text)}>
            {icon}
          </div>
        </div>

        {/* Text content */}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{title}</p>
          <motion.p
            className={clsx('text-2xl font-bold mt-0.5', c.text)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: delay + 0.4 }}
          >
            {value}
          </motion.p>
          {subtitle && (
            <p className="text-[11px] text-gray-500 mt-0.5 truncate">{subtitle}</p>
          )}
        </div>
      </div>
    </motion.div>
  )
}
