import { NavLink } from 'react-router-dom'
import {
  Shield,
  Upload,
  LayoutDashboard,
  BarChart3,
  Video as VideoIcon,
  AlertTriangle,
  PawPrint,
  Settings,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { fetchConfig } from '../services/api'

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/videos', label: 'Videos', icon: VideoIcon },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/animals', label: 'Animals', icon: PawPrint },
  { to: '/risk-events', label: 'Risk Events', icon: AlertTriangle },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function AppShell({ children }: { children: ReactNode }) {
  const [demoMode, setDemoMode] = useState(false)

  useEffect(() => {
    void fetchConfig()
      .then((cfg) => setDemoMode(cfg.demo_mode))
      .catch(() => undefined)
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.08),_transparent_45%)]" />
      {demoMode && (
        <div className="relative z-40 bg-amber-500/15 px-4 py-1.5 text-center text-[11px] font-semibold tracking-wide text-amber-200">
          DEMO / MOCK DATA — detector fallback is active. Predictions are not presented as MegaDetector output.
        </div>
      )}
      
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3.5">
          <NavLink to="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30">
              <Shield size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold tracking-[0.25em] text-white">WILDLIFEGUARD</span>
                <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-400 ring-1 ring-emerald-500/30">
                  AI Pipeline
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Wildlife Detection, Tracking & Farm Encounter-Risk Assessment</p>
            </div>
          </NavLink>

          <nav className="flex items-center gap-1.5">
            {links.map((link) => {
              const Icon = link.icon
              return (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition ${
                      isActive
                        ? 'bg-slate-800 text-emerald-400 shadow-sm ring-1 ring-slate-700'
                        : 'text-slate-400 hover:bg-slate-900 hover:text-white'
                    }`
                  }
                >
                  <Icon size={16} />
                  {link.label}
                </NavLink>
              )
            })}
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="relative flex-1">{children}</div>

      {/* Scientific Limitation & Safety Disclaimer */}
      <footer className="relative mt-auto border-t border-slate-900 bg-slate-950/90 px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center gap-3 text-xs text-slate-500">
          <AlertTriangle size={16} className="text-amber-500/80 shrink-0" />
          <p>
            <strong className="text-slate-400">Scientific Disclaimer:</strong> This system provides an AI-assisted assessment of observable wildlife movement and proximity patterns. It does not determine an animal's intentions or guarantee that an animal is dangerous. Risk scores are estimates based on physical factors and should not replace human judgment or expert wildlife guidance.
          </p>
        </div>
      </footer>
    </div>
  )
}
