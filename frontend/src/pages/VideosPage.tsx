import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileVideo, Play, PlusCircle, Calendar, HardDrive, Clock, Trash2 } from 'lucide-react'
import { deleteVideo, fetchVideos, videoFileUrl, videoThumbnailUrl } from '../services/api'
import type { VideoMetadata } from '../types/api'

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function VideosPage() {
  const [videos, setVideos] = useState<VideoMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    void fetchVideos().then((data) => {
      setVideos(data)
      setLoading(false)
    })
  }, [])

  async function handleDelete(videoId: string, filename: string) {
    const confirmed = window.confirm(`Are you sure you want to delete "${filename}" and all its analysis results?`)
    if (!confirmed) return

    setDeletingId(videoId)
    try {
      await deleteVideo(videoId)
      setVideos((prev) => prev.filter((v) => v.video_id !== videoId))
    } catch (err) {
      alert('Failed to delete video.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white md:text-3xl">Camera-Trap Recordings</h1>
          <p className="mt-1 text-sm text-slate-400">
            All stored wildlife videos. Click on any video to draw farm boundaries and run AI analysis.
          </p>
        </div>
        <Link
          to="/upload"
          className="flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-slate-950 shadow-md transition hover:bg-emerald-400"
        >
          <PlusCircle size={18} />
          Upload Video
        </Link>
      </div>

      {loading ? (
        <div className="py-20 text-center text-slate-500">Loading videos…</div>
      ) : videos.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-800 py-16 text-center">
          <FileVideo className="mx-auto mb-3 text-slate-600" size={42} />
          <p className="text-base font-medium text-white">No videos uploaded yet</p>
          <p className="mt-1 text-xs text-slate-500">Drop an MP4, AVI, MOV, or MKV file to get started.</p>
          <Link
            to="/upload"
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-400"
          >
            Upload Video
          </Link>
        </div>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {videos.map((video) => (
            <div
              key={video.video_id}
              className="flex flex-col justify-between overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm transition hover:border-slate-700"
            >
              <div>
                <div className="relative mb-4 aspect-video w-full overflow-hidden rounded-xl bg-black">
                  {video.thumbnail_url ? (
                    <img
                      src={videoThumbnailUrl(video.video_id)}
                      alt={video.filename}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-slate-700">
                      <FileVideo size={40} />
                    </div>
                  )}
                  {video.duration_seconds && (
                    <span className="absolute bottom-2.5 right-2.5 rounded-md bg-black/85 px-2 py-0.5 text-xs font-mono text-white">
                      {video.duration_seconds}s
                    </span>
                  )}
                </div>

                <h3 className="truncate font-medium text-white" title={video.filename}>
                  {video.filename}
                </h3>
                <p className="mt-1 font-mono text-[11px] text-slate-500">{video.video_id}</p>

                <div className="mt-4 space-y-1.5 text-xs text-slate-400">
                  <div className="flex items-center gap-2">
                    <Clock size={14} className="text-slate-500" />
                    <span>
                      {video.fps ? `${video.fps} FPS` : 'Probing FPS…'} • {video.width ? `${video.width}×${video.height}` : 'Resolution'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <HardDrive size={14} className="text-slate-500" />
                    <span>{formatBytes(video.size_bytes)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar size={14} className="text-slate-500" />
                    <span>{new Date(video.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-slate-800/80 pt-4">
                <div className="flex items-center gap-3">
                  <a
                    href={videoFileUrl(video.video_id)}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-slate-400 hover:text-white"
                  >
                    Raw Video
                  </a>
                  <button
                    type="button"
                    disabled={deletingId === video.video_id}
                    onClick={() => void handleDelete(video.video_id, video.filename)}
                    className="text-slate-500 transition hover:text-rose-400 disabled:opacity-40"
                    title="Delete video"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <Link
                  to={`/analysis/${video.video_id}`}
                  className="flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3.5 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400"
                >
                  <Play size={14} />
                  Analyze
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
