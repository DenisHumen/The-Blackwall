import { useState, useEffect, useCallback, useRef } from 'react'
import { updaterApi } from '../api/updater'
import type { UpdateCheck, UpdateProgress, BackupInfo } from '../api/updater'

const ACTIVE_STATUSES = ['checking', 'downloading', 'backing_up', 'applying', 'rebuilding', 'rolling_back']

export default function Update() {
  const [check, setCheck] = useState<UpdateCheck | null>(null)
  const [progress, setProgress] = useState<UpdateProgress | null>(null)
  const [backups, setBackups] = useState<BackupInfo[]>([])
  const [error, setError] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchProgress = useCallback(async () => {
    try {
      const p = await updaterApi.progress()
      setProgress(p)

      // Stop polling when done
      if (!ACTIVE_STATUSES.includes(p.status) && pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    } catch {
      // ignore polling errors
    }
  }, [])

  const fetchBackups = useCallback(async () => {
    try {
      const b = await updaterApi.backups()
      setBackups(b)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchProgress()
    fetchBackups()
  }, [fetchProgress, fetchBackups])

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(fetchProgress, 1500)
  }, [fetchProgress])

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const handleCheck = async () => {
    setChecking(true)
    setError(null)
    try {
      const result = await updaterApi.check()
      setCheck(result)
      if (result.error) setError(result.error)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка проверки')
    } finally {
      setChecking(false)
    }
  }

  const handleApply = async () => {
    if (!confirm('Применить обновление? Будет создана резервная копия.')) return
    setError(null)
    startPolling()
    try {
      const result = await updaterApi.apply()
      if (!result.success) setError(result.error || 'Ошибка обновления')
      fetchProgress()
      fetchBackups()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
      fetchProgress()
    }
  }

  const handleRollback = async () => {
    if (!confirm('Откатить к предыдущей версии?')) return
    setError(null)
    startPolling()
    try {
      const result = await updaterApi.rollback()
      if (!result.success) setError(result.error || 'Ошибка отката')
      fetchProgress()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
      fetchProgress()
    }
  }

  const isActive = progress && ACTIVE_STATUSES.includes(progress.status)
  const statusLabel = getStatusLabel(progress?.status || 'idle')
  const statusColor = getStatusColor(progress?.status || 'idle')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-white">Управление версиями</h2>
          <p className="text-xs text-gray-500 mt-0.5">Проверка и установка обновлений системы</p>
        </div>
        <button onClick={handleCheck} disabled={checking || !!isActive} className="btn-primary text-sm">
          {checking ? 'Проверка...' : 'Проверить обновления'}
        </button>
      </div>

      {error && (
        <div className="bg-danger/8 border border-danger/15 rounded-xl p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Current Version & Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Текущая версия</h3>
          <div className="text-2xl font-bold font-mono text-white">
            {progress?.current_version || '...'}
          </div>
        </div>
        <div className="card">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Статус</h3>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${statusColor}`} />
            <span className="text-lg font-semibold">{statusLabel}</span>
          </div>
          {progress?.message && (
            <p className="text-sm text-gray-400 mt-1">{progress.message}</p>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      {isActive && progress && (
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold">Прогресс обновления</h3>
            <span className="text-sm text-gray-400">{progress.progress_percent}%</span>
          </div>
          <div className="h-2.5 bg-dark-700/50 rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all duration-500 shadow-sm shadow-accent/30"
              style={{ width: `${progress.progress_percent}%` }}
            />
          </div>
          <p className="text-sm text-gray-400 mt-2">{progress.message}</p>
        </div>
      )}

      {/* Update Available */}
      {check?.has_update && !isActive && (
        <div className="card border-accent/20">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="font-semibold text-accent text-base">Доступно обновление</h3>
              <p className="text-sm text-gray-400 mt-1">
                {check.current_version} → <span className="text-accent font-mono">{check.latest_version}</span>
              </p>
            </div>
            <button onClick={handleApply} className="btn-primary">
              Обновить
            </button>
          </div>
          {check.changelog && (
            <div className="mt-3 pt-3 border-t border-dark-600/30">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Изменения:</h4>
              <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap bg-dark-900/80 rounded-xl p-3 max-h-48 overflow-y-auto border border-dark-600/30">
                {check.changelog}
              </pre>
            </div>
          )}
        </div>
      )}

      {check && !check.has_update && !isActive && (
        <div className="card border-success/15 text-center py-6">
          <span className="text-success text-base font-semibold">Система обновлена</span>
        </div>
      )}

      {/* Rollback / Completed */}
      {progress?.status === 'completed' && (
        <div className="card border-success/15">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2.5 h-2.5 rounded-full bg-success" />
            <h3 className="font-semibold text-success">Обновление завершено</h3>
          </div>
          <p className="text-sm text-gray-400">
            Версия: <span className="font-mono">{progress.current_version}</span>
            {progress.completed_at && (
              <> — {new Date(progress.completed_at).toLocaleString()}</>
            )}
          </p>
          <p className="text-xs text-gray-500 mt-2">
            Перезагрузите сервис для применения обновлений бэкенда.
          </p>
        </div>
      )}

      {progress?.status === 'failed' && (
        <div className="card border-danger/15">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-danger">Ошибка обновления</h3>
              <p className="text-sm text-gray-400 mt-1">{progress.error}</p>
            </div>
            {progress.can_rollback && (
              <button onClick={handleRollback} className="btn-danger text-sm">
                Откатить
              </button>
            )}
          </div>
        </div>
      )}

      {/* Backups */}
      {backups.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">Резервные копии</h3>
            {!isActive && (
              <button onClick={handleRollback} className="btn-ghost text-xs">
                Откатить к последней
              </button>
            )}
          </div>
          <div className="space-y-2">
            {backups.map(b => (
              <div key={b.name} className="flex items-center justify-between bg-dark-900/60 rounded-xl px-4 py-2.5 border border-dark-600/20">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm text-gray-300">{b.commit.slice(0, 8)}</span>
                  <span className="text-xs text-gray-500">{b.name}</span>
                </div>
                <span className="text-xs text-gray-500">
                  {new Date(b.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    idle: 'Готов',
    checking: 'Проверка...',
    available: 'Доступно обновление',
    downloading: 'Загрузка...',
    backing_up: 'Резервное копирование...',
    applying: 'Применение...',
    rebuilding: 'Пересборка...',
    completed: 'Завершено',
    rolling_back: 'Откат...',
    failed: 'Ошибка',
  }
  return labels[status] || status
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    idle: 'bg-gray-500',
    checking: 'bg-accent animate-pulse',
    available: 'bg-accent',
    downloading: 'bg-accent animate-pulse',
    backing_up: 'bg-warning animate-pulse',
    applying: 'bg-accent animate-pulse',
    rebuilding: 'bg-accent animate-pulse',
    completed: 'bg-success',
    rolling_back: 'bg-warning animate-pulse',
    failed: 'bg-danger',
  }
  return colors[status] || 'bg-gray-500'
}
