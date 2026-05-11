import * as vscode from "vscode";
import { NoviSentinelClient } from "../api-client";
import { logger } from "../output";
import { NoviSentinelError } from "../errors";
import type { ScanResponse } from "../types";

const severityToDiagnostic: Record<string, vscode.DiagnosticSeverity> = {
  critical: vscode.DiagnosticSeverity.Error,
  high: vscode.DiagnosticSeverity.Error,
  medium: vscode.DiagnosticSeverity.Warning,
  low: vscode.DiagnosticSeverity.Information,
};

function notificationForResult(
  result: ScanResponse,
  diagnosticCollection: vscode.DiagnosticCollection,
  editor: vscode.TextEditor,
  selectionRange: vscode.Range
): void {
  const n = result.detections.length;

  // Render diagnostics
  const diagnostics: vscode.Diagnostic[] = result.detections.map((d) => {
    const severity = severityToDiagnostic[d.severity] ?? vscode.DiagnosticSeverity.Warning;
    const diag = new vscode.Diagnostic(selectionRange, `NoviSentinel [${d.detector}/${d.type}]: ${d.text}`, severity);
    diag.source = "NoviSentinel";
    return diag;
  });
  diagnosticCollection.set(editor.document.uri, diagnostics);

  switch (result.action) {
    case "allow":
      vscode.window.showInformationMessage("✓ Clean — no detections.");
      break;

    case "warn":
      vscode.window.showWarningMessage(
        `⚠ Warning — ${n} detection${n !== 1 ? "s" : ""}`,
        "View details"
      ).then((btn) => btn && logger.show());
      break;

    case "redact":
      vscode.window.showInformationMessage(
        `✏ Redacted — ${n} detection${n !== 1 ? "s" : ""}`,
        "Replace selection",
        "View details"
      ).then((btn) => {
        if (btn === "Replace selection") {
          editor.edit((eb) => eb.replace(selectionRange, result.redacted_text));
        } else if (btn === "View details") {
          logger.show();
        }
      });
      break;

    case "block":
      vscode.window.showErrorMessage(
        `🛑 Blocked — ${n} detection${n !== 1 ? "s" : ""} (risk: ${result.risk_level})`,
        "View details"
      ).then((btn) => btn && logger.show());
      break;
  }
}

export function registerScanSelectionCommand(
  context: vscode.ExtensionContext,
  client: NoviSentinelClient,
  diagnosticCollection: vscode.DiagnosticCollection
): void {
  const cmd = vscode.commands.registerCommand("novisentinel.scanSelection", async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;

    const selection = editor.selection;
    if (selection.isEmpty) {
      vscode.window.showInformationMessage("NoviSentinel: Select some text first.");
      return;
    }

    const text = editor.document.getText(selection);
    const cfg = vscode.workspace.getConfiguration("novisentinel");
    const scanContext = cfg.get<"input" | "output">("scanContext", "input");

    try {
      const result = await client.scan(text, scanContext);
      notificationForResult(result, diagnosticCollection, editor, selection);
    } catch (err) {
      const msg = err instanceof NoviSentinelError ? err.message : String(err);
      logger.error(`scanSelection: ${msg}`);
      vscode.window.showErrorMessage(`NoviSentinel: ${msg}`);
    }
  });

  context.subscriptions.push(cmd);
}
