export interface User {
  id: number
  username: string
  role: 'root' | 'admin' | 'operator' | 'viewer'
  is_active: boolean
  created_at: string
  last_login: string | null
}

export interface SystemMetrics {
  cpu_percent: number
  memory_percent: number
  memory_used_mb: number
  memory_total_mb: number
  disk_percent: number
  disk_used_gb: number
  disk_total_gb: number
  network_rx_bytes: number
  network_tx_bytes: number
  network_rx_rate: number  // bytes/sec
  network_tx_rate: number  // bytes/sec
  uptime_seconds: number
  load_avg_1: number
  load_avg_5: number
  load_avg_15: number
  timestamp: string
}

export interface TrafficPoint {
  timestamp: string
  rx_rate: number  // bytes/sec
  tx_rate: number  // bytes/sec
}

export interface LoadBalancerConfig {
  id: number
  name: string
  mode: 'round_robin' | 'failover'
  is_active: boolean
  use_virtual_interface: boolean
  virtual_ip: string
  virtual_interface: string
  check_interval: number
  check_target: string
  check_timeout: number
  check_failures: number
  active_gateway_id: number | null
  last_switch: string | null
  switch_count: number
  created_at: string
  updated_at: string
  gateways: Gateway[]
}

export interface Gateway {
  id: number
  lb_config_id: number
  address: string
  interface_name: string
  weight: number
  priority: number
  is_healthy: boolean
  is_primary: boolean
  last_check: string | null
  latency_ms: number | null
  consecutive_failures: number
  total_downtime_sec: number
}

export interface GatewayCreate {
  address: string
  interface_name: string
  weight?: number
  priority?: number
  is_primary?: boolean
}

export interface LoadBalancerCreate {
  name: string
  mode: 'round_robin' | 'failover'
  use_virtual_interface: boolean
  virtual_ip: string
  virtual_interface: string
  check_interval: number
  check_target: string
  check_timeout: number
  check_failures: number
  gateways: GatewayCreate[]
}

export interface LoadBalancerUpdate {
  name?: string
  mode?: 'round_robin' | 'failover'
  is_active?: boolean
  use_virtual_interface?: boolean
  virtual_ip?: string
  virtual_interface?: string
  check_interval?: number
  check_target?: string
  check_timeout?: number
  check_failures?: number
}

export interface LoadBalancerStatus {
  id: number
  name: string
  mode: string
  is_active: boolean
  use_virtual_interface: boolean
  virtual_interface: string
  virtual_ip: string
  interface_exists: boolean
  active_gateway: Gateway | null
  gateways: Gateway[]
  switch_count: number
  last_switch: string | null
}
