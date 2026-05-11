# NoviSentinel OSS — Strategy & Playbook

**For:** Krishna (founder)
**Date:** 2026-05-11
**Context:** You have a complete enterprise NoviSentinel (BE + FE + dashboard). This repo (`novisentinel-core`) is the OSS half of that work. You're new to running an open-source project and want to grow it into something the dev community actually uses, partly so it does sales work for the enterprise product, partly because it'll do good things for your reputation and reach (LinkedIn, community, talent).

This folder is the playbook.

---

## Read in this order

1. **[01-STRATEGY.md](01-STRATEGY.md)** — *What goes in OSS, what stays enterprise, and why.*
   - The single most important file. Once this is decided, everything else flows.
   - Includes a feature-by-feature matrix.
   - **Read this first. Don't skip.**

2. **[02-ROADMAP.md](02-ROADMAP.md)** — *What to build in the next 30 / 60 / 90 days.*
   - Reviews your existing `nifty-dawn` plan — what to keep, what to reframe.
   - Concrete weekly milestones.

3. **[03-DISTRIBUTION.md](03-DISTRIBUTION.md)** — *How to actually get users.*
   - LinkedIn launch post template.
   - First HN post strategy.
   - Reddit, dev.to, Hacker News, X, YouTube — what works for OSS, what doesn't.
   - The "first 100 stars" playbook.

4. **[04-OSS_101.md](04-OSS_101.md)** — *Things you need to know that you don't yet.*
   - Licenses (you picked Apache 2.0 — pros/cons, alternatives you should know).
   - What you are now obligated to do (issues, PRs, releases, security disclosures).
   - How OSS founders burn out, and how not to.
   - When OSS makes sense as a moat and when it doesn't.

---

## The one-line summary

> **OSS = the scanner. Enterprise = the gateway.**

OSS gets the developer pasting `pip install novisentinel` or installing the VS Code extension. Once they want to put it in front of every LLM call their app makes (cost, traces, multi-provider, policies), that's the enterprise upgrade. The scanner is the wedge; the gateway is the business.

Everything in `01-STRATEGY.md` is a more careful version of that sentence.

---

## A note on time

You said you're going to spend most of your time on OSS now. That's the right call for a *brand* — but be honest with yourself:

- **OSS is a long game.** First 100 stars is 1-3 months of work, even with a good product. First 1000 is 6-12 months. Don't measure week-over-week and panic.
- **OSS does not pay rent.** Apache-licensed code generates zero revenue directly. The play is: OSS → trust → enterprise sales. If you have no runway for the enterprise side to land customers, the OSS investment is a gamble.
- **You have an enterprise BE already built.** The hardest part of the open-core model — having something to actually sell when OSS users want more — is already done. That's a big advantage. Don't waste it by letting the BE rot while you chase stars.

The middle path is: spend ~70% of your time on OSS for the next 8 weeks, but keep one foot in the enterprise side (FE catch-up per `prod-level-doc/MASTER_FUTURE_PLAN.md`). When OSS gets traction, the leads it generates need somewhere to land.

---

## When to come back to this folder

- **Quarterly** — re-check `01-STRATEGY.md`. Is the OSS/enterprise line still where you want it? Has a customer asked for something OSS that should be enterprise, or vice versa?
- **Before any big public announcement** — re-check `03-DISTRIBUTION.md`. Same tactics, fresh execution.
- **When a maintainer-shaped problem appears** — `04-OSS_101.md`. Burnout, disputes, license drama, security disclosure — that file has the patterns.
