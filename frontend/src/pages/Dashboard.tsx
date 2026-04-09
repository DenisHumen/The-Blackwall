import { useState, useEffect, useCallback, useRef } from 'react'
import { metricsApi, type TrafficRange } from '../api/metrics'
import type { SystemMetrics, TrafficPoint } from '../types'
import TrafficChart from '../components/TrafficChart'
import MetricsCard from '../components/MetricsCard'

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
  const rangeRef = useRef(trafficRange)
  rangeRef.current = trafficRange

  const fetchMetrics = useCallback(async () => {
    try {
      const m = await metricsApi.current()
      setMetrics(m)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки данных')
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
      {error && (
        <div className="bg-danger/10 border border-danger/20 rounded-xl p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Metrics Cards — UniFi style compact row */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricsCard
          title="CPU"
          value={metrics ? `${metrics.cpu_percent.toFixed(1)}%` : '—'}
          subtitle={metrics ? `Load: ${metrics.load_avg_1.toFixed(2)}` : ''}
          percent={metrics?.cpu_percent}
          icon="cpu"
        />
        <MetricsCard
          title="Память"
          value={metrics ? `${metrics.memory_percent.toFixed(1)}%` : '—'}
          subtitle={metrics ? `${(metrics.memory_used_mb / 1024).toFixed(1)} / ${(metrics.memory_total_mb / 1024).toFixed(1)} GB` : ''}
          percent={metrics?.memory_percent}
          icon="memory"
        />
        <MetricsCard
          title="Сеть ↓"
          value={metrics ? formatBytes(metrics.network_rx_rate) + '/s' : '—'}
          subtitle={metrics ? `Всего: ${formatBytes(metrics.network_rx_bytes)}` : ''}
          icon="download"
        />
        <MetricsCard
          title="Сеть ↑"
          value={metrics ? formatBytes(metrics.network_tx_rate) + '/s' : '—'}
          subtitle={metrics ? `Всего: ${formatBytes(metrics.network_tx_bytes)}` : ''}
          icon="upload"
        />
      </div>

      {/* Traffic Chart — UniFi main area */}
      <div className="card">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-base font-semibold text-white">Активность сети</h2>
            <p className="text-xs text-gray-500 mt-0.5">Входящий и исходящий трафик</p>
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
      </div>

      {/* System Info Row */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Disk */}
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Диск</h3>
              <span className="text-xs text-gray-500">
                {metrics.disk_used_gb.toFixed(1)} / {metrics.disk_total_gb.toFixed(1)} GB
              </span>
            </div>
            <div className="text-2xl font-bold text-white mb-3">{metrics.disk_percent.toFixed(1)}%</div>
            <div className="h-1.5 bg-dark-700/50 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ${metrics.disk_percent > 90 ? 'bg-danger' : metrics.disk_percent > 70 ? 'bg-warning' : 'bg-accent'}`}
                style={{ width: `${metrics.disk_percent}%` }}
              />
            </div>
          </div>

          {/* Load Average */}
          <div className="card">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Load Average</h3>
            <div className="flex items-end gap-6">
              <div>
                <div className="text-2xl font-bold text-white">{metrics.load_avg_1.toFixed(2)}</div>
                <div className="text-[10px] text-gray-500 mt-0.5">1 мин</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-gray-300">{metrics.load_avg_5.toFixed(2)}</div>
                <div className="text-[10px] text-gray-500 mt-0.5">5 мин</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-gray-400">{metrics.load_avg_15.toFixed(2)}</div>
                <div className="text-[10px] text-gray-500 mt-0.5">15 мин</div>
              </div>
            </div>
          </div>

          {/* Uptime */}
          <div className="card">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Uptime</h3>
            <div className="text-2xl font-bold text-white">{formatUptime(metrics.uptime_seconds)}</div>
            <div className="text-xs text-gray-500 mt-1">
              {Math.floor(metrics.uptime_seconds / 86400)} дней непрерывной работы
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(1024))
  const idx = Math.min(i, units.length - 1)
  return `${(bytes / Math.pow(1024, idx)).toFixed(idx > 1 ? 2 : 0)} ${units[idx]}`
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}д ${h}ч`
  if (h > 0) return `${h}ч ${m}м`
  return `${m}м`
}
