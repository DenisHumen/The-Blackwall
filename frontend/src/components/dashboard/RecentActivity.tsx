import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect } from 'react'

interface ActivityItem {
  id: string
  time: string
  action: 'block' | 'allow' | 'alert' | 'system'
  source: string
  message: string
}

const actionConfig = {
  block: {
    color: 'text-danger',
    bg: 'bg-danger/10',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
      </svg>
    ),
  },
  allow: {
    color: 'text-success',
    bg: 'bg-success/10',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
      </svg>
    ),
  },
  alert: {
    color: 'text-warning',
    bg: 'bg-warning/10',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
    ),
  },
  system: {
    color: 'text-cyan-400',
    bg: 'bg-cyan-400/10',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17l-5.384-3.372M11.42 15.17l4.653-3.372M11.42 15.17V20.28a.938.938 0 01-1.475.768l-5.168-3.233A1.875 1.875 0 014 16.19V8.064a1.875 1.875 0 01.776-1.52l5.168-3.233a1.875 1.875 0 011.476-.012l5.168 3.233c.482.301.776.826.776 1.52v.47" />
      </svg>
    ),
  },
}

export default function RecentActivity() {
  const [activities, setActivities] = useState<ActivityItem[]>([])

  useEffect(() => {
    fetchActivity()
    const interval = setInterval(fetchActivity, 10000)
    return () => clearInterval(interval)
  }, [])

  async function fetchActivity() {
    try {
      const res = await fetch('/api/logs/recent?limit=8', { credentials: 'include' })
      if (res.ok) {
        setActivities(await res.json())
        return
      }
    } catch { /* API not available yet */ }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="card-hover"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">
          Последние события
        </h3>
        <motion.div
          className="flex items-center gap-1.5"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-accent" />
          <span className="text-[10px] text-gray-600">Real-time</span>
        </motion.div>
      </div>

      <div className="space-y-1.5 max-h-[320px] overflow-y-auto pr-1">
        {activities.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-gray-600">
            <svg className="w-8 h-8 mb-2 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
            </svg>
            <p className="text-xs">Нет событий</p>
            <p className="text-[10px] text-gray-700 mt-0.5">Данные появятся при работе firewall</p>
          </div>
        )}
        <AnimatePresence mode="popLayout">
          {activities.map((item, i) => {
            const config = actionConfig[item.action]
            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
                className="flex items-start gap-2.5 p-2.5 rounded-xl hover:bg-dark-700/30 transition-colors group"
              >
                <div className={`p-1.5 rounded-lg ${config.bg} ${config.color} flex-shrink-0 mt-0.5`}>
                  {config.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-300 font-mono">{item.source}</span>
                    <span className="text-[10px] text-gray-600">{item.time}</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5 truncate">{item.message}</p>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
