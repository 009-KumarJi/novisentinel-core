# NoviSentinel — Plans

Everything in this folder is meant to be **read by future-you** or **executed by Sonnet** (your Claude Code instance).

## Layout

```
plans/
├── README.md                          ← you are here
│
├── oss-section-doc/                   ← strategic — read once a quarter
│   ├── README.md                      Index, time-allocation note
│   ├── 01-STRATEGY.md                 OSS vs enterprise, feature matrix, moat
│   ├── 02-ROADMAP.md                  90-day plan, critique of nifty-dawn
│   ├── 03-DISTRIBUTION.md             HN / LinkedIn / dev community tactics
│   └── 04-OSS_101.md                  Licenses, governance, security, burnout
│
└── process-plans/                     ← tactical — Sonnet executes these
    ├── README.md                      How Sonnet uses these
    ├── 01-LAUNCH_PREP.md              Repo hygiene before public launch
    ├── 02-PYTHON_SDK.md               SDK polish + PyPI publish
    ├── 03-DASHBOARD.md                Playground page + single-tenant polish
    ├── 04-VSCODE_EXTENSION.md         Full extension build (src/ is empty today)
    ├── 05-EXAMPLES.md                 OpenAI / Anthropic / LangChain / Ollama wrappers
    └── 06-BROWSER_EXTENSION.md        ChatGPT.com / Claude.ai injection (Phase 3)
```

## Which file when

- **About to make a strategic call** (license, what's OSS, when to launch) → `oss-section-doc/`.
- **About to write code** (extension, SDK, dashboard) → `process-plans/`.
- **About to write a launch post** → `oss-section-doc/03-DISTRIBUTION.md`.
- **Hit a maintainer problem** (security disclosure, burned-out, trademark) → `oss-section-doc/04-OSS_101.md`.

## The order to execute process-plans

Follow `01-LAUNCH_PREP.md` first — it's the gate. The others can run in this rough order:

```
01 LAUNCH_PREP   ──┐
02 PYTHON_SDK    ──┼── all done by week 2
                   ┘
03 DASHBOARD     ── week 3
04 VSCODE        ── weeks 4–5  (★ wedge — biggest single piece)
05 EXAMPLES      ── week 6
                              ── LAUNCH HERE ──
06 BROWSER       ── weeks 10–12 (post-launch)
```

This matches the 90-day cadence in `oss-section-doc/02-ROADMAP.md`. If your timeline shifts, the dependency order still holds: SDK before examples, extension before launch, browser extension only after the rest is stable.

## What's not in here

- **Strategic re-framings.** When the OSS/enterprise line moves, update `01-STRATEGY.md`, don't write a new doc.
- **Per-PR task lists.** Each process plan has checkboxes — work against those, don't create parallel tracking.
- **Marketing copy.** `03-DISTRIBUTION.md` has the templates; resist the urge to write polish docs.

Keep this folder lean. Add files only when an actual decision or buildable task needs to live somewhere durable.
