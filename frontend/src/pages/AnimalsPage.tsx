import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Filter, PawPrint, Search } from 'lucide-react'
import { fetchAnimals } from '../services/api'
import type { GlobalTrackResponse } from '../types/api'

function riskClass(level: string) {
  switch (level?.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-rose-500/20 text-rose-300'
    case 'HIGH':
      return 'bg-amber-500/20 text-amber-300'
    case 'MODERATE':
      return 'bg-yellow-500/20 text-yellow-200'
    default:
      return 'bg-emerald-500/20 text-emerald-300'
  }
}

export function AnimalsPage() {
  const [animals, setAnimals] = useState<GlobalTrackResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedSpecies, setSelectedSpecies] = useState('ALL')
  const [selectedRisk, setSelectedRisk] = useState('ALL')

  useEffect(() => {
    void fetchAnimals()
      .then(setAnimals)
      .finally(() => setLoading(false))
  }, [])

  const uniqueSpecies = useMemo(() => {
    const set = new Set<string>()
    animals.forEach((a) => set.add(a.species))
    return Array.from(set).sort()
  }, [animals])

  const filtered = useMemo(() => {
    return animals.filter((animal) => {
      const matchSearch =
        !search ||
        animal.species.toLowerCase().includes(search.toLowerCase()) ||
        animal.video_filename.toLowerCase().includes(search.toLowerCase()) ||
        String(animal.track_id).includes(search)
      const matchSpecies = selectedSpecies === 'ALL' || animal.species === selectedSpecies
      const matchRisk = selectedRisk === 'ALL' || animal.risk_level.toUpperCase() === selectedRisk
      return matchSearch && matchSpecies && matchRisk
    })
  }, [animals, search, selectedSpecies, selectedRisk])

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-white md:text-3xl">Tracked Animals</h1>
        <p className="mt-1 text-sm text-slate-400">
          Persistent identities across analysed camera-trap videos. Speeds are pixel-space movement.
        </p>
      </div>

      {/* Filters & Search Toolbar */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="relative min-w-[220px] flex-1">
          <Search size={16} className="absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search by species, filename, ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2 pl-9 pr-4 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-emerald-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-slate-400">
            <Filter size={14} />
            <span>Species:</span>
            <select
              value={selectedSpecies}
              onChange={(e) => setSelectedSpecies(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-slate-300 outline-none"
            >
              <option value="ALL">All Species ({animals.length})</option>
              {uniqueSpecies.map((sp) => (
                <option key={sp} value={sp}>
                  {sp.replace('_', ' ').toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-slate-400">
            <span>Risk Level:</span>
            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-slate-300 outline-none"
            >
              <option value="ALL">All Levels</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MODERATE">Moderate</option>
              <option value="LOW">Low</option>
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <p className="py-12 text-center text-slate-500">Loading tracks…</p>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-800 py-16 text-center">
          <PawPrint className="mx-auto mb-3 text-slate-600" size={36} />
          <p className="text-white">No animals found matching criteria</p>
          <p className="mt-1 text-sm text-slate-500">Try adjusting your search terms or filters.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-slate-500">
              <tr className="border-b border-slate-800">
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Species</th>
                <th className="px-4 py-3">Video</th>
                <th className="px-4 py-3">Behaviour</th>
                <th className="px-4 py-3">Direction</th>
                <th className="px-4 py-3">Speed</th>
                <th className="px-4 py-3">Risk</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {filtered.map((animal) => (
                <tr key={`${animal.analysis_id}-${animal.track_id}`} className="hover:bg-slate-800/40">
                  <td className="px-4 py-3 font-mono font-bold text-white">#{animal.track_id}</td>
                  <td className="px-4 py-3 capitalize text-emerald-300 font-medium">
                    {animal.species.replaceAll('_', ' ')}
                  </td>
                  <td className="px-4 py-3 truncate max-w-[180px] text-slate-400">{animal.video_filename}</td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                      {animal.behavior}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{animal.direction}</td>
                  <td className="px-4 py-3 font-mono">{animal.average_speed_px_sec} px/s</td>
                  <td className="px-4 py-3">
                    <span className={`rounded px-2 py-0.5 text-xs font-semibold ${riskClass(animal.risk_level)}`}>
                      {animal.risk_level} {animal.risk_score}/100
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/analysis/${animal.video_id}`}
                      className="text-xs font-semibold text-emerald-400 hover:underline"
                    >
                      Open analysis
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}
