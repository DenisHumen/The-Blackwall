import { motion } from 'framer-motion'
import type { SystemMetrics } from '../../types'

interface Props {
  metrics: SystemMetrics
}

export default function SystemInfoGrid({ metrics }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.45 }}
      className="grid grid-cols-1 md:grid-cols-3 gap-4"
    >
      {/* Disk */}
      <div className="card-hover group">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-cyan-400/10 text-cyan-400">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
              </svg>
            </div>
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Диск</h3>
          </div>
          <span className="text-[10px] text-gray-600">
            {metrics.disk_used_gb.toFixed(1)} / {metrics.disk_total_gb.toFixed(1)} GB
          </span>
        </div>
        <motion.div
          className="text-2xl font-bold text-white mb-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          {metrics.disk_percent.toFixed(1)}%
        </motion.div>
        <div className="h-2 bg-dark-700/50 rounded-full overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${
              metrics.disk_percent > 90
                ? 'bg-gradient-to-r from-danger to-red-400'
                : metrics.disk_percent > 70
                  ? 'bg-gradient-to-r from-warning to-amber-400'
                  : 'bg-gradient-to-r from-cyan-500 to-cyan-400'
            }`}
            initial={{ width: 0 }}
            animate={{ width: `${metrics.disk_percent}%` }}
            transition={{ duration: 1, delay: 0.5, ease: [0.4, 0, 0.2, 1] }}
          />
        </div>
      </div>

      {/* Load Average */}
      <div className="card-hover group">
        <div className="flex items-center gap-2 mb-3">
          <div className="p-1.5 rounded-lg bg-accent/10 text-accent">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
            </svg>
          </div>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Load Average</h3>
        </div>
        <div className="flex items-end gap-4">
          {[
            { val: metrics.load_avg_1, label: '1 мин', size: 'text-2xl' },
            { val: metrics.load_avg_5, label: '5 мин', size: 'text-lg' },
            { val: metrics.load_avg_15, label: '15 мин', size: 'text-lg' },
          ].map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + i * 0.1 }}
            >
              <div className={`${item.size} font-bold ${i === 0 ? 'text-white' : 'text-gray-400'}`}>
                {item.val.toFixed(2)}
              </div>
              <div className="text-[10px] text-gray-600 mt-0.5">{item.label}</div>
            </motion.div>
          ))}
        </div>
        {/* Mini sparkline bars */}
        <div className="flex items-end gap-1 mt-3 h-6">
          {[
            metrics.load_avg_15,
            metrics.load_avg_15 * 0.9,
            metrics.load_avg_5,
            metrics.load_avg_5 * 1.1,
            metrics.load_avg_1,
            metrics.load_avg_1 * 0.95,
            metrics.load_avg_1,
          ].map((v, i) => (
            <motion.div
              key={i}
              className="flex-1 bg-accent/30 rounded-t"
              initial={{ height: 0 }}
              animate={{ height: `${Math.min((v / 4) * 100, 100)}%` }}
              transition={{ duration: 0.5, delay: 0.7 + i * 0.05 }}
            />
          ))}
        </div>
      </div>

      {/* Uptime */}
      <div className="card-hover group">
        <div className="flex items-center gap-2 mb-3">
          <div className="p-1.5 rounded-lg bg-success/10 text-success">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Uptime</h3>
        </div>
        <motion.div
          className="text-2xl font-bold text-white"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          {formatUptime(metrics.uptime_seconds)}
        </motion.div>
        <p className="text-xs text-gray-500 mt-1">
          {Math.floor(metrics.uptime_seconds / 86400)} дней непрерывной работы
        </p>

        {/* Uptime visual */}
        <div className="flex items-center gap-0.5 mt-3">
          {Array.from({ length: 30 }, (_, i) => (
            <motion.div
              key={i}
              className="flex-1 h-4 rounded-sm bg-success/20"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 + i * 0.02 }}
              title={`День ${i + 1}`}
            >
              <div className="w-full h-full rounded-sm bg-success/40 hover:bg-success/60 transition-colors" />
            </motion.div>
          ))}
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[9px] text-gray-600">30 дней назад</span>
          <span className="text-[9px] text-gray-600">Сегодня</span>
        </div>
      </div>
    </motion.div>
  )
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}д ${h}ч`
  if (h > 0) return `${h}ч ${m}м`
  return `${m}м`
}
