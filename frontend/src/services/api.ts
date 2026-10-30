import axios from 'axios'
import type {
  AnalysisResultsResponse,
  AnalysisStatusResponse,
  AnalyticsOverviewResponse,
  FarmBoundary,
  GlobalRiskEventResponse,
  GlobalTrackResponse,
  HealthResponse,
  PublicConfig,
  RiskEventResponse,
  TrackResponse,
  VideoMetadata,
  VideoUploadResponse,
} from '../types/api'

export const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await api.get<HealthResponse>('/health')
  return response.data
}

export async function fetchConfig(): Promise<PublicConfig> {
  const response = await api.get<PublicConfig>('/config')
  return response.data
}

export async function uploadVideo(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<VideoUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const response = await api.post<VideoUploadResponse>('/videos/upload', form, {
    onUploadProgress: (event) => {
      if (!onProgress || !event.total) return
      onProgress(Math.round((event.loaded / event.total) * 100))
    },
  })
  return response.data
}

export async function fetchVideos(): Promise<VideoMetadata[]> {
  const response = await api.get<VideoMetadata[]>('/videos')
  return response.data
}

export async function fetchVideo(videoId: string): Promise<VideoMetadata> {
  const response = await api.get<VideoMetadata>(`/videos/${videoId}`)
  return response.data
}

export async function deleteVideo(videoId: string): Promise<{ status: string; video_id: string }> {
  const response = await api.delete<{ status: string; video_id: string }>(`/videos/${videoId}`)
  return response.data
}

export function videoFileUrl(videoId: string): string {
  return `/api/videos/${videoId}/file`
}

export function videoThumbnailUrl(videoId: string): string {
  return `/api/videos/${videoId}/thumbnail`
}

export async function fetchFarmBoundary(videoId: string): Promise<FarmBoundary> {
  const response = await api.get<FarmBoundary>(`/videos/${videoId}/boundary`)
  return response.data
}

export async function saveFarmBoundary(
  videoId: string,
  polygon: [number, number][],
): Promise<FarmBoundary> {
  const response = await api.post<FarmBoundary>(`/videos/${videoId}/boundary`, { polygon })
  return response.data
}

export async function startAnalysis(
  videoId: string,
  farmBoundary?: [number, number][],
  processFps?: number,
): Promise<AnalysisStatusResponse> {
  const response = await api.post<AnalysisStatusResponse>(`/analysis/${videoId}/start`, {
    farm_boundary: farmBoundary,
    process_fps: processFps,
  })
  return response.data
}

export async function fetchAnalysisStatus(videoId: string): Promise<AnalysisStatusResponse> {
  const response = await api.get<AnalysisStatusResponse>(`/analysis/${videoId}/status`)
  return response.data
}

export async function fetchAnalysisResults(videoId: string): Promise<AnalysisResultsResponse> {
  const response = await api.get<AnalysisResultsResponse>(`/analysis/${videoId}/results`)
  return response.data
}

export async function fetchAnalysisTracks(videoId: string): Promise<TrackResponse[]> {
  const response = await api.get<TrackResponse[]>(`/analysis/${videoId}/tracks`)
  return response.data
}

export async function fetchAnalysisRiskEvents(videoId: string): Promise<RiskEventResponse[]> {
  const response = await api.get<RiskEventResponse[]>(`/analysis/${videoId}/risk-events`)
  return response.data
}

export function annotatedVideoUrl(videoId: string): string {
  return `/api/analysis/${videoId}/annotated-video`
}

export function analysisExportUrl(videoId: string, format: 'json' | 'csv' = 'json'): string {
  return `/api/analysis/${videoId}/export?format=${format}`
}

export async function fetchAnalyticsOverview(): Promise<AnalyticsOverviewResponse> {
  const response = await api.get<AnalyticsOverviewResponse>('/analytics/overview')
  return response.data
}

export async function fetchAnimals(): Promise<GlobalTrackResponse[]> {
  const response = await api.get<GlobalTrackResponse[]>('/analytics/animals')
  return response.data
}

export async function fetchRiskEvents(): Promise<GlobalRiskEventResponse[]> {
  const response = await api.get<GlobalRiskEventResponse[]>('/analytics/risk-events')
  return response.data
}
