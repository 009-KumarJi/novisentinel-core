# 01 — Launch Prep

**Repo hygiene before going public.** Do all of this before any launch post is written. The goal: a developer arriving from Hacker News in week 7 sees a polished, trustworthy repo, not a half-finished one.

**Effort:** ~1 week, one engineer.
**Depends on:** nothing.
**Gate to:** every other process plan + the launch.

---

## F-101 — README rewrite

**Phase:** Launch prep · **Effort:** XS · **Status:** `[x]` — done in this conversation (the file is fresh).

Verify the README:
- [x] Removes competitor positioning (Lakera Guard reference gone)
- [x] Opens with a 1-sentence positioning + 30-second example
- [x] Lists detectors with latencies
- [x] Has install + quickstart in the first 50 lines
- [x] References the VS Code extension and dashboard

If you change the README in a subsequent commit, re-verify each of the above.

---

## F-102 — `.env.example` audit

**Phase:** Launch prep · **Effort:** XS · **Depends on:** —

**Goal:** A new user runs `cp .env.example .env && docker compose up` and the API comes up green on first try.

### Tasks

- [ ] **T1.** Open `.env.example`. Confirm every key documented in the README's "Configuration" section is present with a sensible default.
- [ ] **T2.** Add comments above each section explaining what the keys are for (`# --- Database ---`, `# --- ML models ---`, etc.).
- [ ] **T3.** Confirm the default `MASTER_API_KEY` is a placeholder that the app refuses to start with in non-dev (`dev-master-key` is already wired this way in `app/main.py:23`).
- [ ] **T4.** Add a top-of-file comment: `# Copy to .env and edit. Defaults are dev-safe; change MASTER_API_KEY for prod.`
- [ ] **T5.** Test: fresh clone in a tmp directory, `cp .env.example .env`, `docker compose up`. API answers `/healthz` within 60s.

### Acceptance

- `cp .env.example .env && docker compose up` works on a clean clone, on macOS, Linux, and Windows (via WSL).
- Every env var the codebase reads has a documented default or required-without-default warning.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 — 2026-05-11 [ ] T5 (manual: docker compose test)

---

## F-103 — GitHub Actions CI

**Phase:** Launch prep · **Effort:** S · **Depends on:** —

**Goal:** Every push to `main` and every PR runs `pytest`, lint, and type-check. Green badge on the README.

### Tasks

- [ ] **T1.** Create `.github/workflows/ci.yml`. Trigger on push to `main` and on `pull_request`.
- [ ] **T2.** Job: `test`. Runs on `ubuntu-latest`. Steps:
  - Checkout
  - Set up Python 3.11
  - `pip install -r requirements.txt`
  - Download spaCy model: `python -m spacy download en_core_web_lg` (cached)
  - `pytest tests/ -v`
- [ ] **T3.** Job: `lint`. Runs `ruff check .` (you have `ruff.toml` — wire it).
- [ ] **T4.** Cache the pip wheels and the spaCy model across runs (first run is ~5 min; cached is ~1 min).
- [ ] **T5.** Add a status badge to the top of the README: `![CI](https://github.com/009-KumarJi/novi-sentinel/actions/workflows/ci.yml/badge.svg)`.
- [ ] **T6.** Open a PR with an intentional test failure to verify CI catches it. Then revert.

### Files

| Action | Path |
|---|---|
| create | `.github/workflows/ci.yml` |
| edit   | `README.md` (add badge) |

### Acceptance

- `pytest` runs green in CI on a fresh clone.
- A PR with a failing test gets a red CI check.
- The README badge shows the live CI state.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 — 2026-05-11 [ ] T5 (add badge — needs CI to run first) [ ] T6 (manual: open a failing PR)

---

## F-104 — Issue and PR templates

**Phase:** Launch prep · **Effort:** XS · **Depends on:** —

**Goal:** When external users open issues / PRs, they fill in a template that gives you triage signal. Saves time.

### Tasks

- [ ] **T1.** Create `.github/ISSUE_TEMPLATE/bug.yml` (form schema):
  - Fields: title, what happened, what was expected, repro steps, environment (OS, Python version, NoviSentinel version), logs.
- [ ] **T2.** Create `.github/ISSUE_TEMPLATE/feature.yml`:
  - Fields: title, problem you're solving, what you'd like, alternatives considered.
- [ ] **T3.** Create `.github/ISSUE_TEMPLATE/question.yml`:
  - Note at top: "Got a question? Prefer [Discussions](https://github.com/009-KumarJi/novi-sentinel/discussions)."
  - Minimal fields.
- [ ] **T4.** Create `.github/ISSUE_TEMPLATE/config.yml` to add a Discussions link to the "Choose a template" page.
- [ ] **T5.** Create `.github/PULL_REQUEST_TEMPLATE.md`:
  - Checklist: linked issue, tests added, docs updated, CHANGELOG entry.
- [ ] **T6.** Test by opening a draft issue / PR in the UI; confirm the template renders.

### Acceptance

- Clicking "New Issue" on GitHub shows the three templates.
- Opening a PR pre-fills the template.

### Status

- [x] T1 [x] T2 [x] T3 [x] T4 [x] T5 [x] T6 — 2026-05-11 (yml format templates created)

---

## F-105 — Dependabot

**Phase:** Launch prep · **Effort:** XS · **Depends on:** F-103

**Goal:** Automated PRs for outdated Python deps, GitHub Actions, and (after F-104 from VS Code plan) npm deps. Prevents the "abandoned-looking" smell of stale dependency versions.

### Tasks

- [ ] **T1.** Create `.github/dependabot.yml`:
  - `package-ecosystem: pip` for `/`
  - `package-ecosystem: github-actions` for `/`
  - `package-ecosystem: npm` for `/dashboard` and `/extensions/vscode` (once those have lockfiles)
  - Schedule: `weekly`, day `monday`
  - Open at most 5 PRs at a time per ecosystem.
- [ ] **T2.** Set label `dependencies` on Dependabot PRs so they're easy to bulk-triage.

### Acceptance

- Within a week of adding the file, Dependabot opens at least one PR (or confirms everything's up to date).

### Status

- [x] T1 [x] T2 — 2026-05-11

---

## F-106 — TRADEMARK.md

**Phase:** Launch prep · **Effort:** XS · **Depends on:** —

**Goal:** Declare that "NoviSentinel" is your trademark even though the code is Apache-licensed. Doesn't have legal force on its own, but sets community expectation.

### Tasks

- [ ] **T1.** Create `TRADEMARK.md` at repo root with text like:
  ```
  # Trademark Policy

  "NoviSentinel" and the NoviSentinel logo are trademarks of Kumar Ji.

  Apache License 2.0 covers the **code** in this repository. It does
  not grant rights to the NoviSentinel name or logo. You may:

  - Refer to NoviSentinel by name in documentation, blog posts,
    comparisons, and technical articles. This is fair use.
  - Use a derived name on a personal fork ("my-novisentinel-fork")
    in a non-commercial context.

  You may not:

  - Distribute a commercial product or service using "NoviSentinel" in
    its name or branding without written permission.
  - Use the NoviSentinel logo without written permission.
  - Imply official endorsement by the NoviSentinel project.

  For permission requests: <contact email>
  ```
- [ ] **T2.** Add a `TRADEMARK` link in the README footer next to the License.

### Acceptance

- File exists and is linked from the README.

### Status

- [x] T1 [x] T2 — 2026-05-11

---

## F-107 — SECURITY.md verification

**Phase:** Launch prep · **Effort:** XS · **Depends on:** —

**Goal:** Confirm the existing `SECURITY.md` has a working disclosure email and a 48h ack commitment.

### Tasks

- [ ] **T1.** Read the existing `SECURITY.md`. Confirm:
  - The disclosure email is one you actually check daily.
  - There's a stated SLA for first response (48h is industry standard).
  - There's a stated SLA for fix (90 days is industry standard).
  - There's a note about coordinated disclosure.
- [ ] **T2.** Test the email: send a dummy "test disclosure" from a different account. Reply within 24h.
- [ ] **T3.** Enable GitHub Security Advisories in the repo's Security tab (one click). This lets researchers report privately through GitHub.

### Acceptance

- The email works, the SLA is realistic, and GitHub Security Advisories are enabled.

### Status

- [x] T1 — 2026-05-11 (SECURITY.md has 48h ack, 30-day fix, disclosure policy) [ ] T2 (manual: send test email) [ ] T3 (manual: GitHub Security Advisories toggle)

---

## F-108 — v1.0.0 tagged release

**Phase:** Launch prep · **Effort:** XS · **Depends on:** F-102, F-103

**Goal:** The repo has a real GitHub Release at `v1.0.0` with notes derived from `CHANGELOG.md`. Release events create RSS items and trigger ecosystem trackers.

### Tasks

- [ ] **T1.** Verify `CHANGELOG.md` is current (you already have `## [1.0.0] — 2026-05-07`). Update the date if needed.
- [ ] **T2.** Tag the current HEAD: `git tag -a v1.0.0 -m "v1.0.0 — initial public release"`. Push: `git push origin v1.0.0`.
- [ ] **T3.** Create a GitHub Release from the tag. Copy the `[1.0.0]` section of `CHANGELOG.md` into the release notes. Add a "What's next" paragraph linking to the VS Code extension and Python SDK.
- [ ] **T4.** Attach the source tarball + zipball (GitHub does this automatically).
- [ ] **T5.** Tweet / LinkedIn-post the release? — **No, not yet.** This release is the artifact that exists *for* the launch later; don't announce it standalone.

### Acceptance

- `https://github.com/009-KumarJi/novi-sentinel/releases/tag/v1.0.0` returns a real release page with notes.

### Status

- [ ] T1 [ ] T2 [ ] T3 [ ] T4 [ ] T5

---

## F-109 — Clean-clone smoke test

**Phase:** Launch prep · **Effort:** XS · **Depends on:** F-102

**Goal:** A developer with nothing installed but Docker can go from zero to a working scan in 5 minutes. Test it.

### Tasks

- [ ] **T1.** On a fresh machine (or a fresh Docker volume), clone the repo.
- [ ] **T2.** `cp .env.example .env && docker compose up`.
- [ ] **T3.** Wait for `Application startup complete.` in the logs.
- [ ] **T4.** `curl -X POST http://localhost:8000/v1/scan -H "Authorization: Bearer dev-master-key" -H "Content-Type: application/json" -d '{"text":"My SSN is 123-45-6789"}'`. Expect a `block` action with a PII detection.
- [ ] **T5.** Visit `http://localhost:8000/docs`. Confirm Swagger UI loads.
- [ ] **T6.** Visit `http://localhost:3001`. Confirm dashboard loads (after `F-301` is done, otherwise note as known).
- [ ] **T7.** Document any rough edges encountered. File issues for each. Fix the showstoppers before launch.

### Acceptance

- Time from `git clone` to first successful scan ≤ 5 minutes.
- No "you need to install X separately" gotchas surface during the run.

### Status

- [ ] T1 [ ] T2 [ ] T3 [ ] T4 [ ] T5 (manual: git tag + GitHub release)

---

## F-110 — Eval corpus stub

**Phase:** Launch prep · **Effort:** S · **Depends on:** —

**Goal:** Before the launch, have at least a small published evaluation set so when someone asks "how accurate is the injection detector?" you have a real answer.

### Tasks

- [ ] **T1.** Create `eval/` directory at repo root.
- [ ] **T2.** Build a tiny seed corpus (`eval/datasets/injection_seed.jsonl`):
  - 50 known prompt injections (positive class) — sourced from publicly available datasets (e.g. deepset/prompt-injections, lakera-guard public examples, etc. — credit sources in a `SOURCES.md`).
  - 50 benign prompts (negative class) — sourced from public chat datasets.
- [ ] **T3.** Same for PII (`eval/datasets/pii_seed.jsonl`) — 30 positive (synthetic SSNs, emails, etc.), 30 negative.
- [ ] **T4.** Same for secrets (`eval/datasets/secrets_seed.jsonl`) — 30 positive (revoked test keys from public dumps), 30 negative.
- [ ] **T5.** Create `eval/run.py` — loads each dataset, calls `/v1/scan`, computes precision / recall / F1 per detector.
- [ ] **T6.** Run the eval. Document the numbers in `eval/RESULTS.md`. Be honest — if precision is 0.78, write 0.78.
- [ ] **T7.** Add an `eval/README.md` explaining how to reproduce.

### Acceptance

- `python eval/run.py` runs end-to-end and outputs a table of precision/recall/F1.
- `eval/RESULTS.md` documents current numbers.
- README links to `eval/RESULTS.md` from a new "Accuracy" subsection.

### Status

- [ ] T1 [ ] T2 [ ] T3 [ ] T4 [ ] T5 [ ] T6 [ ] T7 (manual: requires live API)

---

## F-111 — Code-of-Conduct enforcement note

**Phase:** Launch prep · **Effort:** XS · **Depends on:** —

**Goal:** You have a `CODE_OF_CONDUCT.md`. Add a one-line note about how violations are reported. Without that, the CoC is decorative.

### Tasks

- [ ] **T1.** Open `CODE_OF_CONDUCT.md`. Find the "Enforcement" or "Reporting" section.
- [ ] **T2.** Confirm it has: a real email, a stated response time (48h), and a stated set of consequences (warning / temporary ban / permanent ban).
- [ ] **T3.** If missing, add. Use the Contributor Covenant v2.1 enforcement language — it's standard.

### Acceptance

- `CODE_OF_CONDUCT.md` has a working reporting path.

### Status

- [x] T1 [x] T2 [x] T3 — 2026-05-11 (48h SLA + warning/ban consequences added to CoC)

---

## F-112 — Pre-launch checklist

**Phase:** Launch prep · **Effort:** XS · **Depends on:** all of F-101..F-111

**Goal:** A single page that says "everything is ready, go."

### Tasks

- [ ] **T1.** Create `plans/process-plans/launch-checklist.md` (this is a stub; expand on launch week):
  - [ ] README final pass
  - [ ] PyPI package published (F-203)
  - [ ] VS Marketplace extension published (F-410)
  - [ ] Examples directory complete (F-505 onwards)
  - [ ] Dashboard playground deployed at `play.novisentinel.dev` (F-310)
  - [ ] Eval results published (F-110)
  - [ ] Launch post drafted (HN + LinkedIn + dev.to + X)
  - [ ] Demo video recorded
  - [ ] 10 friends primed to star within 30 min of launch
- [ ] **T2.** Day of launch: walk down the list. Anything unchecked stops the launch.

### Acceptance

- File exists. On launch day, every line is checked.

### Status

- [ ] T1 [ ] T2

---

## Done condition for this plan

Phase complete when F-101 through F-111 are all `[x]`. F-112 sits as a living checklist past that point.
