import { api } from './client'

export interface FirewallRule {
  id: number
  name: string
  description: string
  source_ip: string
  dest_ip: string
  source_port: string
  dest_port: string
  protocol: string
  interface: string
  direction: string
  action: string
  rate_limit: string
  priority: number
  is_active: boolean
  is_system: boolean
  created_at: string
  updated_at: string
  created_by: string
}

export interface RuleStats {
  totalRules: number
  activeRules: number
  blockedToday: number
  threatsDetected: number
  lastThreat: string | null
}

export interface RuleCreate {
  name: string
  description?: string
  source_ip?: string
  dest_ip?: string
  source_port?: string
  dest_port?: string
  protocol?: string
  interface?: string
  direction?: string
  action?: string
  rate_limit?: string
  priority?: number
  is_active?: boolean
}

export const rulesApi = {
  stats: () => api.get<RuleStats>('/api/rules/stats'),
  list: () => api.get<FirewallRule[]>('/api/rules'),
  get: (id: number) => api.get<FirewallRule>(`/api/rules/${id}`),
  create: (data: RuleCreate) => api.post<FirewallRule>('/api/rules', data),
  update: (id: number, data: Partial<RuleCreate>) => api.patch<FirewallRule>(`/api/rules/${id}`, data),
  delete: (id: number) => api.delete(`/api/rules/${id}`),
}