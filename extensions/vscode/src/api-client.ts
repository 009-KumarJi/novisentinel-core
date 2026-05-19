import * as vscode from "vscode";
import { NoviSentinelError } from "./errors";
import { logger } from "./output";
import type { ScanRequest, ScanResponse } from "./types";

export class NoviSentinelClient {
  constructor(
    private readonly apiUrl: string,
    private readonly apiKey: string,
    private readonly timeoutMs: number = 30_000
  ) {}

  async scan(text: string, context?: "input" | "output"): Promise<ScanResponse> {
    const req: ScanRequest = { text, context };
    // Re-read settings on every call so changes apply without reload.
    const cfg = vscode.workspace.getConfiguration("novisentinel");
    const url = `${cfg.get<string>("apiUrl", this.apiUrl).replace(/\/$/, "")}/v1/scan`;
    const scanCtx = context ?? (cfg.get<string>("scanContext", "input") as "input" | "output");

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    let resp: Response;
    try {
      resp = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
        },
        body: JSON.stringify({ text, context: scanCtx }),
        signal: controller.signal,
      });
    } catch (err: unknown) {
      clearTimeout(timer);
      const msg = err instanceof Error ? err.message : String(err);
      throw new NoviSentinelError(`Cannot reach NoviSentinel at ${url}: ${msg}`);
    }
    clearTimeout(timer);

    if (!resp.ok) {
      const retryAfter = resp.headers.get("retry-after");
      switch (resp.status) {
        case 401:
        case 403:
          throw new NoviSentinelError("Missing or invalid API key. Run: NoviSentinel: Set API Key");
        case 413:
          throw new NoviSentinelError("Selection is too large for the configured server limit.");
        case 429:
          throw new NoviSentinelError(
            `Rate limited. Try again in ${retryAfter ?? "a few"} seconds.`
          );
        default:
          throw new NoviSentinelError(`NoviSentinel returned ${resp.status}`);
      }
    }

    const data = (await resp.json()) as ScanResponse;
    logger.scanResult(req, data);
    return data;
  }

  async health(): Promise<boolean> {
    const cfg = vscode.workspace.getConfiguration("novisentinel");
    const base = cfg.get<string>("apiUrl", this.apiUrl).replace(/\/$/, "");
    try {
      const resp = await fetch(`${base}/health`, { signal: AbortSignal.timeout(5_000) });
      return resp.ok;
    } catch {
      return false;
    }
  }
}
