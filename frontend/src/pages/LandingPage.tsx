import { Link } from 'react-router-dom'
import { Shield, Activity, Camera } from 'lucide-react'
import { useBackendHealth } from '../hooks/useBackendHealth'

export function LandingPage() {
  const { status, data, error, refresh } = useBackendHealth()

  const badge =
    status === 'ok'
      ? 'Connected'
      : status === 'loading'
        ? 'Checking…'
        : status === 'error'
          ? 'Offline'
          : 'Idle'

  const badgeClass =
    status === 'ok'
      ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
      : status === 'loading'
        ? 'bg-amber-500/15 text-amber-200 border-amber-500/40'
        : 'bg-rose-500/15 text-rose-300 border-rose-500/40'

  return (
    <main className="mx-auto flex min-h-[calc(100vh-73px)] max-w-5xl flex-col justify-center px-6 py-16">
      <div className="mb-10 flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
          <Shield size={26} />
        </div>
        <div>
          <p className="text-xs font-semibold tracking-[0.28em] text-emerald-400">WILDLIFEGUARD</p>
          <p className="text-sm text-slate-400">
            AI-Powered Wildlife Detection, Tracking & Farm Risk Monitoring
          </p>
        </div>
      </div>

      <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
        Upload camera-trap video. Encounter-risk estimates come from observable evidence.
      </h1>
      <p className="mt-4 max-w-2xl text-lg text-slate-400">
        This version works only with uploaded files. There is no live camera or hardware control.
        Detection models are added in later milestones.
      </p>

      <div className="mt-8">
        <Link
          to="/upload"
          className="inline-flex rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-medium text-slate-950 hover:bg-emerald-400"
        >
          Upload a video
        </Link>
      </div>

      <section className="mt-10 grid gap-4 sm:grid-cols-3">
        <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <Camera className="mb-3 text-emerald-400" size={22} />
          <h2 className="font-medium text-white">Uploaded video only</h2>
          <p className="mt-2 text-sm text-slate-400">
            MP4, AVI, MOV, and MKV files are stored with UUID names.
          </p>
        </article>
        <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <Activity className="mb-3 text-emerald-400" size={22} />
          <h2 className="font-medium text-white">Backend health</h2>
          <p className="mt-2 text-sm text-slate-400">
            The dashboard calls <code className="text-emerald-300">GET /api/health</code>.
          </p>
        </article>
        <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <div className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium ${badgeClass}`}>
            {badge}
          </div>
          <h2 className="mt-3 font-medium text-white">Connection status</h2>
          <p className="mt-2 font-mono text-sm text-slate-300">
            {data ? JSON.stringify(data) : error ?? 'Waiting for response'}
          </p>
          <button
            type="button"
            onClick={() => void refresh()}
            className="mt-4 rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400"
          >
            Recheck backend
          </button>
        </article>
      </section>

      <p className="mt-12 max-w-3xl text-xs leading-relaxed text-slate-500">
        This system provides an AI-assisted assessment of observable wildlife movement and proximity
        patterns. It does not determine an animal&apos;s intentions or guarantee that an animal is
        dangerous. Risk scores are estimates and should not replace human judgment or expert wildlife
        guidance.
      </p>
    </main>
  )
}
