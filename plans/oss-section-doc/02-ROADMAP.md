# 02 — OSS Roadmap

**What to build, in what order, over the next 90 days.**

Pre-requisite: read [`01-STRATEGY.md`](01-STRATEGY.md) first. This document assumes the OSS/enterprise split is settled.

---

## Review of your existing plan (`nifty-dawn`)

You already have a plan: [`~/.claude/plans/i-am-not-able-nifty-dawn.md`](../../../.claude/plans/i-am-not-able-nifty-dawn.md). Let me grade it against the OSS strategy.

| Phase in `nifty-dawn` | What it ships | Verdict |
|---|---|---|
| **Phase 1 — VS Code extension** | Chat participant + scan-selection + scan-clipboard + status bar | ✅ **Exactly right.** Highest-leverage OSS distribution surface. Keep as-is. |
| **Phase 2a — Publish Python SDK to PyPI** | `pip install novisentinel` | ✅ **Critical.** Should arguably move earlier (week 1, parallel with Phase 1). |
| **Phase 2b — Dashboard playground page** | textarea → scan → chips | ✅ **Yes** — but reframe: this isn't "for personal use," it's the public play page (`play.novisentinel.dev`). LinkedIn audience clicks this from your launch post. |
| **Phase 2c — Examples directory** | OpenAI / Anthropic / LangChain / Ollama wrappers | ✅ **Essential** — these are the docs that turn a curious dev into an integrator. |
| **Phase 3 — Browser extension** | "Scan with NoviSentinel" injected into ChatGPT.com, Claude.ai | ✅ **Yes, eventually.** Big LinkedIn moment when it lands. Save for month 2-3. |

**Verdict:** the plan is correct in scope. What's missing is the **OSS framing** around it. `nifty-dawn` reads as "make this usable for me." The reframed version reads as "ship the OSS distribution surface that gets the first 1000 users."

The same code lands either way; the difference is what you do *alongside* the code (the README rewrite, the launch post, the demo video, the HN/LinkedIn timing).

---

## The reframe — three things `nifty-dawn` is missing

### 1. A "shipping-ready" definition for the README

Today's README is fine for someone who already cares. It's not fine for someone who lands from a HackerNews link. **Before shipping anything else, rewrite the top of the README** to answer in the first 10 seconds:

- What is this?
- What does it do that I can't already get from a library?
- Show me a 30-second example.
- How do I run it?

I'll cover the README rewrite in week 1 of the schedule below.

### 2. A demo video

OSS launches with a video do 5–10× the engagement of OSS launches without one. 90 seconds, no voice required, captured terminal + browser, music optional. Show: `docker compose up`, `pip install`, scan a SSN → block, scan an injection → block, open the dashboard → see logs. That's it.

### 3. A measurable launch event

Don't dribble out PyPI + VS Code + browser extension over 3 months. Stack the launch: pick a day, post everywhere, have all three (or at least PyPI + VS Code) live on that day. One Big Bang gets you to ~500 stars; three small bangs get you to ~150.

---

## The 90-day plan

One engineer (you). One foot in OSS, one foot in keeping the enterprise FE/BE moving per `prod-level-doc/MASTER_FUTURE_PLAN.md`. Roughly 70% OSS / 30% enterprise.

Each week below is a checklist you can copy into a project board.

### Weeks 1–2 — Prep the OSS for the public

You don't launch yet. You make sure the front door is presentable.

- [ ] **README rewrite.** Top of file: 1-sentence positioning, 30-second example, 1-line install. Move the architecture section to the bottom. Add a "Why this exists" paragraph that explains the developer pain.
- [ ] **Polish error states.** Run the API with an invalid key, wrong port, malformed body. Make sure every error is human-readable. OSS users won't email you; they'll churn silently.
- [ ] **Tag a v1.0.0 release on GitHub.** With release notes derived from `CHANGELOG.md`. Releases create RSS items that show up in dev tools.
- [ ] **Publish Python SDK to PyPI.** Confirm the name isn't taken. Tag as `0.1.0`. Test `pip install novisentinel` from a fresh venv on a fresh machine.
- [ ] **Set up an issue template.** Bug / Feature request / Question. Saves you triage time later.
- [ ] **Write a `CONTRIBUTING.md`** (you have one — review it). What kind of PRs do you accept? Test requirements? Code-style expectations?
- [ ] **Add `SECURITY.md`** with a real disclosure email. You have one — confirm the email actually works.
- [ ] **Set up GitHub Actions CI** for `pytest`. Green badge on the README is a trust signal.
- [ ] **Confirm Docker Compose works on a clean clone.** Spin up a fresh VM, clone the repo, `docker compose up`, hit the API. Fix anything that doesn't work.

### Weeks 3–4 — Build the VS Code extension

This is `nifty-dawn` Phase 1, executed.

- [ ] **Scaffold the extension.** `extensions/vscode/` already has a `package.json` — the `src/` is empty. Fill it.
- [ ] **`@novisentinel` chat participant.** Per the package.json's `chatParticipants` entry.
- [ ] **Scan selection / clipboard commands.** Per package.json's `commands`.
- [ ] **Status bar item.** Health-poll the API every 30s.
- [ ] **Settings: `apiUrl`, `apiKey` (SecretStorage), `scanContext`.**
- [ ] **Local "first-run" wizard.** First time the extension loads, detect that the API isn't reachable → offer to run `docker compose up` for the user, OR provide a one-click "use the hosted free playground" option. The hosted option is huge — it eliminates the "I have to set up Docker" objection.
- [ ] **Test on Windows + macOS + Linux.** OSS users are mostly on macOS/Linux, but Windows breaks are loud.
- [ ] **Record a 30-second screen-cap** of the extension in use. You'll need it for the launch.
- [ ] **Publish to VS Marketplace** as `novisentinel.novisentinel-vscode`. This requires a Microsoft account + a `vsce` token. Plan for 1-2 hours of setup, not 15 minutes.

### Week 5 — Examples + Playground

This is `nifty-dawn` Phase 2b + 2c.

- [ ] **`examples/openai_wrapper.py`** — wraps `openai.chat.completions.create()` with pre + post scan.
- [ ] **`examples/anthropic_wrapper.py`** — same for Anthropic SDK.
- [ ] **`examples/langchain_callback.py`** — `NoviSentinelCallbackHandler`.
- [ ] **`examples/ollama_proxy.md`** — short note (OpenAI wrapper works with `base_url=http://localhost:11434/v1`).
- [ ] **`examples/streamlit_chat.py`** — a 50-line Streamlit chat app with NoviSentinel guarding both directions. Shippable demo.
- [ ] **`examples/README.md`** — short index, copy-pastable.
- [ ] **Dashboard playground page (`dashboard/app/playground/page.tsx`).** Textarea + Scan button → render detections as chips. **Deploy this to `play.novisentinel.dev`** — a free public service that runs against a sandboxed API instance. This is the link in your launch posts.

### Week 6 — Launch prep

You don't launch on a random Tuesday. You prepare.

- [ ] **Pick a launch date.** Wednesday at 10am ET is the conventional best HN time. Tuesday-Wednesday is best for LinkedIn. Pick one.
- [ ] **Write the launch post.** Three versions: HN (≤300 words, no fluff), LinkedIn (≤1500 chars, problem-first), Twitter/X thread (10 tweets max). I'll cover the templates in [`03-DISTRIBUTION.md`](03-DISTRIBUTION.md).
- [ ] **Record the demo video.** 90 seconds. Terminal + browser. No voice (subtitles are fine). Music optional, light. Show: install → scan PII → scan injection → scan secrets → see logs.
- [ ] **Make a GIF version** for the README and LinkedIn.
- [ ] **Stub a `landing` page** at `novisentinel.dev` (separate from the dashboard). Marketing copy from your enterprise side already works.
- [ ] **DM 10–20 friends in dev.** Ask them to star the repo *before* the launch — having 0 stars when you post hurts; having 50 helps.
- [ ] **Set up a Discord or GitHub Discussions.** People will have questions; they need somewhere to ask them. Discord is more engaging; Discussions is lower-maintenance. **Lean Discussions** for solo founders.

### Week 7 — Launch day & first week of community

- [ ] **Launch day.** Post to HN at 10am ET. LinkedIn at 9am. Twitter thread at 10:15am. dev.to longer post at 11am.
- [ ] **Sit at your computer for the next 6 hours.** Respond to every comment. Answer every issue. Be present. The "is the founder responsive?" signal matters more than people admit.
- [ ] **Track everything.** GitHub stars per hour, PyPI downloads per day, VS Marketplace installs per day. Numbers grow your nerve to keep going.
- [ ] **Pin a "show & tell" issue.** "What did you scan with NoviSentinel today?" Encourages first-timers to post their use case.

### Weeks 8–9 — Iterate on what landed

- [ ] **Triage all issues.** Aim for first response < 24h, even if it's just "I see this, will look at it this week."
- [ ] **Ship one meaningful improvement per week.** Visible momentum matters.
- [ ] **Write a follow-up blog post** in week 9: "What I learned launching an OSS AI safety tool — 30 days in." This gets a second wave of attention.
- [ ] **Add the first community-requested feature.** Doesn't have to be big — 1 new detector, 1 new SDK method. The point is to *be seen* responding to the community.

### Weeks 10–12 — Phase 3 (browser extension) + ecosystem

- [ ] **Browser extension** (`extensions/browser/`). `nifty-dawn` Phase 3. Manifest V3. Content script injects "Scan with NoviSentinel" into ChatGPT.com, Claude.ai, Gemini, Mistral chat.
- [ ] **Publish to Chrome Web Store + Firefox Add-ons + Edge Add-ons.** Each has its own review process (~3-7 days). Plan for it.
- [ ] **Second launch event** at end of week 12. "ChatGPT now has a PII shield." LinkedIn loves this kind of headline. HN can be more selective; gauge before posting.
- [ ] **Node / TypeScript SDK** (if Python downloads + extension installs justify it). Skip if not.
- [ ] **GitHub Pages docs site.** mkdocs-material against the existing README content. `docs.novisentinel.dev`.

---

## What this plan deliberately does NOT include

- **A second OSS product.** Don't build out novisentinel-anything-else. Stay focused on the core scanner + the SDKs + the extensions. Adding surface area in OSS spreads you thin.
- **Maintainer / contributor recruitment.** Comes later. First, you need traffic; you cannot recruit volunteers to a project nobody knows about.
- **Translations or i18n.** Save for after 5k stars.
- **OSS forum / mailing list.** GitHub Discussions is enough until you've outgrown it. Don't pre-build community infrastructure.
- **Conference talks.** Save for when you have 1k+ stars and a story to tell. Pitching too early is exhausting and a low-ROI use of time.
- **Anything in the enterprise BE.** OSS-focused weeks. Your enterprise BE is paid for already; let it sit. Pick it back up after week 12.

---

## Definition of success

By end of week 12 (90 days), realistic targets:

| Metric | Conservative | Optimistic |
|---|---|---|
| GitHub stars | 250 | 1,500 |
| PyPI weekly downloads | 50 | 800 |
| VS Marketplace installs | 100 | 2,000 |
| Browser extension installs | 50 | 1,000 |
| Discussions / issues opened by external users | 10 | 100 |
| LinkedIn follower growth (you, personally) | +200 | +2,000 |
| **Enterprise inbound leads attributed to OSS** | 0–2 | 5–20 |

If you hit conservative, you have a real OSS project that justifies continuing investment. If you hit optimistic, you have a wedge.

If you hit *less than* conservative on stars after a real launch effort, that's a signal — either the positioning is wrong, or the moment is wrong, or the OSS scanner isn't the wedge you think it is. Don't keep pouring time in without re-evaluating.

---

## How this connects to the enterprise side

Every OSS user is a potential enterprise lead. The path is:

1. Developer installs the VS Code extension or pip-installs the SDK.
2. They tell their team. The team installs.
3. The team wants to use it in production — at which point they need: multi-provider gateway, cost visibility, policy editor, traces, multi-tenant control plane. (= the enterprise BE.)
4. They contact you for the hosted version.

For this to work, **every OSS surface needs to have a non-pushy "and if you're putting this in front of real LLM traffic..." link** to the enterprise landing page. Examples:

- VS Code extension README → "Looking to manage every LLM request your company makes? See novisentinel.dev/pricing."
- Python SDK docstring → similar.
- Playground page → "This playground runs the OSS scanner. The hosted gateway adds [...]."
- Dashboard local-mode → small banner: "running in single-tenant mode."

The conversion path is what makes the OSS investment pay rent. Without it, you have a hobby project.
