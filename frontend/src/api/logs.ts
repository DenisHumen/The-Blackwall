import { api } from './client'

export interface LogEntry {
  id: number
  timestamp: string
  action: string
  severity: string
  source_ip: string
  dest_ip: string
  source_port: number | null
  dest_port: number | null
  protocol: string
  message: string
  rule_id: number | null
  interface: string
  country_code: string
}

export interface RecentActivityItem {
  id: string
  time: string
  action: 'block' | 'allow' | 'alert' | 'system'
  source: string
  message: string
}

export const logsApi = {
  recent: (limit = 8) => api.get<RecentActivityItem[]>(`/api/logs/recent?limit=${limit}`),
  list: (params?: { action?: string; source_ip?: string; skip?: number; limit?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.action) searchParams.set('action', params.action)
    if (params?.source_ip) searchParams.set('source_ip', params.source_ip)
    if (params?.skip) searchParams.set('skip', String(params.skip))
    if (params?.limit) searchParams.set('limit', String(params.limit))
    const qs = searchParams.toString()
    return api.get<LogEntry[]>(`/api/logs${qs ? `?${qs}` : ''}`)
  },
}