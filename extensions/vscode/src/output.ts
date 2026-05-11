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

  scanResult(req: ScanRequest, resp: ScanResponse): void {
    this.channel.appendLine(
      `[${ts()}] SCAN  action=${resp.action} risk=${resp.risk_level} detections=${resp.detections.length} ms=${resp.scan_duration_ms}`
    );
    this.channel.appendLine(`        request : ${JSON.stringify(req)}`);
    this.channel.appendLine(`        response: ${JSON.stringify(resp)}`);
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
