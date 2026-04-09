import { api } from './client'
import type { SystemMetrics, TrafficPoint } from '../types'

export type TrafficRange = '1h' | '24h' | '7d' | '30d'

export const metricsApi = {
  current: () => api.get<SystemMetrics>('/metrics/current'),
  traffic: (range: TrafficRange = '1h') =>
    api.get<TrafficPoint[]>(`/metrics/traffic?range=${range}`),
}
