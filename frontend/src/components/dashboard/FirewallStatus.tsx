import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'

interface FirewallStats {
  totalRules: number
  activeRules: number
  blockedToday: number
  threatsDetected: number
  lastThreat: string | null
}

export default function FirewallStatus() {
  const [stats, setStats] = useState<FirewallStats>({
    totalRules: 0,
    activeRules: 0,
    blockedToday: 0,
    threatsDetected: 0,
    lastThreat: null,
  })

  useEffect(() => {
    // Try to load real data, fallback to demo
    fetchFirewallStats()
    const interval = setInterval(fetchFirewallStats, 15000)
    return () => clearInterval(interval)
  }, [])

  async function fetchFirewallStats() {
    try {
      const res = await fetch('/api/rules/stats', { credentials: 'include' })
      if (res.ok) {
        setStats(await res.json())
        return
      }
    } catch { /* API not available yet */ }
  }

  const items = [
    {
      label: 'Активные правила',
      value: `${stats.activeRules}/${stats.totalRules}`,
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
        </svg>
      ),
      color: 'text-accent',
      bg: 'bg-accent/10',
    },
    {
      label: 'Заблокировано сегодня',
      value: stats.blockedToday.toLocaleString('ru-RU'),
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
        </svg>
      ),
      color: 'text-warning',
      bg: 'bg-warning/10',
    },
    {
      label: 'Угрозы',
      value: stats.threatsDetected.toString(),
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
      ),
      color: stats.threatsDetected > 0 ? 'text-danger' : 'text-success',
      bg: stats.threatsDetected > 0 ? 'bg-danger/10' : 'bg-success/10',
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="card-hover"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Firewall</h3>
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-success/10 text-success text-[10px] font-medium">
          <span className="w-1 h-1 rounded-full bg-success" />
          Active
        </span>
      </div>

      <div className="space-y-3">
        {items.map((item, i) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 + i * 0.1 }}
            className="flex items-center justify-between"
          >
            <div className="flex items-center gap-2.5">
              <div className={`p-1.5 rounded-lg ${item.bg} ${item.color}`}>
                {item.icon}
              </div>
              <span className="text-xs text-gray-400">{item.label}</span>
            </div>
            <span className={`text-sm font-semibold ${item.color}`}>
              {item.value}
            </span>
          </motion.div>
        ))}
      </div>

      {stats.lastThreat && (
        <div className="mt-3 pt-3 border-t border-dark-700/50">
          <div className="flex items-center gap-2 text-[10px] text-gray-600">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Последняя угроза: {stats.lastThreat}
          </div>
        </div>
      )}
    </motion.div>
  )
}
