import { useState, useEffect, useCallback } from 'react'
import { loadbalancerApi } from '../api/loadbalancer'
import type { LoadBalancerConfig, LoadBalancerCreate, Gateway } from '../types'

export default function LoadBalancer() {
  const [configs, setConfigs] = useState<LoadBalancerConfig[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchConfigs = useCallback(async () => {
    try {
      const data = await loadbalancerApi.list()
      setConfigs(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConfigs()
    const interval = setInterval(fetchConfigs, 5000)
    return () => clearInterval(interval)
  }, [fetchConfigs])

  const handleCreate = async (data: LoadBalancerCreate) => {
    try {
      await loadbalancerApi.create(data)
      setShowCreate(false)
      fetchConfigs()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка создания')
    }
  }

  const handleToggle = async (cfg: LoadBalancerConfig) => {
    try {
      await loadbalancerApi.update(cfg.id, { is_active: !cfg.is_active })
      fetchConfigs()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка обновления')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить конфигурацию балансировщика?')) return
    try {
      await loadbalancerApi.delete(id)
      fetchConfigs()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка удаления')
    }
  }

  const handleHealthCheck = async (id: number) => {
    try {
      await loadbalancerApi.healthCheck(id)
      fetchConfigs()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка проверки')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Load Balancer</h1>
          <p className="text-xs text-gray-500 mt-1">
            Управление балансировкой трафика между провайдерами
          </p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary text-sm flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Создать
        </button>
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/20 rounded-lg p-3 text-sm text-red-400 flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">✕</button>
        </div>
      )}

      {/* Create Form */}
      {showCreate && <CreateForm onSubmit={handleCreate} onCancel={() => setShowCreate(false)} />}

      {/* Configs list */}
      {loading ? (
        <div className="text-center text-gray-400 py-12">
          <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          Загрузка...
        </div>
      ) : configs.length === 0 && !showCreate ? (
        <EmptyState onAction={() => setShowCreate(true)} />
      ) : (
        <div className="space-y-4">
          {configs.map(cfg => (
            <ConfigCard
              key={cfg.id}
              config={cfg}
              onToggle={() => handleToggle(cfg)}
              onDelete={() => handleDelete(cfg.id)}
              onHealthCheck={() => handleHealthCheck(cfg.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

/* ─── Empty state ─────────────────────────────────────────────────────── */

function EmptyState({ onAction }: { onAction: () => void }) {
  return (
    <div className="card text-center py-16">
      <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-accent/10 flex items-center justify-center">
        <svg className="w-8 h-8 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold mb-2">Нет конфигураций</h3>
      <p className="text-sm text-gray-400 mb-6 max-w-md mx-auto">
        Создайте конфигурацию балансировщика для распределения трафика
        между несколькими интернет-провайдерами.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-xl mx-auto mb-6">
        <div className="bg-dark-900/60 rounded-2xl p-4 text-left border border-dark-600/30">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-accent" />
            <span className="font-medium text-sm">Round Robin</span>
          </div>
          <p className="text-xs text-gray-500">
            Равномерное распределение трафика между провайдерами с учётом весов
          </p>
        </div>
        <div className="bg-dark-900/60 rounded-2xl p-4 text-left border border-dark-600/30">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-warning" />
            <span className="font-medium text-sm">Failover</span>
          </div>
          <p className="text-xs text-gray-500">
            Автоматическое переключение на резервный канал при сбое основного
          </p>
        </div>
      </div>
      <button onClick={onAction} className="btn-primary text-sm">
        Создать конфигурацию
      </button>
    </div>
  )
}

/* ─── Config card ─────────────────────────────────────────────────────── */

function ConfigCard({
  config: cfg,
  onToggle,
  onDelete,
  onHealthCheck,
}: {
  config: LoadBalancerConfig
  onToggle: () => void
  onDelete: () => void
  onHealthCheck: () => void
}) {
  const healthyCount = cfg.gateways.filter(g => g.is_healthy).length
  const totalCount = cfg.gateways.length
  const allHealthy = healthyCount === totalCount

  return (
    <div className={`card border ${cfg.is_active ? (allHealthy ? 'border-success/30' : 'border-warning/30') : 'border-dark-700'}`}>
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
            cfg.is_active ? 'bg-success/10' : 'bg-dark-800'
          }`}>
            <svg className={`w-5 h-5 ${cfg.is_active ? 'text-success' : 'text-gray-500'}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-base">{cfg.name}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                cfg.mode === 'round_robin'
                  ? 'bg-accent/15 text-accent-light'
                  : 'bg-warning/15 text-amber-400'
              }`}>
                {cfg.mode === 'round_robin' ? 'Round Robin' : 'Failover'}
              </span>
              {cfg.use_virtual_interface && cfg.virtual_ip && (
                <span className="text-xs text-gray-500">VIP: {cfg.virtual_ip}</span>
              )}
              {!cfg.use_virtual_interface && (
                <span className="text-xs text-gray-500">Системные интерфейсы</span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onHealthCheck}
            className="px-3 py-1.5 text-xs rounded-lg bg-dark-800 hover:bg-dark-700 text-gray-300 transition-colors flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            Проверить
          </button>
          <button onClick={onToggle}
            className={`px-3 py-1.5 text-xs rounded-lg transition-colors flex items-center gap-1.5 ${
              cfg.is_active
                ? 'bg-warning/15 text-amber-400 hover:bg-warning/25'
                : 'bg-success/15 text-green-400 hover:bg-success/25'
            }`}>
            {cfg.is_active ? (
              <><svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25v13.5m-7.5-13.5v13.5" /></svg>Остановить</>
            ) : (
              <><svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z" /></svg>Запустить</>
            )}
          </button>
          <button onClick={onDelete}
            className="px-3 py-1.5 text-xs rounded-lg bg-danger/10 text-red-400 hover:bg-danger/20 transition-colors">
            Удалить
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-dark-900/60 rounded-xl px-3 py-2">
          <div className="text-xs text-gray-500 mb-0.5">Шлюзы</div>
          <div className="text-sm font-medium">
            <span className={allHealthy ? 'text-success' : 'text-warning'}>{healthyCount}</span>
            <span className="text-gray-500"> / {totalCount} онлайн</span>
          </div>
        </div>
        <div className="bg-dark-900/60 rounded-xl px-3 py-2">
          <div className="text-xs text-gray-500 mb-0.5">Переключения</div>
          <div className="text-sm font-medium">{cfg.switch_count}</div>
        </div>
        <div className="bg-dark-900/60 rounded-xl px-3 py-2">
          <div className="text-xs text-gray-500 mb-0.5">Проверка</div>
          <div className="text-sm font-medium text-gray-300">
            каждые {cfg.check_interval}с → {cfg.check_target}
          </div>
        </div>
      </div>

      {/* Gateway table */}
      <div className="overflow-hidden rounded-xl border border-dark-600/30">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-dark-900/60 text-gray-500 text-xs">
              <th className="text-left px-4 py-2 font-medium">Статус</th>
              <th className="text-left px-4 py-2 font-medium">Шлюз (IP)</th>
              <th className="text-left px-4 py-2 font-medium">Интерфейс</th>
              {cfg.mode === 'round_robin' && <th className="text-left px-4 py-2 font-medium">Вес</th>}
              {cfg.mode === 'failover' && <th className="text-left px-4 py-2 font-medium">Роль</th>}
              <th className="text-left px-4 py-2 font-medium">Задержка</th>
              <th className="text-left px-4 py-2 font-medium">Сбои</th>
            </tr>
          </thead>
          <tbody>
            {cfg.gateways.map(gw => (
              <GatewayRow key={gw.id} gw={gw} mode={cfg.mode} activeGatewayId={cfg.active_gateway_id} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ─── Gateway row ─────────────────────────────────────────────────────── */

function GatewayRow({ gw, mode, activeGatewayId }: { gw: Gateway; mode: string; activeGatewayId: number | null }) {
  const isActive = gw.id === activeGatewayId
  return (
    <tr className={`border-t border-dark-600/30 ${isActive ? 'bg-accent/5' : 'hover:bg-dark-900/30'}`}>
      <td className="px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${gw.is_healthy ? 'bg-success' : 'bg-danger'}`} />
          <span className={`text-xs ${gw.is_healthy ? 'text-success' : 'text-red-400'}`}>
            {gw.is_healthy ? 'Онлайн' : 'Недоступен'}
          </span>
        </div>
      </td>
      <td className="px-4 py-2.5">
        <span className="font-mono text-sm">{gw.address}</span>
        {isActive && (
          <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-md bg-accent/15 text-accent-light">активен</span>
        )}
      </td>
      <td className="px-4 py-2.5 text-gray-400">{gw.interface_name}</td>
      {mode === 'round_robin' && <td className="px-4 py-2.5 text-gray-300">{gw.weight}</td>}
      {mode === 'failover' && (
        <td className="px-4 py-2.5">
          {gw.is_primary
            ? <span className="text-xs px-2 py-0.5 rounded-full bg-accent/15 text-accent-light">Основной</span>
            : <span className="text-xs px-2 py-0.5 rounded-full bg-dark-600/50 text-gray-400">Резервный</span>}
        </td>
      )}
      <td className="px-4 py-2.5">
        {gw.latency_ms !== null ? (
          <span className={gw.latency_ms > 100 ? 'text-warning' : gw.latency_ms > 50 ? 'text-yellow-500' : 'text-success'}>
            {gw.latency_ms.toFixed(0)} мс
          </span>
        ) : <span className="text-gray-600">—</span>}
      </td>
      <td className="px-4 py-2.5">
        {gw.consecutive_failures > 0
          ? <span className="text-red-400">{gw.consecutive_failures}</span>
          : <span className="text-gray-600">0</span>}
      </td>
    </tr>
  )
}

/* ─── Create form ─────────────────────────────────────────────────────── */

function CreateForm({ onSubmit, onCancel }: { onSubmit: (data: LoadBalancerCreate) => void; onCancel: () => void }) {
  const [name, setName] = useState('')
  const [mode, setMode] = useState<'round_robin' | 'failover'>('round_robin')
  const [useVirtual, setUseVirtual] = useState(false)
  const [virtualIp, setVirtualIp] = useState('10.10.10.1/24')
  const [virtualInterface, setVirtualInterface] = useState('lb0')
  const [checkInterval, setCheckInterval] = useState(5)
  const [checkTarget, setCheckTarget] = useState('8.8.8.8')
  const [checkTimeout, setCheckTimeout] = useState(2.0)
  const [checkFailures, setCheckFailures] = useState(3)
  const [gateways, setGateways] = useState([
    { address: '', interface_name: '', weight: 1, priority: 1, is_primary: true },
    { address: '', interface_name: '', weight: 1, priority: 2, is_primary: false },
  ])

  const addGateway = () => {
    setGateways([...gateways, {
      address: '', interface_name: '', weight: 1, priority: gateways.length + 1, is_primary: false,
    }])
  }

  const removeGateway = (i: number) => {
    if (gateways.length <= 2) return
    setGateways(gateways.filter((_, idx) => idx !== i))
  }

  const updateGateway = (i: number, field: string, value: string | number | boolean) => {
    const updated = [...gateways]
    ;(updated[i] as any)[field] = value
    if (field === 'is_primary' && value === true) {
      updated.forEach((g, idx) => { if (idx !== i) g.is_primary = false })
    }
    setGateways(updated)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      name,
      mode,
      use_virtual_interface: useVirtual,
      virtual_ip: useVirtual ? virtualIp : '',
      virtual_interface: useVirtual ? virtualInterface : '',
      check_interval: checkInterval,
      check_target: checkTarget,
      check_timeout: checkTimeout,
      check_failures: checkFailures,
      gateways,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="card border-accent/15 space-y-5">
      <h3 className="text-base font-semibold">Новая конфигурация</h3>

      {/* Basic settings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">Название</label>
          <input className="input" value={name} onChange={e => setName(e.target.value)} required placeholder="Мой балансировщик" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">Режим работы</label>
          <select className="input" value={mode} onChange={e => setMode(e.target.value as any)}>
            <option value="round_robin">Round Robin — балансировка по весам</option>
            <option value="failover">Failover — основной + резервный</option>
          </select>
        </div>
      </div>

      {/* Virtual interface toggle */}
      <div className="bg-dark-900/60 rounded-xl p-4 border border-dark-600/30">
        <label className="flex items-center gap-3 cursor-pointer">
          <div className="relative">
            <input type="checkbox" checked={useVirtual} onChange={e => setUseVirtual(e.target.checked)} className="sr-only" />
            <div className={`w-10 h-5 rounded-full transition-colors ${useVirtual ? 'bg-accent' : 'bg-dark-600'}`}>
              <div className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-transform ${useVirtual ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </div>
          </div>
          <div>
            <div className="text-sm font-medium">Виртуальный интерфейс</div>
            <div className="text-xs text-gray-500">
              {useVirtual
                ? 'Будет создан dummy-интерфейс как шлюз для клиентов'
                : 'Используются системные интерфейсы Ubuntu напрямую (рекомендуется)'}
            </div>
          </div>
        </label>
        {useVirtual && (
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Virtual IP (CIDR)</label>
              <input className="input" value={virtualIp} onChange={e => setVirtualIp(e.target.value)} required placeholder="10.10.10.1/24" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Имя интерфейса</label>
              <input className="input" value={virtualInterface} onChange={e => setVirtualInterface(e.target.value)} required placeholder="lb0" />
            </div>
          </div>
        )}
      </div>

      {/* Health check settings */}
      <div>
        <h4 className="text-sm font-medium text-gray-300 mb-3">Проверка доступности</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Интервал (сек)</label>
            <input type="number" className="input" value={checkInterval} onChange={e => setCheckInterval(parseInt(e.target.value) || 5)} min={1} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Цель проверки</label>
            <input className="input" value={checkTarget} onChange={e => setCheckTarget(e.target.value)} placeholder="8.8.8.8" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Тайм-аут (сек)</label>
            <input type="number" className="input" value={checkTimeout} onChange={e => setCheckTimeout(parseFloat(e.target.value) || 2)} min={0.5} step={0.5} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Сбоев до переключения</label>
            <input type="number" className="input" value={checkFailures} onChange={e => setCheckFailures(parseInt(e.target.value) || 3)} min={1} />
          </div>
        </div>
      </div>

      {/* Gateways */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-medium text-gray-300">
            Шлюзы провайдеров
            <span className="text-xs text-gray-500 font-normal ml-2">мин. 2 шлюза</span>
          </h4>
          <button type="button" onClick={addGateway} className="text-xs text-accent hover:text-accent-light flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Добавить шлюз
          </button>
        </div>

        <div className="space-y-2">
          {gateways.map((gw, i) => (
            <div key={i} className="bg-dark-900/60 rounded-xl p-4 border border-dark-600/30 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-400">Шлюз #{i + 1}</span>
                {gateways.length > 2 && (
                  <button type="button" onClick={() => removeGateway(i)} className="text-xs text-gray-500 hover:text-danger flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Удалить
                  </button>
                )}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">IP адрес шлюза</label>
                  <input className="input text-sm" placeholder="192.168.1.1" value={gw.address}
                    onChange={e => updateGateway(i, 'address', e.target.value)} required />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Сетевой интерфейс</label>
                  <input className="input text-sm" placeholder="eth0, ens18..." value={gw.interface_name}
                    onChange={e => updateGateway(i, 'interface_name', e.target.value)} required />
                </div>
                {mode === 'round_robin' ? (
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Вес</label>
                    <input type="number" className="input text-sm" value={gw.weight}
                      onChange={e => updateGateway(i, 'weight', parseInt(e.target.value) || 1)} min={1} />
                    <p className="text-[10px] text-gray-600 mt-0.5">Больше = больше трафика</p>
                  </div>
                ) : (
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Роль</label>
                    <label className="flex items-center gap-2 mt-2 cursor-pointer">
                      <input type="radio" name="primary" checked={gw.is_primary}
                        onChange={() => updateGateway(i, 'is_primary', true)} className="accent-accent" />
                      <span className="text-sm">{gw.is_primary ? 'Основной' : 'Резервный'}</span>
                    </label>
                  </div>
                )}
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Приоритет</label>
                  <input type="number" className="input text-sm" value={gw.priority}
                    onChange={e => updateGateway(i, 'priority', parseInt(e.target.value) || 1)} min={1} />
                  <p className="text-[10px] text-gray-600 mt-0.5">Меньше = выше приоритет</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 justify-end pt-2 border-t border-dark-600/30">
        <button type="button" onClick={onCancel} className="btn-ghost text-sm">Отмена</button>
        <button type="submit" className="btn-primary text-sm">Создать конфигурацию</button>
      </div>
    </form>
  )
}
