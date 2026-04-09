import { useState, useEffect, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import { metricsApi, type TrafficRange } from '../api/metrics'
import type { SystemMetrics, TrafficPoint } from '../types'
import TrafficChart from '../components/TrafficChart'
import SystemHealthBanner from '../components/dashboard/SystemHealthBanner'
import GaugeCard from '../components/dashboard/GaugeCard'
import NetworkThroughput from '../components/dashboard/NetworkThroughput'
import FirewallStatus from '../components/dashboard/FirewallStatus'
import RecentActivity from '../components/dashboard/RecentActivity'
import SystemInfoGrid from '../components/dashboard/SystemInfoGrid'
import QuickActions from '../components/dashboard/QuickActions'

const RANGE_OPTIONS: { value: TrafficRange; label: string }[] = [
  { value: '1h', label: '1ч' },
  { value: '24h', label: '24ч' },
  { value: '7d', label: '7д' },
  { value: '30d', label: '30д' },
]

export default function Dashboard() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [traffic, setTraffic] = useState<TrafficPoint[]>([])
  const [trafficRange, setTrafficRange] = useState<TrafficRange>('1h')
  const [error, setError] = useState<string | null>(null)
  const [isOnline, setIsOnline] = useState(true)
  const rangeRef = useRef(trafficRange)
  rangeRef.current = trafficRange

  const fetchMetrics = useCallback(async () => {
    try {
      const m = await metricsApi.current()
      setMetrics(m)
      setError(null)
      setIsOnline(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки данных')
      setIsOnline(false)
    }
  }, [])

  const fetchTraffic = useCallback(async () => {
    try {
      const t = await metricsApi.traffic(rangeRef.current)
      setTraffic(t)
    } catch {
      // traffic fetch failure is non-critical
    }
  }, [])

  useEffect(() => {
    fetchMetrics()
    fetchTraffic()
    const metricsInterval = setInterval(fetchMetrics, 3000)
    const trafficInterval = setInterval(fetchTraffic, 10000)
    return () => { clearInterval(metricsInterval); clearInterval(trafficInterval) }
  }, [fetchMetrics, fetchTraffic])

  useEffect(() => {
    fetchTraffic()
  }, [trafficRange, fetchTraffic])

  return (
    <div className="space-y-6">
      {/* Error banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-danger/10 border border-danger/20 rounded-xl p-3 text-sm text-red-400 flex items-center gap-2"
        >
          <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          {error}
        </motion.div>
      )}

      {/* System Health Banner */}
      <SystemHealthBanner metrics={metrics} isOnline={isOnline} />

      {/* Gauge Cards Row — CPU + Memory + Network Throughput + Firewall */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <GaugeCard
          title="CPU"
          value={metrics ? `${metrics.cpu_percent.toFixed(1)}%` : '—'}
          subtitle={metrics ? `Load: ${metrics.load_avg_1.toFixed(2)}` : 'Загрузка...'}
          percent={metrics?.cpu_percent ?? 0}
          delay={0.1}
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25z" />
            </svg>
          }
        />
        <GaugeCard
          title="Память"
          value={metrics ? `${metrics.memory_percent.toFixed(1)}%` : '—'}
          subtitle={metrics ? `${(metrics.memory_used_mb / 1024).toFixed(1)} / ${(metrics.memory_total_mb / 1024).toFixed(1)} GB` : 'Загрузка...'}
          percent={metrics?.memory_percent ?? 0}
          delay={0.15}
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zm0 9.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zm0 9.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25a2.25 2.25 0 01-2.25-2.25v-2.25z" />
            </svg>
          }
        />

        {/* Network Throughput Card */}
        <NetworkThroughput
          rxRate={metrics?.network_rx_rate ?? 0}
          txRate={metrics?.network_tx_rate ?? 0}
          rxTotal={metrics?.network_rx_bytes ?? 0}
          txTotal={metrics?.network_tx_bytes ?? 0}
        />

        {/* Firewall Status */}
        <FirewallStatus />
      </div>

      {/* Traffic Chart + Recent Activity — side by side */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Traffic Chart — 2/3 width */}
        <motion.div
          className="xl:col-span-2 card-hover"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                Активность сети
                <motion.span
                  className="inline-block w-2 h-2 rounded-full bg-accent"
                  animate={{ scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">Входящий и исходящий трафик в реальном времени</p>
            </div>
            <div className="flex bg-dark-900/80 rounded-lg p-0.5 border border-dark-600/30">
              {RANGE_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setTrafficRange(opt.value)}
                  className={`px-3.5 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
                    trafficRange === opt.value
                      ? 'bg-accent text-white shadow-sm shadow-accent/30'
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <TrafficChart data={traffic} />
        </motion.div>

        {/* Recent Activity — 1/3 width */}
        <RecentActivity />
      </div>

      {/* System Info Row */}
      {metrics && <SystemInfoGrid metrics={metrics} />}

      {/* Quick Actions */}
      <QuickActions />
    </div>
  )
}
