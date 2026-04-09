import { api } from './client'

export interface UpdateCheck {
  has_update: boolean
  current_version: string
  latest_version: string
  changelog: string
  error?: string | null
}

export interface UpdateProgress {
  status: string
  current_version: string
  latest_version: string
  changelog: string
  progress_percent: number
  message: string
  error: string
  started_at: string | null
  completed_at: string | null
  can_rollback: boolean
}

export interface BackupInfo {
  name: string
  commit: string
  created_at: string
}

export const updaterApi = {
  check: () => api.get<UpdateCheck>('/updater/check'),
  apply: () => api.post<{ success: boolean; version?: string; error?: string }>('/updater/apply'),
  rollback: () => api.post<{ success: boolean; version?: string; error?: string }>('/updater/rollback'),
  progress: () => api.get<UpdateProgress>('/updater/progress'),
  backups: () => api.get<BackupInfo[]>('/updater/backups'),
}
