import { create } from 'zustand'
import type { User } from '../types'
import { authApi } from '../api/auth'

interface AuthState {
  user: User | null
  loading: boolean
  error: string | null
  checkAuth: () => Promise<void>
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  setup: (username: string, password: string) => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,
  error: null,

  checkAuth: async () => {
    try {
      const user = await authApi.me()
      set({ user, loading: false, error: null })
    } catch {
      set({ user: null, loading: false })
    }
  },

  login: async (username, password) => {
    set({ loading: true, error: null })
    try {
      const res = await authApi.login(username, password)
      set({ user: res.user, loading: false })
    } catch (e) {
      set({ loading: false, error: e instanceof Error ? e.message : 'Ошибка входа' })
      throw e
    }
  },

  logout: async () => {
    try { await authApi.logout() } catch { /* ignore */ }
    set({ user: null })
  },

  setup: async (username, password) => {
    set({ loading: true, error: null })
    try {
      await authApi.setup(username, password)
      // Auto-login after setup
      const res = await authApi.login(username, password)
      set({ user: res.user, loading: false })
    } catch (e) {
      set({ loading: false, error: e instanceof Error ? e.message : 'Ошибка настройки' })
      throw e
    }
  },

  clearError: () => set({ error: null }),
}))
