# NoviSentinel for VS Code

Scan text for **PII, prompt injection, secrets, and toxicity** before sending to LLMs — right from your editor.

> Requires a running NoviSentinel API ([local Docker](https://github.com/009-KumarJi/novi-sentinel#quickstart) or the [hosted playground](https://play.novisentinel.dev)).

---

## What it does

- **`@novisentinel` chat participant** — type `@novisentinel <your prompt>` in the VS Code chat panel to scan it instantly. See action, risk level, and per-detection explanations inline.
- **Scan Selection** — right-click any selected text → *NoviSentinel: Scan Selection*, or press `Cmd+Shift+S` / `Ctrl+Shift+S`. Detections appear as inline squiggles.
- **Scan Clipboard** — scan whatever's on the clipboard before pasting it into a chat. Press `Cmd+Shift+V Cmd+S` / `Ctrl+Shift+V Ctrl+S`.
- **Status bar indicator** — live connection status at a glance. Click to open settings.

---

## Setup

1. Install the extension from the VS Code Marketplace.
2. Set your API URL in settings: `novisentinel.apiUrl` (default: `http://localhost:8000`).
3. Run **NoviSentinel: Set API Key** from the Command Palette to store your key securely.
4. Run `docker compose up` in your NoviSentinel repo, or point at `https://api-play.novisentinel.dev` for the public playground.

---

## Commands

| Command | Keybinding | Description |
|---------|-----------|-------------|
| `NoviSentinel: Scan Selection` | `Cmd+Shift+S` / `Ctrl+Shift+S` | Scan the selected text |
| `NoviSentinel: Scan Clipboard` | `Cmd+Shift+V Cmd+S` | Scan clipboard contents |
| `NoviSentinel: Set API Key` | — | Store your API key in the OS keychain |
| `NoviSentinel: Test Connection` | — | Verify the API is reachable |
| `NoviSentinel: Open Settings` | — | Open the extension settings |

---

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `novisentinel.apiUrl` | `http://localhost:8000` | Base URL of your NoviSentinel API |
| `novisentinel.scanContext` | `input` | Treat scanned text as LLM `input` or `output` |
| `novisentinel.healthPollSeconds` | `30` | Status bar health check interval (seconds, min 5) |

---

## Links

- [GitHub repo](https://github.com/009-KumarJi/novi-sentinel)
- [Python SDK on PyPI](https://pypi.org/project/novisentinel/)
- [Live playground](https://play.novisentinel.dev)
- [Report an issue](https://github.com/009-KumarJi/novi-sentinel/issues)
