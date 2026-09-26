import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Wind, Navigation, LogOut } from 'lucide-react'
import clsx from 'clsx'
import { getHealth } from '../utils/api'
import AuthModal from './AuthModal'

const NAV_LINKS = [
  { to: '/', label: 'Home', icon: Wind },
  { to: '/commute', label: 'Commute', icon: Navigation },
]

export default function Navbar() {
  const { pathname } = useLocation()
  const [alive, setAlive] = useState(false)
  const [isAuthOpen, setIsAuthOpen] = useState(false)
  const [user, setUser] = useState(null)

  useEffect(() => {
    // Check if user is logged in
    const stored = localStorage.getItem('aqi_logged_in_user')
    if (stored) {
      try {
        setUser(JSON.parse(stored))
      } catch (e) {
        localStorage.removeItem('aqi_logged_in_user')
      }
    }

    let isMounted = true
    const checkHealth = async () => {
      try {
        const res = await getHealth()
        if (isMounted) setAlive(res.status === 'healthy')
      } catch (err) {
        if (isMounted) setAlive(false)
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 10000)
    return () => {
      isMounted = false
      clearInterval(interval)
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('aqi_logged_in_user')
    setUser(null)
  }

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-50" style={{
        background: 'rgba(8,13,26,0.85)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(34,211,238,0.1)',
      }}>
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{
              background: 'linear-gradient(135deg, rgba(34,211,238,0.2), rgba(34,211,238,0.05))',
              border: '1px solid rgba(34,211,238,0.3)',
            }}>
              <Wind size={16} className="text-cyan-400" />
            </div>
            <span className="font-display font-bold text-white text-lg tracking-tight">
              AirRoute <span className="text-cyan-400">Delhi</span>
            </span>
          </Link>

          {/* Links */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map(({ to, label, icon: Icon }) => {
              const active = pathname === to
              return (
                <Link
                  key={to}
                  to={to}
                  className={clsx(
                    'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                    active
                      ? 'text-cyan-400 bg-cyan-400/10'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  )}
                >
                  <Icon size={14} />
                  {label}
                </Link>
              )
            })}
          </div>

          {/* Right Section: Status Dot & Login Button */}
          <div className="flex items-center gap-4">
            {/* Status dot */}
            <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500 font-mono">
              <span className={clsx(
                "w-2 h-2 rounded-full transition-all duration-300",
                alive ? "bg-green-400 animate-pulse" : "bg-red-400"
              )} />
              {alive ? 'API Live' : 'API Offline'}
            </div>

            {/* User Profile / Login Button */}
            {user ? (
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                  <div className="w-5 h-5 rounded-full bg-cyan-400 text-black flex items-center justify-center text-[10px] font-bold">
                    {user.name ? user.name[0].toUpperCase() : 'U'}
                  </div>
                  <span className="text-xs font-semibold text-slate-200">{user.name}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-red-400 border border-red-500/20 hover:border-red-500/40 hover:bg-red-500/10 transition-all duration-200"
                >
                  <LogOut size={12} />
                  Logout
                </button>
              </div>
            ) : (
              <button
                onClick={() => setIsAuthOpen(true)}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold text-cyan-400 border border-cyan-400/30 hover:border-cyan-400 hover:bg-cyan-400/10 transition-all duration-200"
              >
                Sign In
              </button>
            )}
          </div>
        </div>

        {/* Mobile nav */}
        <div className="md:hidden flex overflow-x-auto gap-1 px-4 pb-2">
          {NAV_LINKS.map(({ to, label, icon: Icon }) => {
            const active = pathname === to
            return (
              <Link
                key={to}
                to={to}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs whitespace-nowrap transition-all',
                  active ? 'text-cyan-400 bg-cyan-400/10' : 'text-slate-400 hover:text-white'
                )}
              >
                <Icon size={12} />
                {label}
              </Link>
            )
          })}
        </div>
      </nav>

      {/* Auth Modal Popup */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onLoginSuccess={(userData) => setUser(userData)}
      />
    </>
  )
}

