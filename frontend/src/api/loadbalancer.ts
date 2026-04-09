import { api } from './client'
import type { LoadBalancerConfig, LoadBalancerCreate, LoadBalancerUpdate, GatewayCreate, Gateway } from '../types'

export const loadbalancerApi = {
  list: () => api.get<LoadBalancerConfig[]>('/loadbalancer'),
  get: (id: number) => api.get<LoadBalancerConfig>(`/loadbalancer/${id}`),
  create: (data: LoadBalancerCreate) => api.post<LoadBalancerConfig>('/loadbalancer', data),
  update: (id: number, data: LoadBalancerUpdate) => api.patch<LoadBalancerConfig>(`/loadbalancer/${id}`, data),
  delete: (id: number) => api.delete<void>(`/loadbalancer/${id}`),
  addGateway: (lbId: number, data: GatewayCreate) => api.post<Gateway>(`/loadbalancer/${lbId}/gateways`, data),
  removeGateway: (lbId: number, gwId: number) => api.delete<void>(`/loadbalancer/${lbId}/gateways/${gwId}`),
  healthCheck: (id: number) => api.post<Gateway[]>(`/loadbalancer/${id}/health-check`),
}
