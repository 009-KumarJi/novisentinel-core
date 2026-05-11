import * as vscode from "vscode";
import { NoviSentinelClient } from "./api-client";
import { logger } from "./output";

const ONBOARDED_KEY = "novisentinel.onboarded";
const PUBLIC_API_URL = "https://api-play.novisentinel.dev";
const PUBLIC_API_KEY = "play-public";

export async function runOnboardingIfNeeded(
  context: vscode.ExtensionContext,
  client: NoviSentinelClient
): Promise<void> {
  if (context.globalState.get(ONBOARDED_KEY) === true) {
    return;
  }

  const choice = await vscode.window.showInformationMessage(
    "Welcome to NoviSentinel! Where is your API running?",
    "Use local Docker — http://localhost:8000",
    "Use hosted playground",
    "I'll configure later"
  );

  switch (choice) {
    case "Use local Docker — http://localhost:8000": {
      const healthy = await client.health();
      if (healthy) {
        vscode.window.showInformationMessage("NoviSentinel: Connected. Try scanning something!");
        logger.info("Onboarding: connected to local Docker.");
      } else {
        vscode.window.showWarningMessage(
          "Couldn't reach localhost:8000. Run `docker compose up` from your NoviSentinel folder, then run NoviSentinel: Test Connection.",
          "Open docs"
        ).then((btn) => {
          if (btn === "Open docs") {
            vscode.env.openExternal(
              vscode.Uri.parse("https://github.com/009-KumarJi/novi-sentinel#quickstart")
            );
          }
        });
        logger.warn("Onboarding: local Docker unreachable.");
      }
      break;
    }

    case "Use hosted playground": {
      const cfg = vscode.workspace.getConfiguration("novisentinel");
      await cfg.update("apiUrl", PUBLIC_API_URL, vscode.ConfigurationTarget.Global);
      await context.secrets.store("novisentinel.apiKey", PUBLIC_API_KEY);
      vscode.window.showInformationMessage(
        "Connected to the public playground. Note: rate limits apply."
      );
      logger.info("Onboarding: using public playground.");
      break;
    }

    default:
      logger.info("Onboarding: deferred by user.");
  }

  await context.globalState.update(ONBOARDED_KEY, true);
}

export async function testConnection(client: NoviSentinelClient): Promise<void> {
  const healthy = await client.health();
  if (healthy) {
    vscode.window.showInformationMessage("NoviSentinel: API is reachable and healthy.");
  } else {
    vscode.window.showErrorMessage(
      "NoviSentinel: Cannot reach the API. Check your API URL in settings."
    );
  }
}
