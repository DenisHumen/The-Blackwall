import { motion } from 'framer-motion'
import type { SystemMetrics } from '../../types'

interface Props {
  metrics: SystemMetrics | null
  isOnline: boolean
}

export default function SystemHealthBanner({ metrics, isOnline }: Props) {
  const cpuOk = metrics ? metrics.cpu_percent < 80 : false
  const memOk = metrics ? metrics.memory_percent < 80 : false
  const diskOk = metrics ? metrics.disk_percent < 90 : false
  const allHealthy = isOnline && cpuOk && memOk && diskOk

  const healthScore = metrics
    ? Math.round(100 - (metrics.cpu_percent * 0.4 + metrics.memory_percent * 0.35 + metrics.disk_percent * 0.25))
    : 0

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="relative overflow-hidden rounded-2xl border border-dark-600/50 bg-gradient-to-br from-dark-800/90 via-dark-800/70 to-dark-900/90 p-6"
    >
      {/* Background glow */}
      <div
        className="absolute -top-24 -right-24 w-64 h-64 rounded-full blur-3xl opacity-20 pointer-events-none"
        style={{ background: allHealthy ? 'radial-gradient(circle, #22c55e, transparent)' : 'radial-gradient(circle, #e63946, transparent)' }}
      />

      <div className="relative flex items-center justify-between">
        <div className="flex items-center gap-5">
          {/* Animated health ring */}
          <div className="relative">
            <motion.div
              className="w-16 h-16 rounded-full flex items-center justify-center"
              style={{
                background: `conic-gradient(${allHealthy ? '#22c55e' : '#e63946'} ${healthScore}%, transparent ${healthScore}%)`,
                padding: '3px',
              }}
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            >
              <div className="w-full h-full rounded-full bg-dark-800 flex items-center justify-center">
                <span className="text-lg font-bold text-white">{healthScore}</span>
              </div>
            </motion.div>
            {/* Pulse effect */}
            <motion.div
              className="absolute inset-0 rounded-full"
              style={{ border: `2px solid ${allHealthy ? '#22c55e' : '#e63946'}` }}
              animate={{ scale: [1, 1.3, 1], opacity: [0.6, 0, 0.6] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            />
          </div>

          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              Состояние системы
              <span className={`inline-block w-2 h-2 rounded-full ${allHealthy ? 'bg-success' : 'bg-danger'}`} />
            </h2>
            <p className="text-sm text-gray-400 mt-0.5">
              {allHealthy
                ? 'Все системы работают нормально'
                : 'Обнаружены проблемы с производительностью'
              }
            </p>
          </div>
        </div>

        {/* Quick status chips */}
        <div className="hidden md:flex items-center gap-2">
          <StatusChip label="Firewall" status={isOnline} />
          <StatusChip label="CPU" status={cpuOk} />
          <StatusChip label="RAM" status={memOk} />
          <StatusChip label="Disk" status={diskOk} />
        </div>
      </div>

      {/* Uptime bar */}
      {metrics && (
        <div className="relative mt-4 flex items-center gap-3 text-xs text-gray-500">
          <svg className="w-3.5 h-3.5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Uptime: {formatUptime(metrics.uptime_seconds)}
          <span className="mx-1.5 text-dark-600">•</span>
          Load: {metrics.load_avg_1.toFixed(2)} / {metrics.load_avg_5.toFixed(2)} / {metrics.load_avg_15.toFixed(2)}
        </div>
      )}
    </motion.div>
  )
}

function StatusChip({ label, status }: { label: string; status: boolean }) {
  return (
    <span className={`
      inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
      ${status
        ? 'bg-success/10 text-success border border-success/20'
        : 'bg-danger/10 text-danger border border-danger/20'
      }
    `}>
      <span className={`w-1.5 h-1.5 rounded-full ${status ? 'bg-success' : 'bg-danger'}`} />
      {label}
    </span>
  )
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}д ${h}ч ${m}м`
  if (h > 0) return `${h}ч ${m}м`
  return `${m}м`
}
