import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AlertOctagon, BarChart3, Eye, ShieldCheck } from 'lucide-react'
import { fetchAnalyticsOverview } from '../services/api'
import type { AnalyticsOverviewResponse } from '../types/api'

const RISK_COLORS: Record<string, string> = {
  LOW: '#10b981',
  MODERATE: '#eab308',
  HIGH: '#f97316',
  CRITICAL: '#ef4444',
}

const SPECIES_PALETTE = ['#10b981', '#06b6d4', '#6366f1', '#ec4899', '#f59e0b', '#8b5cf6']

export function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsOverviewResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void fetchAnalyticsOverview()
      .then(setData)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="py-20 text-center text-slate-500">Loading aggregate analytics…</div>
  }

  // Format data for charts
  const speciesData = Object.entries(data?.species_breakdown ?? {}).map(([name, count]) => ({
    name: name.replace('_', ' ').toUpperCase(),
    count,
  }))

  const riskData = Object.entries(data?.risk_level_breakdown ?? {}).map(([level, count]) => ({
    name: level,
    count,
  }))

  const behaviorData = Object.entries(data?.behavior_breakdown ?? {}).map(([beh, count]) => ({
    name: beh,
    count,
  }))

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-white md:text-3xl">Wildlife & Risk Analytics</h1>
        <p className="mt-1 text-sm text-slate-400">
          Aggregated distributions across all camera-trap recordings and analysis runs.
        </p>
      </div>

      {/* Summary KPI Cards */}
      <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs uppercase font-medium">Analyses Executed</span>
            <BarChart3 size={18} className="text-emerald-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">{data?.total_analyses ?? 0}</div>
          <p className="mt-1 text-xs text-slate-500">{data?.total_videos ?? 0} total videos stored</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs uppercase font-medium">Animals Detected</span>
            <Eye size={18} className="text-sky-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">{data?.total_animals_detected ?? 0}</div>
          <p className="mt-1 text-xs text-slate-500">Bounding boxes localized</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs uppercase font-medium">Unique Tracks</span>
            <ShieldCheck size={18} className="text-indigo-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">{data?.total_unique_tracks ?? 0}</div>
          <p className="mt-1 text-xs text-slate-500">Persistent trajectories</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs uppercase font-medium">High / Critical Alerts</span>
            <AlertOctagon size={18} className="text-rose-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-rose-400">{data?.high_risk_events_count ?? 0}</div>
          <p className="mt-1 text-xs text-slate-500">Proximity risk events</p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Species Distribution Chart */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-sm">
          <h2 className="text-base font-semibold text-white">Species Breakdown</h2>
          <p className="text-xs text-slate-400 mb-6">Distribution of classified wildlife across analyses</p>
          <div className="h-72 w-full">
            {speciesData.length === 0 ? (
              <div className="flex h-full items-center justify-center text-xs text-slate-500">
                No species data available yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={speciesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                    itemStyle={{ color: '#ffffff' }}
                  />
                  <Bar dataKey="count" fill="#10b981" radius={[6, 6, 0, 0]}>
                    {speciesData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={SPECIES_PALETTE[index % SPECIES_PALETTE.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Risk Distribution Chart */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-sm">
          <h2 className="text-base font-semibold text-white">Encounter-Risk Distribution</h2>
          <p className="text-xs text-slate-400 mb-6">Proportion of tracks by encounter-risk tier</p>
          <div className="h-72 w-full">
            {riskData.every((d) => d.count === 0) ? (
              <div className="flex h-full items-center justify-center text-xs text-slate-500">
                No risk events recorded yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskData.filter((d) => d.count > 0)}
                    dataKey="count"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={95}
                    innerRadius={45}
                    paddingAngle={3}
                    label={({ name, percent }: { name?: string; percent?: number }) => `${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {riskData.map((entry) => (
                      <Cell key={entry.name} fill={RISK_COLORS[entry.name] || '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                    itemStyle={{ color: '#ffffff' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Observable Behaviour Distribution */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-sm lg:col-span-2">
          <h2 className="text-base font-semibold text-white">Observable Behaviour Patterns</h2>
          <p className="text-xs text-slate-400 mb-6">Kinematic movement pattern frequencies</p>
          <div className="h-72 w-full">
            {behaviorData.length === 0 ? (
              <div className="flex h-full items-center justify-center text-xs text-slate-500">
                No behaviour data recorded yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={behaviorData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                    itemStyle={{ color: '#ffffff' }}
                  />
                  <Bar dataKey="count" fill="#38bdf8" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </main>
  )
}
