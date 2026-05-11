# 01 — OSS vs Enterprise Strategy

**The one decision that drives everything else: which capabilities live in `novisentinel-core` (OSS, Apache 2.0, anyone can self-host) vs `novisentinel-be` (enterprise, hosted, paid).**

This document gives you a framework, an answer, and a feature-by-feature matrix.

---

## 1. The framework — what should be OSS

A capability belongs in OSS if **all four** of the following are true. If any of them isn't, it belongs in enterprise.

1. **It's table-stakes, not differentiated.** Detectors exist in a dozen open libraries (Presidio, detoxify, regex secret scanners, prompt-injection classifiers on HuggingFace). They're commoditizing fast. Keeping them closed buys you nothing.
2. **A single developer can use it locally.** If it only makes sense at multi-tenant scale (billing, SSO, SOC2), it's enterprise.
3. **Closing it would hurt adoption more than it helps revenue.** Closing the scanner means competitors fork an open alternative and your enterprise loses its trojan-horse distribution. Closing billing costs you nothing.
4. **It's the thing the developer integrates first.** The integration moment is where you earn or lose them. Whatever they touch first should be free, low-friction, and self-hostable.

By the same logic, a capability belongs in enterprise if **any** of these is true:

- It's where you have **architectural leverage** that competitors can't replicate cheaply (the gateway + policy engine + observability + accounting bundle is exactly this).
- It only matters at **organizational scale** (orgs, users, scoped keys, SAML, audit, RBAC).
- It's about **trust at scale** (SOC2, EU residency, retention controls, billing).
- It's **operational complexity customers will pay to avoid** (multi-provider failover, cost attribution, eval pipelines, hosted control plane).

---

## 2. The split — one-line answer

> **OSS is "scan one text for safety problems."**
> **Enterprise is "manage every LLM request your company makes."**

OSS gives you: scan an input, get back PII / injection / secrets / toxicity verdicts. Self-host it. Drop it into your code. The unit is **the scan call**.

Enterprise gives you: a hosted gateway that fronts every LLM provider, applies the OSS scanner as a privileged default policy, attributes cost, traces every request, lets you write policies, fails over between providers, etc. The unit is **the LLM request**.

A developer comes for the scanner. An organization pays for the gateway.

---

## 3. The model — open-core, not BSL

There are roughly four ways to license an OSS product:

| Model | Examples | What it means | Right for you? |
|---|---|---|---|
| **Pure Apache / MIT** | Kubernetes, React, FastAPI | Anyone can do anything. Including build a competitor on top. | ❌ Risky for solo founder with monetization ambition — AWS-style competition is the worst case. |
| **Open-core** | GitLab, Elastic (pre-2021), MongoDB (pre-2018), PostHog, Supabase | Free OSS for the core. Proprietary "Enterprise" features layered on top. | ✅ **This is the right model for you.** |
| **BSL (Business Source License)** | HashiCorp Terraform, Sentry, Couchbase, MariaDB | Source-available. Free for non-production / non-competing use. Converts to OSS after N years. | Plausible alternative. More restrictive — less community goodwill. |
| **Source-available / commercial** | Redis (post-2024), Elastic (post-2021) | Source visible but commercial use restricted. | Last resort. Wait until OSS has caught fire and a hyperscaler is about to fork it. |

You're already on **Apache 2.0** for `novisentinel-core` (see `LICENSE`). Keep it. The trick to making open-core work isn't licensing — it's the *line* between OSS and enterprise. Get the line right and Apache is fine; get it wrong and even BSL won't save you.

The line you want:

- **OSS is everything a single developer / team needs to run a safe LLM in a single environment.**
- **Enterprise is everything an organization needs to manage many environments, many providers, many users, and many compliance requirements at once.**

That line is **defensible**. A hyperscaler can fork the OSS scanner, but they can't usefully fork it without also building the multi-tenant control plane, the billing system, the policy engine, the trace inspector, the compliance plumbing. By the time they've done that, they've built a competing product, not commoditized yours.

---

## 4. The feature matrix

This is the single most important table in this folder. Print it. Pin it. Re-read it whenever you're tempted to move the line.

`✅ OSS` = in the OSS repo, Apache-licensed, self-hostable.
`💼 Ent` = enterprise-only.
`✅ + 💼` = the OSS version is the simple/single-tenant form; the enterprise version is the multi-tenant / scaled form.

### Scanner core

| Feature | Where | Why |
|---|---|---|
| PII detection (Presidio) | ✅ OSS | Table stakes. Already free elsewhere. |
| Prompt injection detection (regex + ML) | ✅ OSS | Same. |
| Secrets detection (regex bank) | ✅ OSS | Same. |
| Toxicity detection (Detoxify) | ✅ OSS | Same. |
| Code-injection detection | ✅ OSS | Same — small, lightweight, no reason to gate. |
| URL safety (suspicious patterns, *not* Google Safe Browsing) | ✅ OSS | Pattern logic OSS. Google Safe Browsing key gated to enterprise. |
| `POST /v1/scan` and `/v1/scan/batch` | ✅ OSS | The integration surface. Has to be free. |
| Detector skip / threshold tuning per request | ✅ OSS | Without this, the API is unusable. |
| Async + sync execution, parallel detectors | ✅ OSS | Performance is a feature; OSS users feel performance. |

### Detection depth (advanced)

| Feature | Where | Why |
|---|---|---|
| Multilingual support | ✅ OSS | Important globally; gating hurts community. |
| Topic / off-topic detection | 💼 Ent | Needs eval data + tuning; harder to ship as OSS without a feedback loop. |
| Grounding / hallucination detection | 💼 Ent | Requires context-doc upload + eval harness; not single-developer-friendly. |
| Google Safe Browsing integration | 💼 Ent | We pay for the API key; can't give it away. |
| Custom org-defined HTTP detectors | 💼 Ent | Multi-tenant by nature. |
| Detector confidence calibration (versioned model artifacts) | 💼 Ent | The artifacts come from our eval pipeline. OSS users get unversioned baseline. |
| Active learning loop | 💼 Ent | Needs the feedback data our hosted users generate. |
| Eval harness (F-501) | 💼 Ent | Internal QA infrastructure, not a developer-facing tool. |

### LLM gateway (the wedge)

| Feature | Where | Why |
|---|---|---|
| `/v1/chat/completions` OpenAI-compat ingress | 💼 Ent | **This is the paid product.** Don't OSS this — it's where the value is. |
| Multi-provider egress (8 providers) | 💼 Ent | Same. |
| Streaming pass-through | 💼 Ent | Same. |
| Token + cost accounting | 💼 Ent | Same. |
| Retries + circuit breakers + provider health routing | 💼 Ent | Same. |
| Provider fallback (one-hop) | 💼 Ent | Same. |
| Anthropic-shape egress | 💼 Ent | Same. |

There is **one exception** to consider — and you should think about it: a *very minimal* gateway shim in OSS that proxies one provider with no observability, just so OSS users can experience the "drop-in base_url" feeling locally. This is a marketing decision, not a technical one. Lean **no for now** — the scanner is enough to get them adopted; the gateway is what they pay for.

### Policies

| Feature | Where | Why |
|---|---|---|
| Inline per-request config (`config: { injection_threshold: ... }`) | ✅ OSS | Already in `scan.py`. Keep. |
| Per-key policies stored in DB (JSONB) | 💼 Ent | Needs multi-tenant key model. |
| Policy DSL (declarative YAML/JSON rules engine) | 💼 Ent | The paid differentiator. Strict no on OSS. |
| Routing rules / fallback rules / cost-aware routing / compliance routing | 💼 Ent | Same. |
| Policy bundles (preset templates) | 💼 Ent | Same — these are part of the enterprise editor experience. |
| Custom regex rules / allow-deny lists | 💼 Ent | Same. |

### Agent & tool security

| Feature | Where | Why |
|---|---|---|
| Tool-call argument scanning (call-site, OSS user implements) | ✅ OSS (via SDK examples) | Show how to scan tool args using `/v1/scan`. |
| Tool-call output scanning (same) | ✅ OSS (via SDK examples) | Same. |
| MCP request scanning at gateway level | 💼 Ent | Needs the gateway. |
| Agent-loop budgets (max iters / tools) | 💼 Ent | Needs orchestration state. |
| Function/tool allow-lists at gateway | 💼 Ent | Needs the gateway. |

### Identity & multi-tenant

| Feature | Where | Why |
|---|---|---|
| Master API key | ✅ OSS | Single-tenant only. |
| Per-installation API keys (hashed, basic CRUD) | ✅ OSS | Just enough for a small team. |
| Webhooks (HMAC-signed) | ✅ OSS | Community-table-stakes integration. |
| Scan logs (SHA-256 hashed, no raw text) | ✅ OSS | Trust signal — show the discipline. |
| Stats endpoint | ✅ OSS | Same. |
| Per-key rate limits | ✅ OSS | Same. |
| Organizations & users | 💼 Ent | Multi-tenant; no value at single-tenant. |
| OAuth / OIDC sign-in | 💼 Ent | Same. |
| Scoped API keys (16 scopes) | 💼 Ent | Same. |
| IP allow-list per key | 💼 Ent | Same. |
| SAML SSO | 💼 Ent | Enterprise procurement. |
| RBAC roles | 💼 Ent | Same. |

### Observability

| Feature | Where | Why |
|---|---|---|
| Prometheus `/metrics` endpoint | ✅ OSS | Free, expected, builds trust. |
| Structured logging + request IDs | ✅ OSS | Same. |
| Real health checks (`/healthz`, `/readyz`, `/health`) | ✅ OSS | Same. |
| Audit log for admin actions | ✅ OSS | Same — show the trust pattern. |
| Per-request trace inspector | 💼 Ent | Needs the gateway. |
| Latency / cost / error timeseries | 💼 Ent | Needs the gateway + accounting. |
| Blocked-attack feed | 💼 Ent | Needs persistent storage + UI. |
| Model comparison view | 💼 Ent | Needs the gateway. |
| Prompt analytics / clustering | 💼 Ent | Needs eval infra. |
| Datadog / Splunk forwarding | 💼 Ent | Enterprise integration. |

### Enterprise & scale

All 💼 Ent. No exceptions:
- arq background workers
- GPU inference path
- Stripe billing
- Data retention controls
- On-prem / Helm chart (this is sold separately to enterprise; do **not** OSS the Helm chart even though it deploys OSS components — the value is the chart's tuning, not the binaries)
- SOC2 evidence pipeline
- EU region deployment

### Developer experience (your real moat in OSS)

| Feature | Where | Why |
|---|---|---|
| Python SDK | ✅ OSS | The integration moment. Publish to PyPI. |
| Node / TypeScript SDK | ✅ OSS | When demand emerges. Skip for now per `nifty-dawn`. |
| VS Code extension | ✅ OSS | The single highest-leverage OSS distribution channel. Build it. |
| Browser extension (ChatGPT.com, Claude.ai injection) | ✅ OSS | Phase 3 of `nifty-dawn`. Big LinkedIn moment when it lands. |
| Docker Compose (one-line boot) | ✅ OSS | Already done. Keep polished. |
| Postman collection | ✅ OSS | Already done. |
| Example wrappers (OpenAI, Anthropic, LangChain, Ollama) | ✅ OSS | Per `nifty-dawn` Phase 2. Critical. |
| Public playground at `play.novisentinel.dev` | 💼 Hosted (free) | Free public service that runs the OSS API. Pumps traffic to the GitHub repo. |
| Mini dashboard (single-tenant, local) | ✅ OSS | The Next.js dashboard already in `dashboard/` — keep it tightly scoped to local-single-tenant use. |
| Multi-tenant dashboard | 💼 Ent | Separate `novisentinel-fe` repo. Don't merge. |

---

## 5. The moat

If you put everything in OSS, you have no moat. If you put nothing in OSS, you have no distribution. The split above gives you both:

**OSS moat (defensibility through community):**
- VS Code extension installed by 10k+ developers → those developers are *your* recruits when their company asks "how do we make our AI safer?"
- LinkedIn / HN credibility — the project's existence is your résumé and your sales tool.
- Talent pipeline — contributors who become candidates.
- Distribution — when LangChain integrates against you (because Apache makes it easy), every LangChain user is downstream of you.

**Enterprise moat (defensibility through complexity):**
- The gateway / policy / observability bundle is months of engineering to replicate. A fork can't catch up casually.
- Hosted operational expertise (24/7 ops, EU residency, SOC2). Self-hosting OSS doesn't get you SOC2.
- Cost attribution accuracy (X-4 from the master plan). Customers trust your numbers because you do the work to keep them right.
- The policy editor + dry-run + bundle gallery — a UX investment that's not in the OSS scope.

The two moats reinforce each other. Open source generates demand; enterprise captures revenue. Lose either side and the model collapses.

---

## 6. Things to *not* OSS, no matter how much someone asks

You will get GitHub issues that say "please open-source the gateway / the policy engine / the trace inspector / the dashboard." Answer: **no, but the API is documented and your scanner is free.**

Specifically, hold the line on:

- **The gateway** (`/v1/chat/completions` ingress). This is the paid product.
- **The policy DSL engine.** This is the differentiator.
- **The multi-tenant control plane** (orgs, users, OAuth, SAML, billing).
- **The trace inspector, attack feed, cost dashboard UI.** These are the enterprise FE.
- **The hosted service operations** (alerts, on-call, EU region, status page).

If you OSS any of these, you cannibalize the business. The enterprise BE is roughly 6 months of work. You don't give that away because someone on Twitter is mad.

---

## 7. Things you *should* OSS, even though it feels scary

- **The detectors.** They commoditize. Open-sourcing them is the only way to make sure your scanner becomes the default lingua franca rather than a competitor's.
- **The Python SDK.** Should be `pip install novisentinel` against the OSS API. Free.
- **The VS Code extension.** Free. This is your daily-use marketing.
- **Webhooks.** Free.
- **A "Hello, blocked!" demo + a 90-second video.** Free. These are your top-of-funnel.

If something feels like it could be enterprise but mostly serves to make OSS users feel productive, lean **OSS**. The cost of giving away one feature is much smaller than the cost of being seen as a "fake OSS" project that holds back the basics.

---

## 8. How to handle "but our competitor will copy this!"

You're right. They will. But:

- Your competitors are not Lakera or Protect AI. Those companies are enterprise-only, closed-source, and don't have a community. You will out-distribute them in the OSS market.
- The companies that *will* copy you are folk projects on GitHub — random forks, hobby projects. They have no enterprise side, no support, no SOC2, no roadmap. They are noise, not threat.
- The hyperscaler risk (AWS taking your code and offering it as a managed service) only kicks in at much larger scale than you're at. By then you'll have BSL'd if you need to.

The bigger risk is **not having enough community to matter**. Build the OSS first. Worry about competition later.

---

## 9. Recap (the only paragraph you need to memorize)

**OSS is the scanner: detectors + `/v1/scan` + Python SDK + VS Code extension + local single-tenant dashboard + webhooks + Docker Compose. Apache 2.0. Free forever. The scanner is the wedge — developers integrate it, learn to trust it, and become advocates inside their companies.**

**Enterprise is the gateway: `/v1/chat/completions` + 8 providers + cost accounting + policy engine + multi-tenant orgs + SAML + observability + hosted control plane. Closed source. Paid. The gateway is the business — companies pay for managed traffic and managed safety at scale.**

**The OSS scanner makes the enterprise gateway easy to sell because customers already trust the technology and the brand. The enterprise gateway funds the OSS scanner's continued development. Neither survives alone.**

That's the whole model.
