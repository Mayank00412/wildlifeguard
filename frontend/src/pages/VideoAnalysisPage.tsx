import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Clock,
  Crosshair,
  Download,
  FileVideo,
  Layers,
  Play,
  RotateCcw,
  Save,
  Sparkles,
} from 'lucide-react'
import {
  analysisExportUrl,
  annotatedVideoUrl,
  fetchAnalysisResults,
  fetchAnalysisRiskEvents,
  fetchAnalysisStatus,
  fetchAnalysisTracks,
  fetchFarmBoundary,
  fetchVideo,
  saveFarmBoundary,
  startAnalysis,
  videoFileUrl,
} from '../services/api'
import type {
  AnalysisResultsResponse,
  AnalysisStatusResponse,
  RiskEventResponse,
  TrackResponse,
  VideoMetadata,
} from '../types/api'

export function VideoAnalysisPage() {
  const { videoId } = useParams<{ videoId: string }>()

  const [video, setVideo] = useState<VideoMetadata | null>(null)
  const [boundary, setBoundary] = useState<[number, number][]>([])
  const [boundaryDraft, setBoundaryDraft] = useState<[number, number][]>([])
  const [isEditingBoundary, setIsEditingBoundary] = useState(false)

  const [status, setStatus] = useState<AnalysisStatusResponse | null>(null)
  const [results, setResults] = useState<AnalysisResultsResponse | null>(null)
  const [tracks, setTracks] = useState<TrackResponse[]>([])
  const [riskEvents, setRiskEvents] = useState<RiskEventResponse[]>([])
  const [selectedTrack, setSelectedTrack] = useState<TrackResponse | null>(null)

  const [activeTab, setActiveTab] = useState<'tracks' | 'events'>('tracks')
  const [activePlayer, setActivePlayer] = useState<'dual' | 'annotated' | 'original'>('dual')
  const [targetFps, setTargetFps] = useState(5)
  const [starting, setStarting] = useState(false)

  const originalVideoRef = useRef<HTMLVideoElement>(null)
  const annotatedVideoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  // 1. Initial Load
  useEffect(() => {
    if (!videoId) return
    void fetchVideo(videoId).then(setVideo).catch(() => null)
    void fetchFarmBoundary(videoId)
      .then((res) => {
        setBoundary(res.polygon)
        setBoundaryDraft(res.polygon)
      })
      .catch(() => null)
    void checkStatusAndResults()
  }, [videoId])

  async function checkStatusAndResults() {
    if (!videoId) return
    try {
      const st = await fetchAnalysisStatus(videoId)
      setStatus(st)
      if (st.status === 'COMPLETED') {
        const [res, trks, evts] = await Promise.all([
          fetchAnalysisResults(videoId),
          fetchAnalysisTracks(videoId),
          fetchAnalysisRiskEvents(videoId),
        ])
        setResults(res)
        setTracks(trks)
        setRiskEvents(evts)
      }
    } catch {
      setStatus(null)
    }
  }

  // 2. Poll Status while queued or processing
  useEffect(() => {
    if (!status || (status.status !== 'PROCESSING' && status.status !== 'QUEUED')) return
    const interval = setInterval(async () => {
      try {
        const current = await fetchAnalysisStatus(videoId!)
        setStatus(current)
        if (current.status === 'COMPLETED' || current.status === 'FAILED') {
          clearInterval(interval)
          void checkStatusAndResults()
        }
      } catch {
        // ignore polling error
      }
    }, 1500)
    return () => clearInterval(interval)
  }, [status?.status, videoId])

  // 3. Handle Start Analysis
  async function handleStart() {
    if (!videoId) return
    setStarting(true)
    try {
      const st = await startAnalysis(videoId, boundary, targetFps)
      setStatus(st)
      setResults(null)
      setTracks([])
      setRiskEvents([])
    } catch (err) {
      alert('Failed to launch analysis. Ensure the backend is running.')
    } finally {
      setStarting(false)
    }
  }

  // 4. Boundary Canvas Click Handling
  function handleCanvasClick(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!isEditingBoundary) return
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    const x = Math.round((e.clientX - rect.left) * scaleX)
    const y = Math.round((e.clientY - rect.top) * scaleY)
    setBoundaryDraft((prev) => [...prev, [x, y]])
  }

  // 5. Draw Boundary on Canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    const pts = isEditingBoundary ? boundaryDraft : boundary
    if (pts.length === 0) return

    ctx.beginPath()
    ctx.moveTo(pts[0][0], pts[0][1])
    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(pts[i][0], pts[i][1])
    }
    if (pts.length >= 3) {
      ctx.closePath()
      ctx.fillStyle = 'rgba(16, 185, 129, 0.15)'
      ctx.fill()
    }
    ctx.strokeStyle = '#10b981'
    ctx.lineWidth = 3
    ctx.stroke()

    // Draw vertex handles
    pts.forEach(([x, y], idx) => {
      ctx.beginPath()
      ctx.arc(x, y, 5, 0, Math.PI * 2)
      ctx.fillStyle = '#34d399'
      ctx.fill()
      ctx.strokeStyle = '#064e3b'
      ctx.lineWidth = 1.5
      ctx.stroke()

      ctx.fillStyle = '#ffffff'
      ctx.font = '10px monospace'
      ctx.fillText(`P${idx + 1}`, x + 7, y - 5)
    })
  }, [boundary, boundaryDraft, isEditingBoundary])

  async function handleSaveBoundary() {
    if (!videoId) return
    await saveFarmBoundary(videoId, boundaryDraft)
    setBoundary(boundaryDraft)
    setIsEditingBoundary(false)
  }

  function handleSeekTo(timestampSec: number) {
    if (annotatedVideoRef.current) {
      annotatedVideoRef.current.currentTime = timestampSec
      annotatedVideoRef.current.play().catch(() => null)
    }
    if (originalVideoRef.current) {
      originalVideoRef.current.currentTime = timestampSec
      originalVideoRef.current.play().catch(() => null)
    }
  }

  // Synchronized dual playback handlers
  const handleOriginalPlay = () => {
    if (activePlayer === 'dual' && annotatedVideoRef.current && annotatedVideoRef.current.paused) {
      annotatedVideoRef.current.currentTime = originalVideoRef.current?.currentTime || 0
      annotatedVideoRef.current.play().catch(() => null)
    }
  }

  const handleOriginalPause = () => {
    if (activePlayer === 'dual' && annotatedVideoRef.current && !annotatedVideoRef.current.paused) {
      annotatedVideoRef.current.pause()
    }
  }

  const handleOriginalSeeked = () => {
    if (activePlayer === 'dual' && annotatedVideoRef.current && originalVideoRef.current) {
      if (Math.abs(annotatedVideoRef.current.currentTime - originalVideoRef.current.currentTime) > 0.3) {
        annotatedVideoRef.current.currentTime = originalVideoRef.current.currentTime
      }
    }
  }

  const handleAnnotatedPlay = () => {
    if (activePlayer === 'dual' && originalVideoRef.current && originalVideoRef.current.paused) {
      originalVideoRef.current.currentTime = annotatedVideoRef.current?.currentTime || 0
      originalVideoRef.current.play().catch(() => null)
    }
  }

  const handleAnnotatedPause = () => {
    if (activePlayer === 'dual' && originalVideoRef.current && !originalVideoRef.current.paused) {
      originalVideoRef.current.pause()
    }
  }

  const handleAnnotatedSeeked = () => {
    if (activePlayer === 'dual' && originalVideoRef.current && annotatedVideoRef.current) {
      if (Math.abs(originalVideoRef.current.currentTime - annotatedVideoRef.current.currentTime) > 0.3) {
        originalVideoRef.current.currentTime = annotatedVideoRef.current.currentTime
      }
    }
  }

  const riskBadgeColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/30'
      case 'HIGH':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
      case 'MODERATE':
        return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'
      default:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
    }
  }

  if (!video) {
    return (
      <div className="py-20 text-center text-slate-500">
        Loading video analysis environment…
      </div>
    )
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-6">
      {/* Top Breadcrumb & Action Header */}
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div className="flex items-center gap-3">
          <Link
            to="/videos"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-white"
          >
            <ArrowLeft size={16} />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white md:text-2xl">{video.filename}</h1>
              {results && (
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider ${riskBadgeColor(
                    results.max_risk_level,
                  )}`}
                >
                  {results.max_risk_level} Risk
                </span>
              )}
            </div>
            <p className="font-mono text-xs text-slate-500">ID: {video.video_id}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-300">
            <span>Sampling:</span>
            <select
              value={targetFps}
              onChange={(e) => setTargetFps(Number(e.target.value))}
              disabled={status?.status === 'PROCESSING'}
              className="rounded bg-slate-800 px-1.5 py-0.5 font-semibold text-emerald-400 outline-none"
            >
              <option value={2}>2 FPS</option>
              <option value={5}>5 FPS (Default)</option>
              <option value={10}>10 FPS</option>
            </select>
          </div>

          {results && (
            <div className="flex items-center gap-2">
              <a
                href={analysisExportUrl(video.video_id, 'csv')}
                download
                className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 hover:text-white"
                title="Export trajectory & risk data as CSV"
              >
                <Download size={14} />
                CSV
              </a>
              <a
                href={analysisExportUrl(video.video_id, 'json')}
                download
                className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 hover:text-white"
                title="Export full analysis report as JSON"
              >
                <Download size={14} />
                JSON
              </a>
            </div>
          )}

          <button
            type="button"
            disabled={starting || status?.status === 'PROCESSING' || status?.status === 'QUEUED'}
            onClick={() => void handleStart()}
            className="flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 shadow-md transition hover:bg-emerald-400 disabled:opacity-50"
          >
            <Play size={16} />
            {status?.status === 'COMPLETED' ? 'Re-run Analysis' : 'Start AI Analysis'}
          </button>
        </div>
      </div>

      {status?.status === 'FAILED' && (
        <div className="mb-6 rounded-2xl border border-rose-500/40 bg-rose-950/20 p-4 text-sm text-rose-200">
          Analysis failed: {status.error_message || status.current_stage}
        </div>
      )}

      {/* Progress Bar (When processing) */}
      {(status?.status === 'PROCESSING' || status?.status === 'QUEUED') && (
        <div className="mb-6 rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-5">
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2 font-medium text-emerald-400">
              <Sparkles size={16} className="animate-spin text-emerald-300" />
              {status.current_stage}
            </span>
            <span className="font-mono font-semibold text-white">{status.progress_percent}%</span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300"
              style={{ width: `${status.progress_percent}%` }}
            />
          </div>
        </div>
      )}

      {/* Farm Boundary Editor Toolbar */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800/80 bg-slate-900/60 px-4 py-2.5 text-xs text-slate-300">
        <div className="flex items-center gap-2">
          <Crosshair size={16} className="text-emerald-400" />
          <span className="font-semibold text-white">Farm Boundary Polygon:</span>
          <span>
            {boundary.length >= 3
              ? `${boundary.length} vertices defined`
              : 'No polygon boundary defined yet'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {isEditingBoundary ? (
            <>
              <button
                type="button"
                onClick={() => setBoundaryDraft([])}
                className="flex items-center gap-1 rounded bg-slate-800 px-2.5 py-1 text-slate-300 hover:text-white"
              >
                <RotateCcw size={12} /> Clear Points
              </button>
              <button
                type="button"
                onClick={() => setIsEditingBoundary(false)}
                className="rounded px-2.5 py-1 text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={boundaryDraft.length < 3}
                onClick={() => void handleSaveBoundary()}
                className="flex items-center gap-1 rounded bg-emerald-500 px-3 py-1 font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-40"
              >
                <Save size={12} /> Save Boundary
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => {
                setBoundaryDraft([...boundary])
                setIsEditingBoundary(true)
              }}
              className="flex items-center gap-1 rounded bg-slate-800 px-3 py-1 text-emerald-400 hover:bg-slate-700"
            >
              <Layers size={13} /> {boundary.length >= 3 ? 'Edit Boundary' : 'Draw Boundary on Video'}
            </button>
          )}
        </div>
      </div>

      {/* Video Players Container */}
      <div className="mb-6 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/90 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-800/80 bg-slate-950/60 px-5 py-3">
          <div className="flex items-center gap-4 text-xs">
            <button
              type="button"
              onClick={() => setActivePlayer('dual')}
              className={`font-medium ${activePlayer === 'dual' ? 'text-emerald-400' : 'text-slate-400 hover:text-white'}`}
            >
              Dual Comparison (Synced)
            </button>
            <button
              type="button"
              onClick={() => setActivePlayer('annotated')}
              className={`font-medium ${activePlayer === 'annotated' ? 'text-emerald-400' : 'text-slate-400 hover:text-white'}`}
            >
              AI Annotated Only
            </button>
            <button
              type="button"
              onClick={() => setActivePlayer('original')}
              className={`font-medium ${activePlayer === 'original' ? 'text-emerald-400' : 'text-slate-400 hover:text-white'}`}
            >
              Original Only
            </button>
          </div>

          <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400">
            <span>{video.width ?? 1280}×{video.height ?? 720}</span>
            <span>•</span>
            <span>{video.fps ? `${video.fps} FPS` : ''}</span>
          </div>
        </div>

        <div
          className={`grid gap-4 p-4 ${
            activePlayer === 'dual' ? 'lg:grid-cols-2' : 'grid-cols-1'
          }`}
        >
          {/* Left: Original Video with Farm Boundary Drawing Layer */}
          {(activePlayer === 'dual' || activePlayer === 'original') && (
            <div className="relative overflow-hidden rounded-xl bg-black">
              <div className="absolute left-3 top-3 z-10 rounded bg-slate-950/80 px-2 py-0.5 text-[11px] font-medium text-slate-300 backdrop-blur">
                Original Camera Trap Video
              </div>
              <video
                ref={originalVideoRef}
                src={videoFileUrl(video.video_id)}
                controls
                onPlay={handleOriginalPlay}
                onPause={handleOriginalPause}
                onSeeked={handleOriginalSeeked}
                className="w-full rounded-xl bg-black aspect-video object-contain"
              />
              {/* Overlay Canvas for Boundary Drawing */}
              <canvas
                ref={canvasRef}
                width={video.width || 640}
                height={video.height || 360}
                onClick={handleCanvasClick}
                className={`absolute inset-0 h-full w-full ${
                  isEditingBoundary
                    ? 'cursor-crosshair z-20 pointer-events-auto bg-black/20'
                    : 'pointer-events-none z-10'
                }`}
              />
            </div>
          )}

          {/* Right: AI Annotated Video */}
          {(activePlayer === 'dual' || activePlayer === 'annotated') && (
            <div className="relative overflow-hidden rounded-xl bg-black">
              <div className="absolute left-3 top-3 z-10 flex items-center gap-2 rounded bg-slate-950/80 px-2 py-0.5 text-[11px] font-medium text-emerald-400 backdrop-blur">
                <Sparkles size={12} /> AI Detections & Trajectory Overlay
              </div>
              {results?.annotated_video_url ? (
                <video
                  ref={annotatedVideoRef}
                  src={annotatedVideoUrl(video.video_id)}
                  controls
                  onPlay={handleAnnotatedPlay}
                  onPause={handleAnnotatedPause}
                  onSeeked={handleAnnotatedSeeked}
                  className="w-full rounded-xl bg-black aspect-video object-contain"
                />
              ) : (
                <div className="flex aspect-video w-full flex-col items-center justify-center p-6 text-center text-slate-500">
                  <FileVideo size={48} className="mb-2 text-slate-700" />
                  <p className="text-sm font-medium text-slate-400">Annotated Video Not Generated Yet</p>
                  <p className="mt-1 text-xs text-slate-600">
                    Click "Start AI Analysis" above to run MegaDetector and render the overlay video.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Analysis Results Metrics Bar */}
      {results && (
        <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <span className="text-xs text-slate-400">Total Animals Detected</span>
            <div className="mt-1 text-2xl font-bold text-white">{results.total_animals}</div>
            <p className="text-[11px] text-slate-500">Confidence: {(results.avg_detection_confidence * 100).toFixed(0)}%</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <span className="text-xs text-slate-400">Unique Tracks Mapped</span>
            <div className="mt-1 text-2xl font-bold text-white">{results.unique_tracks}</div>
            <p className="text-[11px] text-slate-500">Persistent IDs</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <span className="text-xs text-slate-400">Species Identified</span>
            <div className="mt-1 text-sm font-semibold text-emerald-400 capitalize truncate">
              {results.species_detected.join(', ') || 'None'}
            </div>
            <p className="text-[11px] text-slate-500">Classifier: {(results.avg_classification_confidence * 100).toFixed(0)}%</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <span className="text-xs text-slate-400">Highest Encounter Risk</span>
            <div className={`mt-1 text-xl font-bold ${riskBadgeColor(results.max_risk_level)}`}>
              {results.max_risk_level}
            </div>
            <p className="text-[11px] text-slate-500">Physical factor estimate</p>
          </div>
        </div>
      )}

      {/* Detailed Tabs: Tracks & Animals vs Risk Events */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="mb-6 flex border-b border-slate-800">
          <button
            type="button"
            onClick={() => setActiveTab('tracks')}
            className={`pb-3 text-sm font-semibold transition ${
              activeTab === 'tracks'
                ? 'border-b-2 border-emerald-400 text-emerald-400'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Tracked Wildlife & Trajectories ({tracks.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('events')}
            className={`ml-8 pb-3 text-sm font-semibold transition ${
              activeTab === 'events'
                ? 'border-b-2 border-emerald-400 text-emerald-400'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Chronological Risk Events ({riskEvents.length})
          </button>
        </div>

        {/* Tab Content: Tracks */}
        {activeTab === 'tracks' && (
          <div className="overflow-x-auto">
            {tracks.length === 0 ? (
              <p className="py-12 text-center text-sm text-slate-500">
                No tracks found. Launch analysis to detect and track wildlife.
              </p>
            ) : (
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
                    <th className="py-3 px-3">Track ID</th>
                    <th className="py-3 px-3">Species</th>
                    <th className="py-3 px-3">Direction</th>
                    <th className="py-3 px-3">Observable Behaviour</th>
                    <th className="py-3 px-3">Avg Speed</th>
                    <th className="py-3 px-3">Duration</th>
                    <th className="py-3 px-3">Risk Level</th>
                    <th className="py-3 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {tracks.map((t) => (
                    <tr key={t.track_id} className="hover:bg-slate-800/40">
                      <td className="py-3 px-3 font-mono font-bold text-white">#{t.track_id}</td>
                      <td className="py-3 px-3 font-medium text-emerald-300 capitalize">
                        {t.species.replace('_', ' ')}
                      </td>
                      <td className="py-3 px-3 font-medium text-slate-300">{t.direction}</td>
                      <td className="py-3 px-3">
                        <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-300">
                          {t.behavior}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono">{t.average_speed_px_sec} px/s</td>
                      <td className="py-3 px-3 font-mono">{t.duration_seconds}s</td>
                      <td className="py-3 px-3">
                        <span
                          className={`rounded px-2 py-0.5 text-[11px] font-bold ${riskBadgeColor(
                            t.risk_level,
                          )}`}
                        >
                          {t.risk_level} ({t.risk_score})
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          type="button"
                          onClick={() => setSelectedTrack(t)}
                          className="rounded bg-slate-800 px-2.5 py-1 text-slate-300 hover:text-white"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Tab Content: Risk Events */}
        {activeTab === 'events' && (
          <div className="space-y-3">
            {riskEvents.length === 0 ? (
              <p className="py-12 text-center text-sm text-slate-500">
                No risk events generated for this video.
              </p>
            ) : (
              riskEvents.map((evt) => (
                <div
                  key={evt.id}
                  className="flex flex-col justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4 sm:flex-row sm:items-center"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-white">{evt.event_code}</span>
                      <span className="font-medium text-emerald-300 capitalize">
                        {evt.species.replace('_', ' ')} #{evt.track_id}
                      </span>
                      <span
                        className={`rounded px-2 py-0.5 text-[10px] font-bold ${riskBadgeColor(
                          evt.risk_level,
                        )}`}
                      >
                        {evt.risk_level} · {evt.risk_score}/100
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Distance: <span className="font-mono text-white">{evt.distance_image_space} px</span> • Direction:{' '}
                      <span className="text-white">{evt.direction}</span> • Observable Behaviour:{' '}
                      <span className="text-white">{evt.behavior}</span>
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {evt.factors.map((f, i) => (
                        <span key={i} className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                          ✓ {f}
                        </span>
                      ))}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleSeekTo(evt.timestamp_sec)}
                    className="flex shrink-0 items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-semibold text-emerald-400 hover:bg-slate-700"
                  >
                    <Clock size={13} />
                    Seek ({evt.timestamp_sec.toFixed(1)}s)
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Animal Trajectory Inspector Modal */}
      {selectedTrack && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">
                  Animal #{selectedTrack.track_id} · {selectedTrack.species.replace('_', ' ').toUpperCase()}
                </h3>
                <p className="text-xs text-slate-400">Persistent Trajectory & Movement Profile</p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedTrack(null)}
                className="rounded-lg p-1 text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg bg-slate-800/60 p-3">
                <span className="text-slate-400">Duration</span>
                <p className="font-mono text-sm font-semibold text-white">{selectedTrack.duration_seconds}s</p>
              </div>
              <div className="rounded-lg bg-slate-800/60 p-3">
                <span className="text-slate-400">Average Pixel Speed</span>
                <p className="font-mono text-sm font-semibold text-white">{selectedTrack.average_speed_px_sec} px/s</p>
              </div>
              <div className="rounded-lg bg-slate-800/60 p-3">
                <span className="text-slate-400">Net Displacement</span>
                <p className="font-mono text-sm font-semibold text-white">{selectedTrack.total_displacement_px} px</p>
              </div>
              <div className="rounded-lg bg-slate-800/60 p-3">
                <span className="text-slate-400">Encounter Risk</span>
                <p className={`text-sm font-bold ${riskBadgeColor(selectedTrack.risk_level)}`}>
                  {selectedTrack.risk_level} ({selectedTrack.risk_score}/100)
                </p>
              </div>
            </div>

            <div className="mt-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Sample Trajectory Coordinates
              </h4>
              <div className="max-h-40 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950 p-2 font-mono text-[11px] text-slate-400">
                {selectedTrack.trajectory.slice(0, 10).map((pt, i) => (
                  <div key={i} className="flex justify-between py-0.5 border-b border-slate-900">
                    <span>T: {pt.timestamp_sec.toFixed(2)}s (F:{pt.frame_idx})</span>
                    <span>X: {pt.center[0].toFixed(0)}, Y: {pt.center[1].toFixed(0)}</span>
                    <span className="text-emerald-400">{pt.speed_px_sec.toFixed(1)} px/s</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-5 flex justify-end">
              <button
                type="button"
                onClick={() => {
                  handleSeekTo(selectedTrack.start_time)
                  setSelectedTrack(null)
                }}
                className="flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-400"
              >
                <Play size={13} />
                Jump to Animal in Video ({selectedTrack.start_time.toFixed(1)}s)
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
