export interface StatsResponse {
  total_scans: number
  flagged_scans?: number
  flag_rate?: number
  blocked?: number
  redacted?: number
  avg_scan_ms?: number
  by_risk_level?: Record<string, number>
}

export interface LogEntry {
  scan_id: string
  context: string | null
  safe: boolean
  risk_level: string
  action: string
  pii_count: number
  injection_count: number
  secrets_count: number
  toxicity_count: number
  total_detections: number
  scan_duration_ms: number
  created_at: string
}

export interface ApiKeyRecord {
  key_id: string
  prefix: string
  name: string
  owner: string
  is_active: boolean
  created_at: string
}

export interface CreateKeyResponse {
  key: string
  key_id: string
  prefix: string
  message: string
}
