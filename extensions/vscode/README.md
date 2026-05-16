# NoviSentinel for VS Code

**Privacy proxy for AI coding agents** — scan and redact secrets, PII, and prompt injection right from your editor.

> Requires a running NoviSentinel instance. Start one with `docker run -d -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... ghcr.io/009-kumarji/novisentinel:latest`. No API key needed for local use.

---

## What it does

- **`@novisentinel` chat participant** — type `@novisentinel <your prompt>` in the VS Code chat panel to scan it before sending. See action, risk level, and per-detection explanations inline.
- **Scan Selection** — right-click any selected text → *NoviSentinel: Scan Selection*, or press `Cmd+Shift+S` / `Ctrl+Shift+S`. Detections appear as inline squiggles.
- **Scan Clipboard** — scan whatever's on the clipboard before pasting into a chat prompt. Press `Cmd+Shift+V Cmd+S` / `Ctrl+Shift+V Ctrl+S`.
- **Status bar indicator** — live connection status at a glance. Click to open settings.

---

## Setup

1. Install the extension from the VS Code Marketplace.
2. Start NoviSentinel locally:
   ```bash
   docker run -d -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... ghcr.io/009-kumarji/novisentinel:latest
   ```
3. The extension connects automatically to `http://localhost:8000`. No API key required for local use.
4. *(Optional)* Change the URL in settings: `novisentinel.apiUrl`.

---

## Commands

| Command | Keybinding | Description |
|---------|-----------|-------------|
| `NoviSentinel: Scan Selection` | `Cmd+Shift+S` / `Ctrl+Shift+S` | Scan the selected text |
| `NoviSentinel: Scan Clipboard` | `Cmd+Shift+V Cmd+S` | Scan clipboard contents |
| `NoviSentinel: Set API Key` | — | Store an API key (for hosted version) |
| `NoviSentinel: Test Connection` | — | Verify NoviSentinel is reachable |
| `NoviSentinel: Open Settings` | — | Open extension settings |

---

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `novisentinel.apiUrl` | `http://localhost:8000` | Base URL of your NoviSentinel instance |
| `novisentinel.scanContext` | `input` | Treat scanned text as LLM `input` or `output` |
| `novisentinel.healthPollSeconds` | `30` | Status bar health check interval (seconds, min 5) |

---

## Links

- [GitHub repo](https://github.com/009-KumarJi/novisentinel-core)
- [Python SDK on PyPI](https://pypi.org/project/novisentinel/)
- [Report an issue](https://github.com/009-KumarJi/novisentinel-core/issues)
