import * as vscode from "vscode";
import type { ScanRequest, ScanResponse } from "./types";

class Logger {
  private channel: vscode.OutputChannel;

  constructor() {
    this.channel = vscode.window.createOutputChannel("NoviSentinel");
  }

  info(msg: string): void {
    this.channel.appendLine(`[${ts()}] INFO  ${msg}`);
  }

  warn(msg: string): void {
    this.channel.appendLine(`[${ts()}] WARN  ${msg}`);
  }

  error(msg: string): void {
    this.channel.appendLine(`[${ts()}] ERROR ${msg}`);
  }

  /**
   * Log a scan result without ever writing the raw text or matched spans
   * to the output panel — that panel is sent in VSCode error reports if
   * the user opts in to telemetry, and we don't want to leak the PII a
   * user just scanned.
   */
  scanResult(req: ScanRequest, resp: ScanResponse): void {
    const summary = {
      action: resp.action,
      risk: resp.risk_level,
      detections: resp.detections.map((d) => ({
        detector: d.detector,
        type: d.type,
        severity: d.severity,
        confidence: d.confidence,
      })),
      duration_ms: resp.scan_duration_ms,
      original_length: resp.original_length,
      context: req.context ?? null,
    };
    this.channel.appendLine(
      `[${ts()}] SCAN  ${JSON.stringify(summary)}`
    );
  }

  show(): void {
    this.channel.show(true);
  }

  dispose(): void {
    this.channel.dispose();
  }
}

function ts(): string {
  return new Date().toISOString();
}

export const logger = new Logger();
