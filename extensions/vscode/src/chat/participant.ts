import * as vscode from "vscode";
import { NoviSentinelClient } from "../api-client";
import { logger } from "../output";
import { explain } from "./explanation";
import type { ScanResponse } from "../types";

function actionEmoji(action: ScanResponse["action"]): string {
  return { block: "🛑", warn: "⚠️", redact: "✏️", allow: "✅" }[action];
}

function severityBadge(s: string): string {
  return { critical: "🔴", high: "🟠", medium: "🟡", low: "🔵", none: "⚪" }[s] ?? s;
}

export function registerChatParticipant(
  context: vscode.ExtensionContext,
  client: NoviSentinelClient
): void {
  const participant = vscode.chat.createChatParticipant(
    "novisentinel.scan",
    async (request, _ctx, response, token) => {
      if (token.isCancellationRequested) return;

      let result: ScanResponse;
      try {
        result = await client.scan(request.prompt, "input");
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        response.markdown(
          `**NoviSentinel error:** ${msg}\n\nMake sure the API is running — \`docker compose up\``
        );
        logger.error(`Chat participant error: ${msg}`);
        return;
      }

      // Header line
      response.markdown(
        `**Action: ${result.action.toUpperCase()}** ${actionEmoji(result.action)} · ` +
        `risk: ${severityBadge(result.risk_level)} ${result.risk_level} · ` +
        `${result.detections.length} detection${result.detections.length !== 1 ? "s" : ""} · ` +
        `${result.scan_duration_ms}ms\n\n`
      );

      // Detections table
      if (result.detections.length > 0) {
        response.markdown(
          "| Detector | Type | Confidence | Severity | Preview |\n" +
          "|----------|------|-----------|----------|---------|\n" +
          result.detections
            .map(
              (d) =>
                `| ${d.detector} | ${d.type} | ${(d.confidence * 100).toFixed(0)}% | ${d.severity} | \`${d.text.slice(0, 40)}\` |`
            )
            .join("\n") +
          "\n\n"
        );

        // Explanation per detection
        response.markdown("**Why these were flagged:**\n\n");
        for (const d of result.detections) {
          response.markdown(`- **${d.detector}/${d.type}**: ${explain(d)}\n`);
        }
      }

      // Redacted version
      if (result.redacted_text !== request.prompt) {
        response.markdown("\n\n**Redacted version:**\n\n```\n" + result.redacted_text + "\n```\n");
      }

      // Follow-up suggestion on block
      if (result.action === "block") {
        response.button({ title: "How can I rephrase this safely?", command: "" });
      }
    }
  );

  participant.followupProvider = {
    provideFollowups(result, _ctx, _token) {
      return [{ prompt: "How can I rephrase this prompt to avoid the detection?", label: "Rephrase safely" }];
    },
  };

  context.subscriptions.push(participant);
}
