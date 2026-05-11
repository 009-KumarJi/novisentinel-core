import * as vscode from "vscode";
import { NoviSentinelClient } from "./api-client";

type State = "live" | "degraded" | "unreachable";

export class StatusBar {
  private readonly item: vscode.StatusBarItem;
  private interval: ReturnType<typeof setInterval> | undefined;

  constructor(private readonly client: NoviSentinelClient) {
    this.item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    this.item.command = "novisentinel.openSettings";
    this.item.show();
  }

  start(): void {
    this.check();
    this.scheduleInterval();

    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("novisentinel.healthPollSeconds")) {
        this.scheduleInterval();
      }
    });
  }

  private scheduleInterval(): void {
    if (this.interval) {
      clearInterval(this.interval);
    }
    const secs = vscode.workspace
      .getConfiguration("novisentinel")
      .get<number>("healthPollSeconds", 30);
    this.interval = setInterval(() => this.check(), Math.max(secs, 5) * 1_000);
  }

  private async check(): Promise<void> {
    const healthy = await this.client.health();
    this.render(healthy ? "live" : "unreachable");
  }

  private render(state: State): void {
    const cfg = vscode.workspace.getConfiguration("novisentinel");
    const apiUrl = cfg.get<string>("apiUrl", "http://localhost:8000");
    const checked = new Date().toLocaleTimeString();

    switch (state) {
      case "live":
        this.item.text = "$(shield) NoviSentinel";
        this.item.color = undefined;
        this.item.backgroundColor = undefined;
        break;
      case "degraded":
        this.item.text = "$(shield) NoviSentinel ⚠";
        this.item.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
        break;
      case "unreachable":
        this.item.text = "$(shield-x) NoviSentinel ✕";
        this.item.backgroundColor = new vscode.ThemeColor("statusBarItem.errorBackground");
        break;
    }
    this.item.tooltip = `NoviSentinel — ${apiUrl}\nLast check: ${checked}`;
  }

  dispose(): void {
    if (this.interval) {
      clearInterval(this.interval);
    }
    this.item.dispose();
  }
}
