import * as vscode from "vscode";
import { NoviSentinelClient } from "./api-client";
import { logger } from "./output";
import { StatusBar } from "./status-bar";
import { runOnboardingIfNeeded, testConnection } from "./onboarding";
import { registerChatParticipant } from "./chat/participant";
import { registerScanSelectionCommand } from "./commands/scan-selection";
import { registerScanClipboardCommand } from "./commands/scan-clipboard";

async function getApiKey(context: vscode.ExtensionContext): Promise<string> {
  const stored = await context.secrets.get("novisentinel.apiKey");
  if (stored) return stored;
  const fromEnv = process.env["NOVISENTINEL_API_KEY"];
  if (fromEnv) return fromEnv;
  return "dev-master-key";
}

function buildClient(context: vscode.ExtensionContext): NoviSentinelClient {
  const cfg = vscode.workspace.getConfiguration("novisentinel");
  const apiUrl = cfg.get<string>("apiUrl", "http://localhost:8000");
  // ApiKey is read async on first use, but client is constructed synchronously.
  // We pass a placeholder; getApiKey() is called inside commands that need it.
  return new NoviSentinelClient(apiUrl, "placeholder");
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  logger.info("NoviSentinel activated.");

  const apiKey = await getApiKey(context);
  const cfg = vscode.workspace.getConfiguration("novisentinel");
  const apiUrl = cfg.get<string>("apiUrl", "http://localhost:8000");
  const client = new NoviSentinelClient(apiUrl, apiKey);

  // --- Diagnostic collection (shared across commands) ---
  const diagnosticCollection = vscode.languages.createDiagnosticCollection("novisentinel");
  context.subscriptions.push(diagnosticCollection);

  // --- setApiKey command (F-403) ---
  context.subscriptions.push(
    vscode.commands.registerCommand("novisentinel.setApiKey", async () => {
      const key = await vscode.window.showInputBox({
        prompt: "Enter your NoviSentinel API key",
        password: true,
        ignoreFocusOut: true,
      });
      if (key) {
        await context.secrets.store("novisentinel.apiKey", key);
        vscode.window.showInformationMessage("NoviSentinel: API key saved.");
        logger.info("API key updated via command.");
      }
    })
  );

  // --- openSettings command ---
  context.subscriptions.push(
    vscode.commands.registerCommand("novisentinel.openSettings", () => {
      vscode.commands.executeCommand(
        "workbench.action.openSettings",
        "@ext:novisentinel.novisentinel-vscode"
      );
    })
  );

  // --- testConnection command (F-409 T5) ---
  context.subscriptions.push(
    vscode.commands.registerCommand("novisentinel.testConnection", () => testConnection(client))
  );

  // --- Status bar (F-404) ---
  const statusBar = new StatusBar(client);
  statusBar.start();
  context.subscriptions.push({ dispose: () => statusBar.dispose() });

  // --- Scan commands (F-406, F-407) ---
  registerScanSelectionCommand(context, client, diagnosticCollection);
  registerScanClipboardCommand(context, client);

  // --- Chat participant (F-408) ---
  registerChatParticipant(context, client);

  // --- First-run onboarding (F-409) ---
  await runOnboardingIfNeeded(context, client);

  // Prompt for key if none is configured
  const hasKey = !!(await context.secrets.get("novisentinel.apiKey"));
  if (!hasKey && !process.env["NOVISENTINEL_API_KEY"]) {
    vscode.window
      .showInformationMessage("NoviSentinel: No API key configured.", "Set API Key")
      .then((btn) => btn && vscode.commands.executeCommand("novisentinel.setApiKey"));
  }
}

export function deactivate(): void {
  logger.info("NoviSentinel deactivated.");
  logger.dispose();
}
