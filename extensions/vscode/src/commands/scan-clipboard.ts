import * as vscode from "vscode";
import { NoviSentinelClient } from "../api-client";
import { logger } from "../output";
import { NoviSentinelError } from "../errors";

export function registerScanClipboardCommand(
  context: vscode.ExtensionContext,
  client: NoviSentinelClient
): void {
  const cmd = vscode.commands.registerCommand("novisentinel.scanClipboard", async () => {
    const text = await vscode.env.clipboard.readText();

    if (!text.trim()) {
      vscode.window.showInformationMessage("NoviSentinel: Clipboard is empty.");
      return;
    }

    const cfg = vscode.workspace.getConfiguration("novisentinel");
    const scanContext = cfg.get<"input" | "output">("scanContext", "input");

    try {
      const result = await client.scan(text, scanContext);
      const n = result.detections.length;

      switch (result.action) {
        case "allow":
          vscode.window.showInformationMessage("✓ Clipboard is clean — no detections.");
          break;

        case "warn":
          vscode.window.showWarningMessage(
            `⚠ Warning — ${n} detection${n !== 1 ? "s" : ""} in clipboard`,
            "View details"
          ).then((btn) => btn && logger.show());
          break;

        case "redact":
          vscode.window.showInformationMessage(
            `✏ PII redacted from clipboard`,
            "Copy redacted text",
            "View details"
          ).then((btn) => {
            if (btn === "Copy redacted text") {
              vscode.env.clipboard.writeText(result.redacted_text);
              vscode.window.showInformationMessage("Redacted text copied to clipboard.");
            } else if (btn === "View details") {
              logger.show();
            }
          });
          break;

        case "block":
          vscode.window.showErrorMessage(
            `🛑 Blocked — ${n} detection${n !== 1 ? "s" : ""} in clipboard (risk: ${result.risk_level})`,
            "View details"
          ).then((btn) => btn && logger.show());
          break;
      }
    } catch (err) {
      const msg = err instanceof NoviSentinelError ? err.message : String(err);
      logger.error(`scanClipboard: ${msg}`);
      vscode.window.showErrorMessage(`NoviSentinel: ${msg}`);
    }
  });

  context.subscriptions.push(cmd);
}
