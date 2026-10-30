import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  AlertOctagon,
  ArrowRight,
  Eye,
  FileVideo,
  Play,
  PlusCircle,
  ShieldCheck,
  TrendingUp,
  Zap,
} from 'lucide-react'
import { fetchAnalyticsOverview, fetchConfig, fetchVideos, videoThumbnailUrl } from '../services/api'
import type { AnalyticsOverviewResponse, PublicConfig, VideoMetadata } from '../types/api'

export function DashboardPage() {
  const [overview, setOverview] = useState<AnalyticsOverviewResponse | null>(null)
  const [videos, setVideos] = useState<VideoMetadata[]>([])
  const [config, setConfig] = useState<PublicConfig | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetchAnalyticsOverview().catch(() => null),
      fetchVideos().catch(() => []),
      fetchConfig().catch(() => null),
    ]).then(([ov, vids, cfg]) => {
      setOverview(ov)
      setVideos(vids)
      setConfig(cfg)
      setLoading(false)
    })
  }, [])

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      {/* Top Hero Banner */}
      <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white md:text-3xl">
            Wildlife Encounter-Risk Monitoring
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Real-time pipeline overview: detection, tracking, behaviour recognition, and farm proximity evaluation.
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            to="/upload"
            className="flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-slate-950 shadow-md transition hover:bg-emerald-400"
          >
            <PlusCircle size={18} />
            Upload Video
          </Link>
          <Link
            to="/analytics"
            className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-slate-800"
          >
            <TrendingUp size={18} />
            Analytics
          </Link>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="mb-10 grid grid-cols-2 gap-4 md:grid-cols-5">
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Total Animals</span>
            <Eye size={18} className="text-emerald-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">
            {loading ? '…' : overview?.total_animals_detected ?? 0}
          </div>
          <p className="mt-1 text-xs text-slate-500">Across camera-trap recordings</p>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Unique Tracks</span>
            <Activity size={18} className="text-sky-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">
            {loading ? '…' : overview?.total_unique_tracks ?? 0}
          </div>
          <p className="mt-1 text-xs text-slate-500">Persistent trajectories mapped</p>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Species Detected</span>
            <ShieldCheck size={18} className="text-indigo-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">
            {loading ? '…' : Object.keys(overview?.species_breakdown ?? {}).length}
          </div>
          <p className="mt-1 text-xs text-slate-500">Classified wildlife species</p>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">High Risk Events</span>
            <AlertOctagon size={18} className="text-amber-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-amber-400">
            {loading ? '…' : overview?.high_risk_events_count ?? 0}
          </div>
          <p className="mt-1 text-xs text-slate-500">Boundary proximity alerts</p>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Target Process FPS</span>
            <Zap size={18} className="text-teal-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">{config?.process_fps ?? 5} FPS</div>
          <p className="mt-1 text-xs text-slate-500">Configurable OpenCV sampling</p>
        </div>
      </div>

      {/* Videos Section */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Uploaded Camera-Trap Videos</h2>
            <p className="text-xs text-slate-400">Select a video to define farm boundary and view AI analysis.</p>
          </div>
          <Link to="/videos" className="text-xs font-medium text-emerald-400 hover:underline">
            View all videos ({videos.length})
          </Link>
        </div>

        {videos.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-800 py-12 text-center">
            <FileVideo className="mx-auto mb-3 text-slate-600" size={36} />
            <p className="text-sm font-medium text-slate-300">No wildlife videos uploaded yet</p>
            <p className="mt-1 text-xs text-slate-500">Upload an MP4, AVI, MOV, or MKV file to begin.</p>
            <Link
              to="/upload"
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/20 px-3.5 py-1.5 text-xs font-medium text-emerald-300 hover:bg-emerald-500/30"
            >
              Upload Video <ArrowRight size={14} />
            </Link>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {videos.slice(0, 6).map((video) => (
              <div
                key={video.video_id}
                className="group relative flex flex-col justify-between overflow-hidden rounded-xl border border-slate-800/90 bg-slate-900/70 p-4 transition hover:border-slate-700"
              >
                <div>
                  <div className="relative mb-3 aspect-video w-full overflow-hidden rounded-lg bg-black/60">
                    {video.thumbnail_url ? (
                      <img
                        src={videoThumbnailUrl(video.video_id)}
                        alt={video.filename}
                        className="h-full w-full object-cover transition group-hover:scale-105"
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center text-slate-600">
                        <FileVideo size={32} />
                      </div>
                    )}
                    {video.duration_seconds && (
                      <span className="absolute bottom-2 right-2 rounded bg-black/80 px-1.5 py-0.5 text-[10px] font-mono text-white">
                        {video.duration_seconds}s
                      </span>
                    )}
                  </div>
                  <h3 className="truncate text-sm font-medium text-white" title={video.filename}>
                    {video.filename}
                  </h3>
                  <div className="mt-1 flex items-center gap-2 text-xs text-slate-400">
                    <span>{video.width ? `${video.width}×${video.height}` : 'Video'}</span>
                    <span>•</span>
                    <span>{video.fps ? `${video.fps} FPS` : `${(video.size_bytes / (1024 * 1024)).toFixed(1)} MB`}</span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300">
                    {video.status}
                  </span>
                  <Link
                    to={`/analysis/${video.video_id}`}
                    className="flex items-center gap-1 rounded-lg bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/25"
                  >
                    <Play size={13} />
                    Analyze
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AI Pipeline Architecture Card */}
      <div className="mt-8 rounded-2xl border border-slate-800/80 bg-slate-900/30 p-6">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">WildlifeGuard AI Architecture</h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 md:grid-cols-5 text-xs text-slate-300">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
            <span className="font-mono text-emerald-400">01. Frame Extraction</span>
            <p className="mt-1 text-slate-400">OpenCV decodes at configurable 5 FPS, downscaling to 1280px max width.</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
            <span className="font-mono text-sky-400">02. MegaDetector V6</span>
            <p className="mt-1 text-slate-400">Microsoft PyTorch-Wildlife animal localization with CPU/CUDA auto-detection.</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
            <span className="font-mono text-indigo-400">03. Species & Tracking</span>
            <p className="mt-1 text-slate-400">Crop classification + ByteIoUTracker for continuous identity and trajectory history.</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
            <span className="font-mono text-amber-400">04. Farm Geometry</span>
            <p className="mt-1 text-slate-400">User polygon definition, point-in-polygon & distance in image-space pixels.</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
            <span className="font-mono text-rose-400">05. Risk Assessment</span>
            <p className="mt-1 text-slate-400">0–100 encounter risk based on species, proximity, approach vector, and speed.</p>
          </div>
        </div>
      </div>
    </main>
  )
}
