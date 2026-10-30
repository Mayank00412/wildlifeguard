import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AxiosError } from 'axios'
import { Upload, FileVideo, AlertCircle, CheckCircle2 } from 'lucide-react'
import { fetchConfig, fetchVideos, uploadVideo, videoFileUrl } from '../services/api'
import type { PublicConfig, VideoMetadata, VideoUploadResponse } from '../types/api'

const DEFAULT_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv']

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function UploadPage() {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [config, setConfig] = useState<PublicConfig | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<VideoUploadResponse | null>(null)
  const [recent, setRecent] = useState<VideoMetadata[]>([])
  const [dragOver, setDragOver] = useState(false)

  const allowed = config?.allowed_extensions ?? DEFAULT_EXTENSIONS
  const maxMb = config?.max_video_size_mb ?? 250
  const accept = useMemo(() => allowed.join(','), [allowed])

  useEffect(() => {
    void fetchConfig().then(setConfig).catch(() => undefined)
    void fetchVideos().then(setRecent).catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  function validate(next: File): string | null {
    const ext = `.${next.name.split('.').pop()?.toLowerCase() ?? ''}`
    if (!allowed.includes(ext)) {
      return `Unsupported format. Allowed: ${allowed.join(', ')}`
    }
    if (next.size > maxMb * 1024 * 1024) {
      return `File is larger than ${maxMb} MB.`
    }
    if (next.size === 0) {
      return 'The selected file is empty.'
    }
    return null
  }

  function choose(next: File | null) {
    setResult(null)
    setProgress(0)
    if (!next) {
      setFile(null)
      setError(null)
      return
    }
    const message = validate(next)
    if (message) {
      setFile(null)
      setError(message)
      return
    }
    setError(null)
    setFile(next)
  }

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setError(null)
    setProgress(0)
    try {
      const payload = await uploadVideo(file, setProgress)
      setResult(payload)
      setRecent(await fetchVideos())
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: any }>
      let message = 'Upload failed. Check the backend and try again.'
      if (axiosError.response?.data?.detail) {
        const detail = axiosError.response.data.detail
        if (typeof detail === 'string') {
          message = detail
        } else if (Array.isArray(detail)) {
          message = detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ')
        } else {
          message = JSON.stringify(detail)
        }
      } else if (axiosError.response?.status) {
        message = `Server error HTTP ${axiosError.response.status}: ${axiosError.response.statusText || 'Upload failed'}`
      } else if (axiosError.message) {
        message = `${axiosError.message}. Make sure the FastAPI backend is running on http://127.0.0.1:8000.`
      }
      setError(message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-white">Upload wildlife video</h1>
        <p className="mt-2 max-w-2xl text-slate-400">
          Drop a camera-trap recording. Files are stored with a generated ID; original names cannot
          traverse directories. Analysis starts only after a successful upload.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="space-y-4">
          <button
            type="button"
            onDragOver={(event) => {
              event.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(event) => {
              event.preventDefault()
              setDragOver(false)
              choose(event.dataTransfer.files[0] ?? null)
            }}
            onClick={() => inputRef.current?.click()}
            className={`w-full rounded-2xl border-2 border-dashed px-6 py-16 text-center transition ${
              dragOver
                ? 'border-emerald-400 bg-emerald-500/10'
                : 'border-slate-700 bg-slate-900/60 hover:border-slate-500'
            }`}
          >
            <Upload className="mx-auto mb-4 text-emerald-400" />
            <p className="text-lg font-medium text-white">Drag and drop a video here</p>
            <p className="mt-2 text-sm text-slate-400">or click to browse. MP4, AVI, MOV, MKV · max {maxMb} MB</p>
          </button>
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            className="hidden"
            onChange={(event) => choose(event.target.files?.[0] ?? null)}
          />

          {file && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <div className="flex items-start gap-3">
                <FileVideo className="mt-1 text-emerald-400" size={20} />
                <div>
                  <p className="font-medium text-white">{file.name}</p>
                  <p className="text-sm text-slate-400">{formatBytes(file.size)}</p>
                </div>
              </div>
              {previewUrl && (
                <video className="mt-4 w-full rounded-xl bg-black" src={previewUrl} controls />
              )}
              {uploading && (
                <div className="mt-4">
                  <div className="mb-1 flex justify-between text-xs text-slate-400">
                    <span>Uploading…</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                    <div className="h-full bg-emerald-400" style={{ width: `${progress}%` }} />
                  </div>
                </div>
              )}
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={uploading}
                  onClick={() => void handleUpload()}
                  className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
                >
                  {uploading ? 'Uploading…' : 'Upload video'}
                </button>
                <button
                  type="button"
                  disabled={!result}
                  onClick={() => result && navigate(`/analysis/${result.video_id}`)}
                  className="rounded-lg bg-emerald-500/20 border border-emerald-500/40 px-4 py-2 text-sm font-semibold text-emerald-300 hover:bg-emerald-500/30 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Start Analysis →
                </button>
              </div>
            </div>
          )}

          {error && (
            <p className="flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              <AlertCircle size={16} /> {error}
            </p>
          )}
          {result && (
            <div className="flex items-center justify-between rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-sm text-emerald-100">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={18} className="text-emerald-400" />
                <span>Uploaded {result.filename}</span>
              </div>
              <button
                type="button"
                onClick={() => navigate(`/analysis/${result.video_id}`)}
                className="rounded-lg bg-emerald-500 px-3 py-1 text-xs font-semibold text-slate-950 hover:bg-emerald-400"
              >
                Proceed to Analysis
              </button>
            </div>
          )}
        </section>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <h2 className="font-medium text-white">Validation</h2>
            <ul className="mt-3 space-y-2 text-sm text-slate-400">
              <li>Extensions: {allowed.join(', ')}</li>
              <li>Size limit: {maxMb} MB (from server config)</li>
              <li>Stored as UUID filename under /videos</li>
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <h2 className="font-medium text-white">Recent uploads</h2>
            {recent.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">No videos yet.</p>
            ) : (
              <ul className="mt-3 space-y-3">
                {recent.slice(0, 8).map((video) => (
                  <li key={video.video_id} className="text-sm border-b border-slate-800/60 pb-2">
                    <p className="text-slate-200 font-medium truncate">{video.filename}</p>
                    <div className="mt-1 flex items-center justify-between text-xs">
                      <Link to={`/analysis/${video.video_id}`} className="text-emerald-400 hover:underline">
                        Open Analysis →
                      </Link>
                      <a className="text-slate-500 hover:underline" href={videoFileUrl(video.video_id)}>
                        Raw File
                      </a>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>
      </div>
    </main>
  )
}
