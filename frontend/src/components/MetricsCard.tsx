import clsx from 'clsx'

interface Props {
  title: string
  value: string
  subtitle?: string
  percent?: number
  icon: 'cpu' | 'memory' | 'download' | 'upload'
}

const icons: Record<string, JSX.Element> = {
  cpu: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25z" />
    </svg>
  ),
  memory: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zm0 9.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zm0 9.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25a2.25 2.25 0 01-2.25-2.25v-2.25z" />
    </svg>
  ),
  download: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
  ),
  upload: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
    </svg>
  ),
}

export default function MetricsCard({ title, value, subtitle, percent, icon }: Props) {
  const color = percent !== undefined
    ? percent > 90 ? 'text-danger' : percent > 70 ? 'text-warning' : 'text-accent'
    : 'text-accent'

  const iconBg = percent !== undefined
    ? percent > 90 ? 'bg-danger/10 text-danger' : percent > 70 ? 'bg-warning/10 text-warning' : 'bg-accent/10 text-accent'
    : 'bg-accent/10 text-accent'

  return (
    <div className="card group hover:border-dark-500/50 transition-colors">
      <div className="flex items-start gap-3.5">
        <div className={clsx('p-2.5 rounded-xl', iconBg)}>
          {icons[icon]}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{title}</p>
          <p className={clsx('text-xl font-bold mt-1', color)}>{value}</p>
          {subtitle && <p className="text-[11px] text-gray-600 mt-0.5 truncate">{subtitle}</p>}
        </div>
      </div>
      {percent !== undefined && (
        <div className="mt-3 h-1 bg-dark-700/50 rounded-full overflow-hidden">
          <div
            className={clsx('h-full rounded-full transition-all duration-700', {
              'bg-danger': percent > 90,
              'bg-warning': percent > 70 && percent <= 90,
              'bg-accent': percent <= 70,
            })}
            style={{ width: `${Math.min(percent, 100)}%` }}
          />
        </div>
      )}
    </div>
  )
}
