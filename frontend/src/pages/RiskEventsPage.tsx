import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, Filter, Search } from 'lucide-react'
import { fetchRiskEvents } from '../services/api'
import type { GlobalRiskEventResponse } from '../types/api'

function riskClass(level: string) {
  switch (level?.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-rose-500/20 text-rose-300 border-rose-500/30'
    case 'HIGH':
      return 'bg-amber-500/20 text-amber-300 border-amber-500/30'
    case 'MODERATE':
      return 'bg-yellow-500/20 text-yellow-200 border-yellow-500/30'
    default:
      return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
  }
}

export function RiskEventsPage() {
  const [events, setEvents] = useState<GlobalRiskEventResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedRisk, setSelectedRisk] = useState('ALL')

  useEffect(() => {
    void fetchRiskEvents()
      .then(setEvents)
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    return events.filter((event) => {
      const matchSearch =
        !search ||
        event.species.toLowerCase().includes(search.toLowerCase()) ||
        event.video_filename.toLowerCase().includes(search.toLowerCase()) ||
        event.event_code.toLowerCase().includes(search.toLowerCase())
      const matchRisk = selectedRisk === 'ALL' || event.risk_level.toUpperCase() === selectedRisk
      return matchSearch && matchRisk
    })
  }, [events, search, selectedRisk])

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-white md:text-3xl">Risk Events Log</h1>
        <p className="mt-1 text-sm text-slate-400">
          Chronological encounter-risk estimates based on observable proximity, trajectory vector, and pixel velocity.
        </p>
      </div>

      {/* Filters Toolbar */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="relative min-w-[220px] flex-1">
          <Search size={16} className="absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search by species, event code, video…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2 pl-9 pr-4 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-emerald-500"
          />
        </div>

        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Filter size={14} />
          <span>Risk Level:</span>
          <select
            value={selectedRisk}
            onChange={(e) => setSelectedRisk(e.target.value)}
            className="rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-slate-300 outline-none"
          >
            <option value="ALL">All Risk Levels ({events.length})</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MODERATE">Moderate</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {loading ? (
        <p className="py-12 text-center text-slate-500">Loading events…</p>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-800 py-16 text-center">
          <AlertTriangle className="mx-auto mb-3 text-slate-600" size={36} />
          <p className="text-white">No risk events match criteria</p>
          <p className="mt-1 text-sm text-slate-500">Try adjusting your filters or run analysis on new videos.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((event) => (
            <article
              key={event.id}
              className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 transition hover:border-slate-700"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-slate-400">{event.event_code}</span>
                    <h2 className="font-semibold text-white capitalize">
                      {event.species.replaceAll('_', ' ')} #{event.track_id}
                    </h2>
                    <span className={`rounded border px-2 py-0.5 text-xs font-bold ${riskClass(event.risk_level)}`}>
                      {event.risk_level} · {event.risk_score}/100
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-400">
                    {event.video_filename} · {event.timestamp_sec.toFixed(1)}s · {event.distance_image_space} px to farm · {event.direction} · {event.behavior}
                  </p>
                </div>
                <Link
                  to={`/analysis/${event.video_id}`}
                  className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400"
                >
                  View Video
                </Link>
              </div>
              <ul className="mt-3 flex flex-wrap gap-1.5">
                {event.factors.map((factor) => (
                  <li key={factor} className="rounded bg-slate-800 px-2 py-0.5 text-[11px] text-slate-300">
                    ✓ {factor}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-[11px] text-slate-500">
                Estimate confidence {(event.confidence * 100).toFixed(0)}%. Physical movement metrics only; not a claim of animal danger.
              </p>
            </article>
          ))}
        </div>
      )}
    </main>
  )
}
