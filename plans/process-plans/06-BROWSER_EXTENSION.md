# 06 — Browser Extension

**Inject NoviSentinel into ChatGPT.com, Claude.ai, Gemini, etc. Scan before paste.**

This is **Phase 3** of the original `nifty-dawn` plan. It is **deferred until post-launch.** Build the VS Code extension first; if that lands well, this is the next big OSS moment. If VS Code doesn't land, this likely shouldn't either.

**Effort:** ~5 days, one engineer.
**Depends on:** F-410 (VS Marketplace publish), F-310 (public playground for the extension's fallback API), `play.novisentinel.dev` running.
**Gate:** decide go/no-go based on VS Code extension installs at week 8–10 post-launch.

---

## Decision criteria — should this be built?

Don't start this plan unless **at least two** of these are true:

1. VS Code extension has > 500 Marketplace installs.
2. At least one user has asked for a browser extension in GitHub Discussions / Issues.
3. The PyPI package is getting > 100 downloads/week.

If none are true, the OSS isn't landing, and a second distribution surface won't fix it. Reconsider strategy in `plans/oss-section-doc/02-ROADMAP.md`.

---

## F-601 — Architecture decisions

**Phase:** Post-launch · **Effort:** XS · **Depends on:** decision

**Goal:** Lock in the technical approach before writing code.

### Decisions to make

- [ ] **D1.** **Manifest version.** V3 only — V2 is being phased out by Chrome. Confirm Firefox supports V3 (it does as of 2024+).
- [ ] **D2.** **Cross-browser strategy.** Build once with `webextension-polyfill`. Targets: Chrome, Edge, Firefox, Opera (Brave inherits Chrome). Skip Safari for v1 (different signing process).
- [ ] **D3.** **Bundler.** Vite with `@crxjs/vite-plugin`. Fast HMR for development, clean production output.
- [ ] **D4.** **Default API endpoint.** `https://api-play.novisentinel.dev` (the public playground from F-310). Users can configure their own URL in the options page.
- [ ] **D5.** **Content script injection strategy.** Match patterns on `*://chatgpt.com/*`, `*://claude.ai/*`, `*://gemini.google.com/*`, `*://chat.mistral.ai/*`. Inject a small button next to the chat input.
- [ ] **D6.** **Scanning trigger.** On click (not on every keystroke — too aggressive). Show result in a tooltip / popover.
- [ ] **D7.** **Privacy posture.** Make it crystal clear: text is sent to the configured API. By default `api-play.novisentinel.dev`. Show the configured URL in the popup so it's never hidden.

### Files

| Action | Path |
|---|---|
| create | `extensions/browser/DESIGN.md` documenting all decisions |

### Status

- [ ] D1 [ ] D2 [ ] D3 [ ] D4 [ ] D5 [ ] D6 [ ] D7

---

## F-602 — Scaffolding

**Phase:** Post-launch · **Effort:** S · **Depends on:** F-601

**Goal:** A working "Hello, world" browser extension that loads in Chrome and Firefox.

### Tasks

- [ ] **T1.** Create `extensions/browser/`. Initialize: `npm init -y`.
- [ ] **T2.** Install: `vite`, `@crxjs/vite-plugin`, `@types/chrome`, `webextension-polyfill`, `typescript`.
- [ ] **T3.** Create `manifest.json` (V3):
  ```json
  {
    "manifest_version": 3,
    "name": "NoviSentinel",
    "version": "0.1.0",
    "description": "Scan prompts for PII, prompt injection, secrets, and toxicity before sending them to ChatGPT, Claude, Gemini, and more.",
    "permissions": ["storage", "clipboardRead", "activeTab"],
    "host_permissions": [
      "https://chatgpt.com/*",
      "https://claude.ai/*",
      "https://gemini.google.com/*",
      "https://chat.mistral.ai/*",
      "https://api-play.novisentinel.dev/*"
    ],
    "background": { "service_worker": "src/background.ts", "type": "module" },
    "content_scripts": [
      {
        "matches": ["https://chatgpt.com/*", "https://claude.ai/*", "https://gemini.google.com/*", "https://chat.mistral.ai/*"],
        "js": ["src/content/index.ts"],
        "css": ["src/content/styles.css"]
      }
    ],
    "action": { "default_popup": "src/popup/index.html" },
    "options_page": "src/options/index.html",
    "icons": { "16": "icons/16.png", "48": "icons/48.png", "128": "icons/128.png" }
  }
  ```
- [ ] **T4.** Set up `vite.config.ts` with `@crxjs/vite-plugin`.
- [ ] **T5.** Create empty stubs: `src/background.ts`, `src/content/index.ts`, `src/content/styles.css`, `src/popup/index.html`, `src/popup/popup.ts`, `src/options/index.html`, `src/options/options.ts`.
- [ ] **T6.** Add icons (reuse the VS Code extension icon, resized).
- [ ] **T7.** Build: `npm run build`. Load `dist/` as an unpacked extension in `chrome://extensions/`. Confirm it loads with no errors.

### Files

| Action | Path |
|---|---|
| create | `extensions/browser/` directory tree as above |

### Acceptance

- Extension loads in Chrome and Firefox without console errors.
- The toolbar icon is present.

### Status

- [ ] T1 [ ] T2 [ ] T3 [ ] T4 [ ] T5 [ ] T6 [ ] T7

---

## F-603 — Background service worker — API client

**Phase:** Post-launch · **Effort:** S · **Depends on:** F-602

**Goal:** Background service worker holds the API client. Content scripts message it to perform scans. This keeps the API URL + key in one place and avoids CORS issues for the content script.

### Tasks

- [ ] **T1.** Implement `src/background.ts`:
  - On install, set default storage: `apiUrl: 'https://api-play.novisentinel.dev'`, `apiKey: 'play-public'`.
  - Listen on `browser.runtime.onMessage` for `{type: 'scan', text, context}` messages.
  - On message: fetch from `${apiUrl}/v1/scan` with `Authorization: Bearer ${apiKey}`. Return the response.
  - Errors: catch and return `{ok: false, error: '...'}`.
- [ ] **T2.** Define a typed message protocol in `src/protocol.ts`.

### Acceptance

- Content scripts can `await browser.runtime.sendMessage({type: 'scan', text: 'hello'})` and get back a `ScanResponse`.

### Status

- [ ] T1 [ ] T2

---

## F-604 — Content script — ChatGPT.com integration

**Phase:** Post-launch · **Effort:** M · **Depends on:** F-603

**Goal:** On ChatGPT.com, find the chat input box. Inject a small "Scan" button next to the Send button. On click: scan the input → show result in a popover.

### Tasks

- [ ] **T1.** Inspect ChatGPT.com's DOM. Find the textarea / contenteditable selector for the chat input + the send button. **This selector will break occasionally** — that's a maintenance reality of browser extensions on third-party sites.
- [ ] **T2.** In `src/content/chatgpt.ts`, implement:
  - On DOMContentLoaded (or observed input appearance): find the input + send button.
  - Inject a "🛡 Scan" button immediately to the left of Send.
  - On click: read the input text → send a `scan` message to the background → render the result in a floating popover above the input.
- [ ] **T3.** Popover layout (use a small Shadow DOM to avoid site CSS conflicts):
  - Header: action pill (BLOCK / WARN / REDACT / ALLOW)
  - Body: short detection list — type + severity + confidence
  - Footer: "Replace input with redacted version" button (if applicable) + "Send anyway" button + "Cancel."
- [ ] **T4.** "Replace input with redacted version" → programmatically set the input's text content to `result.redacted_text`. Most chat inputs are contenteditable; use the React-aware approach (dispatch an input event).
- [ ] **T5.** Use a `MutationObserver` to re-inject the button if the chat input is re-rendered (ChatGPT's React tree thrashes).
- [ ] **T6.** Style the button to look at home in ChatGPT's UI — match border-radius, padding, hover state.

### Files

| Action | Path |
|---|---|
| create | `src/content/chatgpt.ts`, `src/content/popover.ts`, `src/content/styles.css` |

### Acceptance

- On `chatgpt.com`, the Scan button appears next to Send.
- Clicking with a clean message → "Allow" popover.
- Clicking with "My SSN is 123-45-6789" → "Block" popover with PII details.
- "Replace with redacted" correctly updates the input.

### Status

- [ ] T1 [ ] T2 [ ] T3 [ ] T4 [ ] T5 [ ] T6

---

## F-605 — Content script — Claude.ai integration

**Phase:** Post-launch · **Effort:** S · **Depends on:** F-604

**Goal:** Same as F-604 but on Claude.ai.

### Tasks

- [ ] **T1.** Inspect Claude.ai's DOM. Find the input + send button selectors.
- [ ] **T2.** Implement `src/content/claude.ts` mirroring F-604's structure.
- [ ] **T3.** Match Claude.ai's UI style.

### Acceptance

- Same as F-604 but on Claude.ai.

### Status

- [ ] T1 [ ] T2 [ ] T3

---

## F-606 — Content script — Gemini integration

**Phase:** Post-launch · **Effort:** S · **Depends on:** F-604

**Goal:** Same on `gemini.google.com`.

### Tasks

- [ ] **T1.** Inspect, implement, match.

### Acceptance

- Same as F-604/F-605.

### Status

- [ ] T1

---

## F-607 — Content script — Mistral Chat integration

**Phase:** Post-launch · **Effort:** S · **Depends on:** F-604

**Goal:** Same on `chat.mistral.ai`.

### Tasks

- [ ] **T1.** Inspect, implement, match.

### Acceptance

- Same.

### Status

- [ ] T1

---

## F-608 — Popup UI

**Phase:** Post-launch · **Effort:** S · **Depends on:** F-603

**Goal:** Clicking the toolbar icon opens a popup with a textarea + Scan button. Lets users scan arbitrary text outside of the supported chat sites.

### Tasks

- [ ] **T1.** In `src/popup/`:
  - Textarea (large).
  - "Scan as input" / "Scan as output" radio.
  - "Scan" button.
  - Result panel below — same look as the content-script popover.
- [ ] **T2.** Wire to the background.
- [ ] **T3.** Add a "Open Playground →" link to `play.novisentinel.dev`.
- [ ] **T4.** Add a "Configure API" link to the options page.

### Acceptance

- Clicking the toolbar icon opens the popup.
- The popup can scan any text.

### Status

- [ ] T1 [ ] T2 [ ] T3 [ ] T4

---

## F-609 — Options page

**Phase:** Post-launch · **Effort:** S · **Depends on:** F-603

**Goal:** Users can configure their own API URL and API key. Trust signal — they can point at their own self-hosted instance instead of the default public one.

### Tasks

- [ ] **T1.** In `src/options/`:
  - Field: API URL (default `https://api-play.novisentinel.dev`).
  - Field: API key (default `play-public`, masked).
  - "Test connection" button → fires a `/healthz` ping → shows result.
  - "Save" button → writes to `browser.storage.sync`.
  - Explainer: "By default, NoviSentinel sends text to our public playground at api-play.novisentinel.dev. To self-host, run `docker compose up` from the NoviSentinel repo and set the URL to `http://localhost:8000`."
- [ ] **T2.** Privacy section at the bottom: link to a privacy doc explaining what data the extension sends.

### Acceptance

- User can change the API URL and key. New scans use the new endpoint.
- Test-connection button works.

### Status

- [ ] T1 [ ] T2

---

## F-610 — CORS update on BE

**Phase:** Post-launch · **Effort:** XS · **Depends on:** F-603

**Goal:** The OSS BE must allow CORS requests from the browser extension's origin (`chrome-extension://...` and `moz-extension://...`).

### Tasks

- [ ] **T1.** In `app/config.py`, add `chrome-extension://*` and `moz-extension://*` to the default `cors_origins`.
- [ ] **T2.** Update the public playground's CORS config (F-310) similarly.

### Acceptance

- A content script's `fetch()` to the BE succeeds without CORS errors.

### Status

- [ ] T1 [ ] T2

---

## F-611 — Privacy policy doc

**Phase:** Post-launch · **Effort:** XS · **Depends on:** F-609

**Goal:** Browser stores require a privacy policy for extensions that send data to a server. Write one.

### Tasks

- [ ] **T1.** Create `extensions/browser/PRIVACY.md`. Cover:
  - What text the extension sends and when.
  - Where it sends it (default + user-configurable).
  - What we do with it: scan, return a verdict, **never store raw text** (the BE hashes everything).
  - Cookies: none.
  - Third parties: none.
  - Data retention on the public playground: 30 days for scan logs (hashes only).
- [ ] **T2.** Host it at `https://novisentinel.com/privacy/browser-extension` (or a `gh-pages` doc).
- [ ] **T3.** Link it from the options page and from each store listing.

### Acceptance

- Privacy policy is hosted, linked, accurate.

### Status

- [ ] T1 [ ] T2 [ ] T3

---

## F-612 — Chrome Web Store publish

**Phase:** Post-launch · **Effort:** S · **Depends on:** F-602..F-611

**Goal:** The extension is installable from the Chrome Web Store.

### Tasks

- [ ] **T1.** Create a Chrome Web Store developer account ($5 one-time registration fee).
- [ ] **T2.** Generate marketing assets: 128×128 icon, 1280×800 screenshots (at least 1, ideally 3–5), 440×280 promo tile, optional YouTube demo video.
- [ ] **T3.** Write the store listing: short description (132 chars), long description (markdown allowed, ~500 words), category (Productivity).
- [ ] **T4.** Production build: `npm run build`. Zip the `dist/` folder.
- [ ] **T5.** Upload, fill the listing, submit for review.
- [ ] **T6.** **Review takes 3–7 days** for first submission. Plan accordingly.
- [ ] **T7.** Once published, capture the install URL. Add to the README.

### Acceptance

- The extension is listed on the Chrome Web Store and installs cleanly.

### Status

- [ ] T1 [ ] T2 [ ] T3 [ ] T4 [ ] T5 [ ] T6 [ ] T7

---

## F-613 — Firefox Add-ons publish

**Phase:** Post-launch · **Effort:** S · **Depends on:** F-602..F-611

**Goal:** Same on `addons.mozilla.org`.

### Tasks

- [ ] **T1.** Create a Firefox Add-ons account (free).
- [ ] **T2.** Build a Firefox-specific bundle (`webextension-polyfill` handles most differences).
- [ ] **T3.** Submit. Review usually faster than Chrome (~1-3 days).

### Acceptance

- Available on `addons.mozilla.org`.

### Status

- [ ] T1 [ ] T2 [ ] T3

---

## F-614 — Edge Add-ons publish

**Phase:** Post-launch · **Effort:** XS · **Depends on:** F-612

**Goal:** Microsoft Edge has its own store; Chrome extensions can be re-submitted there with minimal changes.

### Tasks

- [ ] **T1.** Microsoft Partner Center account (free).
- [ ] **T2.** Submit the same Chrome bundle.

### Acceptance

- Available in the Edge Add-ons store.

### Status

- [ ] T1 [ ] T2

---

## F-615 — Launch announcement

**Phase:** Post-launch · **Effort:** XS · **Depends on:** F-612 (Chrome live)

**Goal:** When the Chrome extension is live, post a follow-up launch announcement.

### Tasks

- [ ] **T1.** Write a LinkedIn post: "ChatGPT now has a PII shield" — frame it as a useful safety win, not a product announcement.
- [ ] **T2.** Write a tweet thread (5–8 tweets) showing the extension in action.
- [ ] **T3.** Maybe a second HN post? Gauge: only post if the extension brings something materially new (e.g. "now works on Claude.ai, Gemini, ChatGPT, and Mistral with one install"). Otherwise skip — second HN posts of the same project rarely succeed.
- [ ] **T4.** Update `README.md` with the install link.
- [ ] **T5.** Update the dashboard playground with a "Try the browser extension →" CTA.

### Acceptance

- Public announcement is live.
- Install link is on the README.

### Status

- [ ] T1 [ ] T2 [ ] T3 [ ] T4 [ ] T5

---

## Done condition for this plan

Phase complete when F-601 through F-615 are all `[x]`.

When this plan is done:
- The extension is on Chrome Web Store, Firefox Add-ons, Edge Add-ons.
- ChatGPT.com, Claude.ai, Gemini, and Mistral Chat all have the Scan button.
- Real users can scan before they paste, without ever leaving the browser.
