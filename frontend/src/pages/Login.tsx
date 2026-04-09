import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'

export default function Login() {
  const { login, setup, error, clearError, loading } = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isSetup, setIsSetup] = useState(false)
  const [checkingSetup, setCheckingSetup] = useState(true)

  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then(r => {
        if (r.status === 401) {
          return fetch('/api/auth/setup-check').then(r2 => r2.json()).catch(() => ({ needs_setup: false }))
        }
        return { needs_setup: false }
      })
      .then((data: any) => {
        setIsSetup(data?.needs_setup === true)
        setCheckingSetup(false)
      })
      .catch(() => setCheckingSetup(false))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    try {
      if (isSetup) {
        await setup(username, password)
      } else {
        await login(username, password)
      }
    } catch {
      // error is set in store
    }
  }

  if (checkingSetup) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-950">
        <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-950 px-4">
      {/* Subtle background glow */}
      <div className="fixed inset-0 bg-gradient-to-br from-accent/5 via-transparent to-transparent pointer-events-none" />

      <div className="w-full max-w-sm relative z-10">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent/10 border border-accent/20 mb-5 shadow-lg shadow-accent/10">
            <svg className="w-7 h-7 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">The Blackwall</h1>
          <p className="text-gray-500 mt-1 text-sm">
            {isSetup ? 'Первоначальная настройка' : 'Вход в систему'}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {isSetup && (
            <div className="bg-accent/8 border border-accent/15 rounded-xl p-3.5 text-sm text-accent">
              Создайте учётную запись администратора для начала работы
            </div>
          )}

          {error && (
            <div className="bg-danger/8 border border-danger/15 rounded-xl p-3.5 text-sm text-red-400">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
              Имя пользователя
            </label>
            <input
              type="text"
              className="input"
              placeholder="admin"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoFocus
              autoComplete="username"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
              Пароль
            </label>
            <input
              type="password"
              className="input"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !username || !password}
            className="btn-primary w-full py-3 text-sm"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {isSetup ? 'Создание...' : 'Вход...'}
              </span>
            ) : (
              isSetup ? 'Создать и войти' : 'Войти'
            )}
          </button>
        </form>

        <p className="text-center text-[11px] text-gray-700 mt-8">
          The Blackwall • Firewall Management v0.1.0
        </p>
      </div>
    </div>
  )
}
