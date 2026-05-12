# Changelog

## [1.0.1] — 2026-05-13

### Fixed

- Connection check now uses `/health` instead of `/healthz`, fixing repeated 404s in the API logs and the disconnected status bar when the API was actually running.

## [1.0.0] — 2026-05-12

### Added

- `@novisentinel` chat participant — scan prompts inline in VS Code chat.
- **Scan Selection** command (`Ctrl+Shift+S` / `Cmd+Shift+S`) with inline squiggles.
- **Scan Clipboard** command (`Ctrl+Shift+V Ctrl+S` / `Cmd+Shift+V Cmd+S`).
- Status bar indicator showing live API connection health.
- Secure API key storage via VS Code `SecretStorage` (OS keychain).
- First-run onboarding flow to set API URL and key.
- Supports PII, prompt injection, secrets, and toxicity detectors.
