import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import clsx from 'clsx'

const navItems = [
  { to: '/', label: 'Dashboard', icon: DashboardIcon },
  { to: '/loadbalancer', label: 'Load Balancer', icon: LBIcon },
  { to: '/update', label: 'Обновление', icon: UpdateIcon },
]

export default function Layout() {
  const { user, logout } = useAuthStore()
  const location = useLocation()

  // Page title based on current route
  const pageTitle = navItems.find(
    item => item.to === '/' ? location.pathname === '/' : location.pathname.startsWith(item.to)
  )?.label || 'The Blackwall'

  return (
    <div className="min-h-screen flex bg-dark-950">
      {/* Narrow icon sidebar — UniFi style */}
      <aside className="w-[68px] bg-dark-900 border-r border-dark-700/50 flex flex-col fixed h-full z-50">
        {/* Logo */}
        <div className="flex items-center justify-center py-5">
          <div className="w-10 h-10 rounded-xl bg-accent/15 flex items-center justify-center border border-accent/20">
            <svg className="w-5 h-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
          </div>
        </div>

        {/* Navigation icons */}
        <nav className="flex-1 flex flex-col items-center gap-1 px-2 pt-2">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              title={item.label}
              className={({ isActive }) => clsx(
                'w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-200 group relative',
                isActive
                  ? 'bg-accent/15 text-accent shadow-lg shadow-accent/10'
                  : 'text-gray-500 hover:text-gray-200 hover:bg-dark-700/50'
              )}
            >
              <item.icon />
              {/* Tooltip */}
              <span className="absolute left-full ml-3 px-2.5 py-1 bg-dark-700 text-white text-xs rounded-lg
                opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all whitespace-nowrap
                pointer-events-none shadow-xl border border-dark-600/50">
                {item.label}
              </span>
            </NavLink>
          ))}
        </nav>

        {/* User avatar + logout at bottom */}
        <div className="flex flex-col items-center gap-2 pb-4">
          <div className="w-9 h-9 rounded-full bg-dark-600 flex items-center justify-center text-xs font-bold text-gray-300 uppercase" title={user?.username}>
            {user?.username?.charAt(0) || 'U'}
          </div>
          <button
            onClick={logout}
            className="w-9 h-9 rounded-xl flex items-center justify-center text-gray-500 hover:text-accent hover:bg-accent/10 transition-colors"
            title="Выйти"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
            </svg>
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 ml-[68px] min-h-screen">
        {/* Top bar */}
        <header className="sticky top-0 z-40 px-8 py-4 bg-dark-950/80 backdrop-blur-xl border-b border-dark-700/30">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-white">{pageTitle}</h1>
            </div>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1.5 text-xs text-gray-500">
                <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                Онлайн
              </span>
              <span className="text-xs text-gray-600">v0.1.0</span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

function DashboardIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zm0 9.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zm0 9.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25a2.25 2.25 0 01-2.25-2.25v-2.25z" />
    </svg>
  )
}

function LBIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
    </svg>
  )
}

function UpdateIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
    </svg>
  )
}
