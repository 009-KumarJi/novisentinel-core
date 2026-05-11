# NoviSentinel — Process Plans

**For:** Sonnet (the Claude Code instance executing these), and future-you reviewing what got shipped.

This folder is the per-component task list for the OSS work. It mirrors the enterprise side's `BE_PROCESS_PLAN.md` / `FE_PROCESS_PLAN.md` style: every feature has explicit tasks with checkboxes, files to touch, acceptance criteria, and a status entry that gets ticked off as work lands.

---

## How Sonnet uses these files

1. **Pick a feature.** Look up its ID in the relevant file. If it depends on an earlier feature that's not done, do that one first.
2. **Open the feature entry.** Read goal, dependencies, tasks, files.
3. **Execute tasks in order.** Each task has an explicit acceptance criterion. If a task's scope is unclear, write a 1-page design note in `plans/notes/<feature-id>.md` before coding.
4. **Update status.** After every task, change the checkbox and append `— YYYY-MM-DD — <sha>`. Never delete a task entry — completed tasks stay as history.
5. **Run the acceptance check.** Don't mark a feature done until *every* acceptance bullet passes.

### Status legend

| Marker | Meaning |
|--------|---------|
| `[ ]`  | Not started |
| `[~]`  | In progress |
| `[x]`  | Done — append `— YYYY-MM-DD — <sha>` |
| `[!]`  | Blocked — append `— <reason>` |
| `[/]`  | Dropped — append `— <reason>` (rare; explain in commit message) |

### Working rules

- **One feature per branch.** Branch names: `feature/<plan>-<F-ID>-<slug>` (e.g. `feature/vscode-F-401-chat-participant`).
- **One task per commit, ideally.** Use Conventional Commits.
- **Update the plan in the same commit as the code.** The status tick lives next to the work.
- **No silent scope expansion.** If a task uncovers extra work, add a new task to the feature with a `[ ]` and explain why in the commit message.
- **Tests-as-acceptance.** If acceptance says "X works," there must be a test that proves it. Manual verification is acceptable only for UI-adjacent surfaces (extension, dashboard).

---

## Feature ID scheme

To stay aligned with the enterprise plan's ID convention, OSS features use a `F-<prefix><digits>` scheme:

| Prefix | Domain |
|---|---|
| `F-1xx` | Repo hygiene / launch prep |
| `F-2xx` | Python SDK |
| `F-3xx` | Dashboard |
| `F-4xx` | VS Code extension |
| `F-5xx` | Examples |
| `F-6xx` | Browser extension |

These IDs are **stable** — they don't change between plan revisions.

---

## Active plans

| File | Phase | Status | Headline |
|---|---|---|---|
| [`01-LAUNCH_PREP.md`](01-LAUNCH_PREP.md) | Pre-launch | `[ ]` | README rewrite, CI, v1.0 tag, repo hygiene |
| [`02-PYTHON_SDK.md`](02-PYTHON_SDK.md) | Pre-launch | `[ ]` | Polish, PyPI publish |
| [`03-DASHBOARD.md`](03-DASHBOARD.md) | Pre-launch | `[ ]` | Playground page, single-tenant polish |
| [`04-VSCODE_EXTENSION.md`](04-VSCODE_EXTENSION.md) | Pre-launch ★ | `[ ]` | Full build — extensions/vscode/src/ is empty today |
| [`05-EXAMPLES.md`](05-EXAMPLES.md) | Pre-launch | `[ ]` | OpenAI / Anthropic / LangChain / Ollama wrappers |
| [`06-BROWSER_EXTENSION.md`](06-BROWSER_EXTENSION.md) | Post-launch | `[ ]` | ChatGPT / Claude.ai injection |

★ = wedge feature — the single biggest piece of OSS distribution work.

---

## What's in scope, what's not

**In scope for the OSS process plans:**
- Code that lives inside `novisentinel-core/`
- Code that becomes a published artifact tied to OSS (PyPI package, VS Marketplace extension, Chrome Web Store extension)
- The local single-tenant dashboard
- Examples that show how to integrate the OSS scanner

**Out of scope** (these live elsewhere):
- Enterprise BE features — see `novisentinel-be/plans/BE_PROCESS_PLAN.md`
- Enterprise FE features — see `novisentinel-fe/plans/FE_PROCESS_PLAN.md` and `FE_ARCHITECTURAL_PHASES.md`
- Marketing site, landing page, docs site — separate concerns
- Strategic decisions about OSS/enterprise split — see `plans/oss-section-doc/01-STRATEGY.md`

If a task feels like it crosses into the enterprise side, stop and check the strategy doc before continuing.
