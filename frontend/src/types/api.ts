export type HealthResponse = {
  status: string
  service: string
}

export type PublicConfig = {
  max_video_size_mb: number
  allowed_extensions: string[]
  demo_mode: boolean
  process_fps: number
  model_device: string
  detection_model_name: string
  detection_confidence: number
  classification_confidence: number
  risk_low_max: number
  risk_moderate_max: number
  risk_high_max: number
}

export type VideoUploadResponse = {
  video_id: string
  filename: string
  status: string
}

export type VideoMetadata = {
  video_id: string
  filename: string
  stored_filename: string
  content_type: string | null
  size_bytes: number
  status: string
  fps?: number | null
  width?: number | null
  height?: number | null
  duration_seconds?: number | null
  total_frames?: number | null
  processed_fps?: number | null
  thumbnail_url?: string | null
  created_at: string
}

export type FarmBoundary = {
  video_id: string
  polygon: [number, number][]
}

export type AnalysisStatusResponse = {
  analysis_id: string
  video_id: string
  status: 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  current_stage: string
  progress_percent: number
  error_message?: string | null
}

export type TrajectoryPoint = {
  frame_idx: number
  timestamp_sec: number
  bbox: [number, number, number, number]
  center: [number, number]
  speed_px_sec: number
}

export type TrackResponse = {
  track_id: number
  species: string
  detection_confidence: number
  classification_confidence: number
  duration_seconds: number
  start_time: number
  end_time: number
  average_speed_px_sec: number
  max_speed_px_sec: number
  total_displacement_px: number
  direction: string
  behavior: string
  risk_score: number
  risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL'
  trajectory: TrajectoryPoint[]
}

export type RiskEventResponse = {
  id: string
  event_code: string
  track_id: number
  species: string
  timestamp_sec: number
  risk_score: number
  risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL'
  factors: string[]
  confidence: number
  distance_image_space: number
  direction: string
  behavior: string
}

export type AnalysisResultsResponse = {
  analysis_id: string
  video_id: string
  status: string
  total_animals: number
  unique_tracks: number
  species_detected: string[]
  avg_detection_confidence: number
  avg_classification_confidence: number
  behavior_distribution: Record<string, number>
  risk_distribution: Record<string, number>
  max_risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL'
  annotated_video_url?: string | null
  created_at: string
  completed_at?: string | null
}

export type GlobalTrackResponse = TrackResponse & {
  video_id: string
  analysis_id: string
  video_filename: string
}

export type GlobalRiskEventResponse = RiskEventResponse & {
  video_id: string
  analysis_id: string
  video_filename: string
}

export type AnalyticsOverviewResponse = {
  total_videos: number
  total_analyses: number
  total_animals_detected: number
  total_unique_tracks: number
  high_risk_events_count: number
  species_breakdown: Record<string, number>
  risk_level_breakdown: Record<string, number>
  behavior_breakdown: Record<string, number>
}
