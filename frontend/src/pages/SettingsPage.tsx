import { useEffect, useState } from 'react'
import { fetchConfig } from '../services/api'
import type { PublicConfig } from '../types/api'

export function SettingsPage() {
  const [config, setConfig] = useState<PublicConfig | null>(null)

  useEffect(() => {
    void fetchConfig().then(setConfig).catch(() => undefined)
  }, [])

  const rows = config
    ? [
        ['Demo mode', String(config.demo_mode)],
        ['Process FPS', String(config.process_fps)],
        ['Model device', config.model_device],
        ['Detection model', config.detection_model_name],
        ['Detection confidence', String(config.detection_confidence)],
        ['Classification confidence', String(config.classification_confidence)],
        ['Max video size (MB)', String(config.max_video_size_mb)],
        ['Allowed formats', config.allowed_extensions.join(', ')],
        ['Risk LOW max', String(config.risk_low_max)],
        ['Risk MODERATE max', String(config.risk_moderate_max)],
        ['Risk HIGH max', String(config.risk_high_max)],
      ]
    : []

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="text-2xl font-bold tracking-tight text-white md:text-3xl">Settings</h1>
      <p className="mt-2 text-sm text-slate-400">
        Runtime configuration is loaded from <code className="text-emerald-300">.env</code>. Change values there and
        restart the backend. Thresholds are prototype defaults, not safety claims.
      </p>

      <div className="mt-8 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
        {config ? (
          <dl>
            {rows.map(([label, value]) => (
              <div key={label} className="grid grid-cols-2 gap-4 border-b border-slate-800 px-5 py-3 last:border-0">
                <dt className="text-sm text-slate-400">{label}</dt>
                <dd className="font-mono text-sm text-white">{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="p-6 text-slate-500">Loading configuration…</p>
        )}
      </div>
    </main>
  )
}
