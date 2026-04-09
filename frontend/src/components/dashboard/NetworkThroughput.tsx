import { motion } from 'framer-motion'

interface Props {
  rxRate: number
  txRate: number
  rxTotal: number
  txTotal: number
}

export default function NetworkThroughput({ rxRate, txRate, rxTotal, txTotal }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="card-hover"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Сеть</h3>
        <div className="flex items-center gap-1.5">
          <motion.span
            className="w-1.5 h-1.5 rounded-full bg-success"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
          <span className="text-[10px] text-gray-600">Live</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Download */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-accent/10">
              <svg className="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
            </div>
            <span className="text-xs text-gray-400">Входящий</span>
          </div>
          <motion.div
            className="text-xl font-bold text-white"
            key={rxRate}
            initial={{ opacity: 0.5 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            {formatBytes(rxRate)}/s
          </motion.div>
          <div className="text-[10px] text-gray-600">
            Всего: {formatBytes(rxTotal)}
          </div>
          {/* Mini bar */}
          <div className="h-1 bg-dark-700/50 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-accent to-accent-light rounded-full"
              animate={{ width: `${Math.min(Math.max((rxRate / 1048576) * 10, 2), 100)}%` }}
              transition={{ duration: 0.8 }}
            />
          </div>
        </div>

        {/* Upload */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-success/10">
              <svg className="w-4 h-4 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <span className="text-xs text-gray-400">Исходящий</span>
          </div>
          <motion.div
            className="text-xl font-bold text-white"
            key={txRate}
            initial={{ opacity: 0.5 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            {formatBytes(txRate)}/s
          </motion.div>
          <div className="text-[10px] text-gray-600">
            Всего: {formatBytes(txTotal)}
          </div>
          {/* Mini bar */}
          <div className="h-1 bg-dark-700/50 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-success to-emerald-400 rounded-full"
              animate={{ width: `${Math.min(Math.max((txRate / 1048576) * 10, 2), 100)}%` }}
              transition={{ duration: 0.8 }}
            />
          </div>
        </div>
      </div>
    </motion.div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.min(Math.floor(Math.log(Math.abs(bytes)) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, i)).toFixed(i > 1 ? 2 : 0)} ${units[i]}`
}
