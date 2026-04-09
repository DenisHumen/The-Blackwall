import { api } from './client'
import type { User } from '../types'

export const authApi = {
  setup: (username: string, password: string) =>
    api.post<User>('/auth/setup', { username, password }),

  login: (username: string, password: string) =>
    api.post<{ message: string; user: User }>('/auth/login', { username, password }),

  logout: () => api.post<{ message: string }>('/auth/logout'),

  me: () => api.get<User>('/auth/me'),
}
