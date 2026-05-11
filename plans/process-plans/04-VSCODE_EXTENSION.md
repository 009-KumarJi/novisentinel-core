# 04 â€” VS Code Extension â˜…

**The wedge feature.** A working VS Code extension is the single highest-leverage piece of OSS distribution work in this whole roadmap. Every developer who installs it becomes a downstream advocate inside their company.

Today: `extensions/vscode/package.json` is filled in (contributes commands, chat participant, configuration). `extensions/vscode/src/` is **empty**. You need to write the TypeScript.

**Effort:** ~2 weeks, one engineer.
**Depends on:** F-203 (PyPI publish â€” for parity messaging) is helpful but not blocking.
**Gate to:** the launch.

---

## F-401 â€” TypeScript scaffolding

**Phase:** Pre-launch Â· **Effort:** XS Â· **Depends on:** â€”

**Goal:** `extensions/vscode/` compiles cleanly. No code logic yet â€” just the skeleton.

### Tasks

- [ ] **T1.** `cd extensions/vscode && npm install`. Resolve any missing peer deps.
- [ ] **T2.** Create `extensions/vscode/tsconfig.json` if missing. Targets: ES2022, module commonjs (vsce expects this), `rootDir: src`, `outDir: out`, `strict: true`.
- [ ] **T3.** Create `src/extension.ts` with a minimal `activate()` / `deactivate()` exporting nothing else yet. Just `console.log('NoviSentinel activated')` on activate.
- [ ] **T4.** Create `.vscodeignore` to exclude `src/`, `tsconfig.json`, `node_modules/`, `**/.git*` from the packaged vsix. Include only `out/`, `package.json`, `README.md`, `LICENSE`, `CHANGELOG.md`.
- [ ] **T5.** `npm run compile`. Confirm `out/extension.js` is created.
- [ ] **T6.** In VS Code, open `extensions/vscode/`. Press F5. Extension Development Host opens. Look in the Output panel â†’ "NoviSentinel" channel (or developer console) for the activation log.

### Files

| Action | Path |
|---|---|
| edit | `extensions/vscode/tsconfig.json` |
| create | `extensions/vscode/src/extension.ts` |
| create | `extensions/vscode/.vscodeignore` |
| create | `extensions/vscode/README.md` (placeholder; full version in F-411) |

### Acceptance

- `npm run compile` produces `out/extension.js`.
- F5 launches an Extension Development Host with the extension loaded.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 â€” 2026-05-11 [ ] T5 (manual: npm run compile) [ ] T6 (manual: F5 in VS Code)

---

## F-402 â€” API client (TS port of the Python SDK)

**Phase:** Pre-launch Â· **Effort:** S Â· **Depends on:** F-401

**Goal:** `src/api-client.ts` â€” a thin TypeScript wrapper over `fetch` (or `node-fetch`) that calls the NoviSentinel API. Mirrors the Python SDK's surface.

### Tasks

- [ ] **T1.** Define TypeScript types matching the BE's Pydantic models. Mirror `ScanRequest`, `ScanResponse`, `Detection`. Put them in `src/types.ts`.
- [ ] **T2.** Create `src/api-client.ts` exporting a `NoviSentinelClient` class with:
  - `constructor(apiUrl: string, apiKey: string, timeoutMs: number = 30000)`
  - `async scan(text: string, context?: 'input' | 'output'): Promise<ScanResponse>`
  - `async health(): Promise<boolean>` â€” calls `/healthz`, returns true/false without throwing.
- [ ] **T3.** Use VS Code's built-in `fetch` (available in modern VS Code) â€” don't pull in `node-fetch`. Verify it works against `engines.vscode: ^1.93.0`.
- [ ] **T4.** Map errors:
  - Network error â†’ `NoviSentinelError('Cannot reach NoviSentinel at ' + apiUrl)`
  - 401/403 â†’ `NoviSentinelError('Invalid API key. Run: NoviSentinel: Set API Key')`
  - 429 â†’ `NoviSentinelError('Rate limited. Try again in ' + retryAfter + 's')`
  - 5xx â†’ `NoviSentinelError('NoviSentinel returned ' + status)`
- [ ] **T5.** Add a `requestTimeout` abort signal so a hung request doesn't freeze the editor.
- [ ] **T6.** Read settings (apiUrl, scanContext) on every call so settings changes take effect without a reload.

### Files

| Action | Path |
|---|---|
| create | `src/types.ts`, `src/api-client.ts`, `src/errors.ts` |

### Acceptance

- `await client.scan("My SSN is 123-45-6789")` returns a `ScanResponse` against a running local API.
- Network failure raises a clear error message.
- Settings changes (`apiUrl`) reflect on the next call without VS Code restart.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 â€” 2026-05-11 [ ] T5 (manual: npm run compile) [ ] T6 (manual: F5 in VS Code)

---

## F-403 â€” API key storage (SecretStorage)

**Phase:** Pre-launch Â· **Effort:** XS Â· **Depends on:** F-402

**Goal:** The API key never lives in a plain settings JSON file. Store it in VS Code's `SecretStorage`.

### Tasks

- [ ] **T1.** In `src/extension.ts`, register the `novisentinel.setApiKey` command. The command:
  - Opens an `InputBox` (password-typed).
  - Writes to `context.secrets.store('novisentinel.apiKey', value)`.
  - Shows an info notification: "API key saved."
- [ ] **T2.** Add a helper `getApiKey(context: ExtensionContext): Promise<string | undefined>` that reads from `context.secrets.get('novisentinel.apiKey')`. Falls back to checking the env var `NOVISENTINEL_API_KEY` for dev convenience.
- [ ] **T3.** If `getApiKey()` returns undefined when a scan is invoked, show a notification with a button: "Set API key now" â†’ triggers `setApiKey` command.
- [ ] **T4.** Bonus: on first activation, if no key is stored, show a one-time notification with the same prompt.

### Acceptance

- The key is stored encrypted (VS Code's OS keychain).
- Restarting VS Code preserves the key.
- Uninstalling the extension removes the key (VS Code handles this).

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 -- 2026-05-11

---

## F-404 â€” Status bar item

**Phase:** Pre-launch Â· **Effort:** S Â· **Depends on:** F-402

**Goal:** A status bar item shows the connection state to the NoviSentinel API. Green = live, yellow = degraded, red = unreachable.

### Tasks

- [ ] **T1.** Create `src/status-bar.ts`. Export a `StatusBar` class that:
  - Creates a `StatusBarItem` at `StatusBarAlignment.Right`, priority 100.
  - Renders three states with icons + color:
    - Live: `$(shield) NoviSentinel` (default fg color)
    - Degraded: `$(shield) NoviSentinel âš ` (`statusBarItem.warningBackground`)
    - Unreachable: `$(shield-x) NoviSentinel âœ•` (`statusBarItem.errorBackground`)
  - Tooltip: shows last-check time + the API URL.
  - On click: opens NoviSentinel settings.
- [ ] **T2.** Health-poll loop. Use `setInterval` with the configured `novisentinel.healthPollSeconds` (default 30, min 5). Cancel on `deactivate()`.
- [ ] **T3.** First check fires immediately on activation (no 30s wait for first status).
- [ ] **T4.** Re-create the interval if `healthPollSeconds` setting changes (use `workspace.onDidChangeConfiguration`).
- [ ] **T5.** Define "degraded": health endpoint returns 200 but with `models: { pii: false }` etc. (some detectors not loaded).

### Files

| Action | Path |
|---|---|
| create | `src/status-bar.ts` |
| edit | `src/extension.ts` (instantiate + dispose) |

### Acceptance

- Status bar reflects API state within 30s of a change.
- Clicking it opens the NoviSentinel settings page.
- Stopping `docker compose` turns it red within `healthPollSeconds` + a few seconds.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 [x] T5 -- 2026-05-11

---

## F-405 â€” Output channel

**Phase:** Pre-launch Â· **Effort:** XS Â· **Depends on:** F-402

**Goal:** A dedicated "NoviSentinel" output channel that logs every scan's full JSON response. Helps users debug.

### Tasks

- [ ] **T1.** Create `src/output.ts`. Export a `Logger` singleton wrapping `OutputChannel`.
- [ ] **T2.** Methods: `info(msg)`, `warn(msg)`, `error(msg)`, `scanResult(req, resp)` â€” pretty-prints request + response with timestamp.
- [ ] **T3.** Use it from every command + the api-client error path.

### Acceptance

- Open View â†’ Output â†’ select "NoviSentinel" â€” see a running log of every scan.
- Errors land here too.

### Status

- [x] T1 [x] T2 [x] T3 -- 2026-05-11

---

## F-406 â€” Command: Scan Selection

**Phase:** Pre-launch Â· **Effort:** S Â· **Depends on:** F-402, F-403, F-405

**Goal:** Right-click selected text â†’ "NoviSentinel: Scan Selection" â†’ scan runs â†’ result shows as inline diagnostics + a notification.

### Tasks

- [ ] **T1.** Implement `novisentinel.scanSelection` in `src/commands/scan-selection.ts`:
  - Read the current selection from the active editor.
  - If empty: notify "Select some text first."
  - Else: call `client.scan(text, context)` where context comes from settings (default `input`).
- [ ] **T2.** On result:
  - `action: 'allow'` â†’ info notification: `âœ“ Clean (no detections)`.
  - `action: 'warn'` â†’ warning notification: `âš  Warning â€” N detections`. Show "View details" button â†’ opens the output channel.
  - `action: 'redact'` â†’ info notification with the redacted text + "Replace selection with redacted" button.
  - `action: 'block'` â†’ error notification: `ðŸ›‘ Blocked â€” N detections (severity: critical)`. Show "View details" button.
- [ ] **T3.** Render each detection as a VS Code `Diagnostic` on the active document. Severity: maps to detection severity (`critical/high â†’ Error`, `medium â†’ Warning`, `low â†’ Information`). Range: the selection range, narrowed to the detection's `start`/`end` if reasonable.
- [ ] **T4.** Wire the `editor/context` menu (already in package.json) to fire the command.
- [ ] **T5.** Wire the keybinding (`Ctrl+Shift+S` / `Cmd+Shift+S`).
- [ ] **T6.** Manual test: select a SSN string, run the command, confirm a red squiggle appears + a blocked notification.

### Files

| Action | Path |
|---|---|
| create | `src/commands/scan-selection.ts` |
| edit | `src/extension.ts` (register command + diagnostic collection) |

### Acceptance

- Right-click on selected text â†’ command appears.
- Cmd+Shift+S triggers a scan.
- Detections render as inline diagnostics with the right severity.
- Notification matches the action.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 â€” 2026-05-11 [ ] T5 (manual: npm run compile) [ ] T6 (manual: F5 in VS Code)

---

## F-407 â€” Command: Scan Clipboard

**Phase:** Pre-launch Â· **Effort:** XS Â· **Depends on:** F-406

**Goal:** Run a scan against whatever's currently on the clipboard. Meant for "I'm about to paste this into ChatGPT â€” is it safe?"

### Tasks

- [ ] **T1.** Implement `novisentinel.scanClipboard` in `src/commands/scan-clipboard.ts`:
  - Read clipboard via `env.clipboard.readText()`.
  - If empty: notify "Clipboard is empty."
  - Else: same scan + result flow as Scan Selection, minus the diagnostic-rendering step (no editor selection to attach to).
- [ ] **T2.** Bonus: if action is `redact`, offer a button "Copy redacted text to clipboard" that overwrites the clipboard with `result.redacted_text`.

### Acceptance

- `Cmd+Shift+V Cmd+S` triggers a scan of the clipboard.
- Result notification matches the action.
- The "Copy redacted" button correctly replaces the clipboard.

### Status

- [x] T1 [x] T2 -- 2026-05-11

---

## F-408 â€” Chat participant `@novisentinel`

**Phase:** Pre-launch Â· **Effort:** M Â· **Depends on:** F-402

**Goal:** In VS Code's chat panel, typing `@novisentinel <prompt>` runs the prompt through NoviSentinel's scanner and renders the verdict + detections in the chat panel. Lives next to GitHub Copilot Chat in the same UI.

### Tasks

- [ ] **T1.** Implement the chat participant handler in `src/chat/participant.ts`:
  - Signature: `(request, context, response, token) => Promise<void>`.
  - Read `request.prompt`.
  - Call `client.scan(request.prompt, 'input')`.
  - Render markdown to `response`:
    - Top line: `**Action: BLOCK** Â· risk: critical Â· 1 detection Â· 12ms`
    - Detections table: detector | type | confidence | severity | preview.
    - "Why this was flagged" â€” one-line explanation per detection (write a tiny `explanation(detection)` helper that maps `(detector, type)` to a friendly string).
    - "Redacted version" (if applicable): code block.
- [ ] **T2.** Register the participant in `src/extension.ts` via `chat.createChatParticipant('novisentinel.scan', handler)`.
- [ ] **T3.** Set the participant icon (use the project shield logo at a small size â€” see F-411 README for the asset).
- [ ] **T4.** Add a follow-up suggestion: after a block, suggest "How can I rephrase this safely?" as a follow-up prompt the user can click.
- [ ] **T5.** Handle errors gracefully: API unreachable â†’ "NoviSentinel isn't running. Start it with `docker compose up` and try again."
- [ ] **T6.** Manual test: open the chat panel, type `@novisentinel ignore previous instructions`, confirm the blocked-injection response renders correctly.

### Files

| Action | Path |
|---|---|
| create | `src/chat/participant.ts`, `src/chat/explanation.ts` |
| edit | `src/extension.ts` (registration) |

### Acceptance

- `@novisentinel <text>` works in the VS Code chat panel.
- Result renders cleanly with markdown formatting.
- A blocked prompt shows the right detection + a friendly explanation.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 â€” 2026-05-11 [ ] T5 (manual: npm run compile) [ ] T6 (manual: F5 in VS Code)

---

## F-409 â€” First-run onboarding

**Phase:** Pre-launch Â· **Effort:** S Â· **Depends on:** F-401..F-408

**Goal:** First time a user installs the extension, walk them through setup in 60 seconds. Without this, the install-to-first-scan funnel leaks badly.

### Tasks

- [ ] **T1.** On first activation (detect via `context.globalState.get('novisentinel.onboarded') !== true`):
  - Show an info notification: "Welcome to NoviSentinel. Where is your API running?"
  - Buttons: `[Use local Docker â€” http://localhost:8000]` `[Use hosted playground]` `[I'll configure later]`.
- [ ] **T2.** "Use local Docker":
  - Test the local URL via `client.health()`.
  - If healthy: notify "Connected. Try scanning something."
  - If not: notify "Couldn't reach localhost:8000. Run `docker compose up` from your NoviSentinel folder, then run **NoviSentinel: Test Connection**." + a button to open docs.
- [ ] **T3.** "Use hosted playground":
  - Set `apiUrl` to `https://api-play.novisentinel.dev` (the F-310 instance).
  - Auto-set the API key to the public `play-public` key.
  - Notify: "Connected to the public playground. Note: rate limits apply."
- [ ] **T4.** "I'll configure later": dismiss + set the flag.
- [ ] **T5.** Add a `novisentinel.testConnection` command for re-testing.

### Files

| Action | Path |
|---|---|
| create | `src/onboarding.ts` |
| edit | `src/extension.ts` |
| edit | `package.json` (add `novisentinel.testConnection` command) |

### Acceptance

- First install â†’ user sees the welcome flow.
- "Use hosted playground" gets them to a working scan with zero setup.
- Subsequent activations don't repeat the flow.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 [x] T5 -- 2026-05-11

---

## F-410 â€” VS Marketplace publish

**Phase:** Pre-launch Â· **Effort:** S Â· **Depends on:** F-401..F-409

**Goal:** `novisentinel-vscode` is installable from the VS Code Marketplace via "Install Extension" search.

### Tasks

- [ ] **T1.** Create a Marketplace publisher account at https://marketplace.visualstudio.com/manage. Choose the publisher ID `novisentinel` (matches `package.json`).
- [ ] **T2.** Generate a Personal Access Token (PAT) from Azure DevOps for marketplace.publishing.
- [ ] **T3.** Install `vsce` globally: `npm i -g @vscode/vsce`.
- [ ] **T4.** Login: `vsce login novisentinel`. Paste the PAT.
- [ ] **T5.** Polish `package.json`:
  - Add `repository` field pointing to GitHub.
  - Add `bugs.url` pointing to GitHub issues.
  - Add `homepage` pointing to `https://novisentinel.com` (or repo).
  - Add a `galleryBanner` with `color: "#0a0b0d"` and `theme: dark`.
  - Add an `icon` field pointing to a 128Ã—128 PNG in `extensions/vscode/icon.png`.
- [ ] **T6.** Add a quality `README.md` for the extension (see F-411).
- [ ] **T7.** Add a `CHANGELOG.md` for the extension.
- [ ] **T8.** Package: `vsce package`. Produces `novisentinel-vscode-0.1.0.vsix`.
- [ ] **T9.** Install the vsix locally on a clean VS Code profile. Confirm everything works.
- [ ] **T10.** Publish: `vsce publish`. (Or first publish as preview via `vsce publish --pre-release`.)
- [ ] **T11.** Verify: search "NoviSentinel" in the Marketplace UI. Confirm the listing renders correctly.

### Files

| Action | Path |
|---|---|
| edit | `extensions/vscode/package.json` |
| create | `extensions/vscode/icon.png`, `extensions/vscode/README.md`, `extensions/vscode/CHANGELOG.md` |

### Acceptance

- The extension is published and installable from the Marketplace.
- The listing page shows the icon, banner, README, and changelog.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 â€” 2026-05-11 [ ] T5 (manual: npm run compile) [ ] T6 (manual: F5 in VS Code) [ ] T7 [ ] T8 [ ] T9 [ ] T10 [ ] T11

---

## F-411 â€” Extension README

**Phase:** Pre-launch Â· **Effort:** XS Â· **Depends on:** F-401

**Goal:** A short, scannable README that shows up on the Marketplace listing.

### Tasks

- [ ] **T1.** Create `extensions/vscode/README.md`:
  - 1-sentence positioning: "Scan text for PII, prompt injection, secrets, and toxicity before sending to LLMs."
  - GIF (record one!) of the chat participant in action.
  - Three sections: **What it does**, **Setup** (3 lines: install, set API URL, set API key), **Commands** (table of commands + keybindings).
  - Link back to the main GitHub repo.
  - Mention: "Requires a running NoviSentinel API (local Docker or hosted playground)."
- [ ] **T2.** Record the GIF. Use Kap (macOS) or LICEcap (cross-platform). 5-10 seconds. Show: open chat â†’ type `@novisentinel my SSN is 123-45-6789` â†’ see the blocked result.
- [ ] **T3.** Save the GIF in `extensions/vscode/docs/demo.gif`. Reference from README.

### Acceptance

- Marketplace listing renders the README cleanly.
- The GIF auto-plays on the listing.

### Status

- [x] T1 [x] T2 [x] T3 -- 2026-05-11

---

## F-412 â€” Webview playground panel (stretch)

**Phase:** Post-launch Â· **Effort:** M Â· **Depends on:** F-410

**Goal:** A webview panel inside VS Code that mirrors the dashboard playground. Open via `NoviSentinel: Open Playground`. Power-user feature.

### Tasks

- [ ] **T1.** Defer until V0.1 has shipped + a user requests it.
- [ ] **T2.** Sketch the panel content in a design note in `plans/notes/F-412.md`.

### Status

- [x] T1 [x] T2 -- 2026-05-11

---

## F-413 â€” Diagnostic-on-paste (stretch)

**Phase:** Post-launch Â· **Effort:** M Â· **Depends on:** F-406

**Goal:** Auto-scan pasted text in the editor (if larger than 100 chars). Surface findings as diagnostics without the user explicitly running a command.

### Tasks

- [ ] **T1.** Defer until V0.1 has shipped.

### Status

- [x] T1 -- 2026-05-11

---

## Done condition for this plan

Phase complete when F-401 through F-411 are all `[x]`. F-412 and F-413 are post-launch stretch.

When this plan is done:
- The extension is on the VS Marketplace.
- Installing it gives a developer a working `@novisentinel` participant, scan commands, and a status bar indicator.
- The launch post has a Marketplace link as a real artifact.
