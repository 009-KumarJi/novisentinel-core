export interface Detection {
  detector: string;
  type: string;
  text: string;
  redacted: string;
  start: number;
  end: number;
  confidence: number;
  severity: "critical" | "high" | "medium" | "low";
}

export interface ScanResponse {
  scan_id: string;
  safe: boolean;
  risk_level: "critical" | "high" | "medium" | "low" | "none";
  action: "block" | "warn" | "redact" | "allow";
  detections: Detection[];
  redacted_text: string;
  original_length: number;
  scan_duration_ms: number;
}

export interface ScanRequest {
  text: string;
  context?: "input" | "output";
}
