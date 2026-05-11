# 03 — Distribution & Community

**How to get your first 1000 users.**

You said: *"if it works I will share on LinkedIn and make the whole dev community use it."* This document tells you how to make that real.

OSS distribution is its own discipline. Most OSS projects fail not because the code is bad but because the founder didn't do the unglamorous distribution work. The good news: it's a skill you can learn in a month if you're systematic.

---

## The mental model

OSS distribution is a funnel:

```
Awareness (someone hears about the project)
   ↓
Curiosity (they click the link)
   ↓
Trust (they spend 30 seconds and don't bounce)
   ↓
Trial (they install it)
   ↓
Use (they integrate it into something)
   ↓
Advocacy (they tell someone else)
   ↓
Contribution (they file an issue or PR)
```

Each step has a ~10× drop-off. To get 10 contributors you need 100 users. To get 100 users you need 1,000 trials. To get 1,000 trials you need 10,000 people aware. That's the math.

The job is to make every step less leaky than the average OSS project.

---

## Top of funnel — channels ranked

These are the channels that work for OSS in 2026, ranked by ROI for a brand-new project. I'll explain each.

| Rank | Channel | Effort | Reach | Best for |
|---|---|---|---|---|
| 1 | **Hacker News (Show HN)** | Low (one post) | 10k–500k | Launch moment |
| 2 | **GitHub itself (trending, search)** | Medium (passive) | 1k–100k | Long tail |
| 3 | **LinkedIn (personal post + comments)** | Medium | 5k–50k | Credibility + leads |
| 4 | **X / Twitter (thread + engagement)** | Medium | 1k–100k | Dev community |
| 5 | **dev.to / Hashnode / Medium long-post** | Medium | 500–10k | SEO + depth |
| 6 | **Reddit (r/programming, r/MachineLearning, r/LocalLLaMA)** | Low | 1k–50k | Niche |
| 7 | **Newsletters (Ben's Bites, TLDR, AI Tidbits, MLOps Community)** | High (pitch them) | 5k–100k | One-shot bursts |
| 8 | **YouTube (your channel)** | Very high | 100–10k | Long-term moat |
| 9 | **Podcasts (Latent Space, MLOps Community, ChangeLog)** | Very high | 1k–50k | Authority |
| 10 | **Conference talks** | Very high | 100–1k | Skip until 1k+ stars |

For your first 90 days, focus on **1, 2, 3, 4, 5, 6**. The rest come later.

---

## Hacker News — Show HN

The single highest-ROI launch channel. A successful Show HN post can take you from 50 stars to 2,000 in 24 hours.

### Rules

1. **One Show HN per project, ever.** Don't waste it. Wait until the launch is *actually* ready.
2. **Post at 9–10am US Eastern, Tuesday–Thursday.** That's when the most-relevant audience is online.
3. **Title format:** `Show HN: NoviSentinel – self-hosted PII / injection / secrets scanner for LLM apps`. Lower case after "Show HN:", em-dash, terse. **No emojis. No marketing voice.**
4. **First comment from you** within 5 minutes of posting. It should be the "how I built this / why" backstory — 200 words max, technical, no fluff.
5. **Reply to every comment for the next 6 hours.** This is non-negotiable. HN rewards engaged founders.
6. **Don't ask for upvotes.** Reciprocally, don't DM friends to upvote — HN detects this and shadows the post.

### Template (post body, ≤300 words)

```
NoviSentinel is an open-source safety scanner for LLM apps. It runs as a self-hostable FastAPI service and detects four classes of risk per request: PII (Presidio), prompt injection (regex + DeBERTa-v3), exposed secrets (regex bank), and toxicity (Detoxify).

The reason I built it: most LLM apps have no inspection layer between the user and the model. Lakera Guard is the closest thing but it's closed-source and enterprise-only. I wanted something a small team could `docker compose up` and integrate in 30 minutes.

What's there today:
- POST /v1/scan returns risk_level + action (allow / warn / redact / block) + per-detector findings
- Python SDK: `pip install novisentinel`
- VS Code extension: `@novisentinel <prompt>` in the chat panel scans before you send
- Local dashboard with logs and stats
- Docker Compose for one-command boot

The detectors are intentionally commodity — the value is the integration surface, not the ML. I'd love feedback on the API shape, the action-decision logic (block / warn / redact / allow), and the SDK ergonomics.

GitHub: <link>
Playground (try without installing): <link>
VS Code extension: <link>

License is Apache 2.0. There's also a hosted multi-provider gateway version I'm building separately (closed source) — but everything in this repo is free forever.
```

The hosted-gateway aside is important. Be upfront about the commercial side. HN punishes pretending to be pure-OSS when you're not.

### What to expect

- **First 30 minutes:** post climbs or doesn't. If you're not on the front page by minute 60, the post likely flopped — you can try again in 6 months with a meaningfully bigger v2.
- **If it works:** 200–2000 stars in 24h, 5k–50k unique visitors, 50–500 PyPI downloads. Then a hard fall-off as the post leaves the front page.
- **Aftermath:** 30% of those users churn within 7 days. 5–10% become active. 0.5–2% become contributors.

---

## LinkedIn — your owned channel

LinkedIn for OSS is underrated. Devs are on LinkedIn for job opportunities; OSS founders ranked highly because they signal capability.

### Strategy

You have **two LinkedIn channels**:
1. **Your personal profile** — high reach when posts work, very personal.
2. **The NoviSentinel page** (if you create one) — lower reach, more "official."

For your first 6 months, **post from personal only.** Pages get throttled by LinkedIn's algorithm for accounts without existing follower bases.

### Launch post template (≤1500 chars)

```
3 months ago I started building NoviSentinel — an open-source safety scanner for LLM apps.

It detects four things in real time:
→ PII (SSN, credit cards, emails)
→ Prompt injection attempts
→ Exposed API keys / secrets
→ Toxic content

Why I built it:
Every LLM app has two moments of risk — what the user types in, and what the model spits out. Lakera Guard does this commercially, but it's closed-source and enterprise-only. I wanted something a developer could install in 5 minutes.

Today it's live on GitHub (Apache 2.0).

→ Python SDK: `pip install novisentinel`
→ VS Code extension: `@novisentinel <prompt>` scans before you send
→ Self-host via `docker compose up`

What I'm hoping for:
- Try it. Tell me what's confusing.
- Open issues for bugs / features.
- If you're building agents, see the LangChain example.

Link in first comment.

#opensource #llm #aisafety #python
```

**Why first-comment links:** LinkedIn algorithm punishes posts with outbound links in the body. Put the link in the first comment and the post itself stays in feeds longer.

### Cadence after launch

- **Week 1:** the launch post + one follow-up at end of week ("48h in, here's what surprised me about the response").
- **Weeks 2–4:** 2–3 posts/week. Each is **one specific thing** — a feature shipped, a contributor's PR merged, a real prompt-injection caught in the wild, a benchmark, a fun bug story. **No marketing voice.** Founder-builder voice.
- **Months 2–3:** weekly cadence. Mix of feature posts and "I learned X building this" posts. The "I learned" posts get 3–5× the reach.

### What kills LinkedIn reach for OSS founders

- **Posting the same content as HN/Twitter.** LinkedIn rewards original framing. Rephrase for the audience.
- **Hashtag spam.** 2–5 hashtags max. `#opensource #llm #python` is enough.
- **Anything that looks like a press release.** "Excited to announce" → instant skim. Lead with the user problem.
- **Posting too often.** 3 posts/week is the cap. More than that and reach falls off.

---

## X / Twitter

Less central to OSS than it was, but the AI dev community still lives there. Anthropic, OpenAI, LangChain, Pinecone all have major presence; their followers are your audience.

### Strategy

- **One thread for the launch.** 8–12 tweets. Each is a single, scannable point. First tweet must hook in 280 chars or fewer.
- **Reply to every prominent reply.** Same as HN.
- **Quote-tweet** big AI accounts when relevant ("interesting take from @SimonW — here's how NoviSentinel handles it"). Don't tag for the sake of tagging, but if there's a real connection, take it.
- **Follow / engage with the OSS AI safety crowd.** @lakeralabs, @protectai, @langchainai, @SimonW, @swyx, etc. Build the audience by participating, not announcing.

### What works

- Demos with embedded video / GIF.
- Specific, surprising numbers ("DeBERTa-v3 base catches 91% of injection patterns at 80ms p95 — code in the repo").
- Replies to viral tweets about LLM safety incidents. ("Here's how this would have been caught in NoviSentinel: [snippet]")

### What doesn't

- Threads of more than 15 tweets. People scroll past.
- "Excited to announce…" Same as LinkedIn.
- Reposting your launch every week. The algorithm notices.

---

## dev.to / Hashnode / Medium

These are the SEO play. A well-written launch post on dev.to ranks on Google for "open source LLM safety" within a week and keeps bringing traffic for months.

### Post template

Title: **"I built an open-source PII / prompt injection / secrets / toxicity scanner for LLM apps"**

Structure (~1500 words):

1. **The problem** (300 words). Real example. "Last month a developer pasted their AWS key into a ChatGPT prompt..."
2. **What exists** (200 words). Lakera, Protect AI, Microsoft Presidio. Why they're not enough.
3. **What I built** (400 words). The 4 detectors. The API. The action logic.
4. **The hard parts** (300 words). What surprised you. What the ML model misses. The honesty earns trust.
5. **Try it** (200 words). Install instructions. Playground link.
6. **What's next** (100 words). Roadmap teaser.

Cross-post to your own blog if you have one, with `rel=canonical` pointing to dev.to so Google credits the right URL.

---

## Reddit

Use sparingly. Reddit subs ban anything that smells like self-promotion.

**Subs that allow it (with effort):**
- **r/programming** — strict about quality but a successful post hits 5–50k.
- **r/MachineLearning** — academic-leaning. Best for "here are the precision/recall numbers" posts, not "I built a thing."
- **r/LocalLLaMA** — your audience. Self-hosting, local LLM enthusiasts. Be in the community for 2 weeks before you post your own thing.
- **r/SideProject** — friendly, lower reach (~500–5k).
- **r/Python** — accepts new libraries if you explain *why*.

**How to not get banned:**
- Read each sub's rules.
- Don't post the same content in 5 subs in 24h — Reddit detects.
- If you're going to do an "I built X" post, do it **once** in the most relevant sub. Then engage with comments for a week. Then a second post can be a follow-up ("X update — 30 days in").

---

## Newsletters (the dark horse)

A single placement in a big AI newsletter can do as much as a Show HN. The trick is most newsletters don't accept submissions — you have to know the editor.

**Newsletters worth pitching to:**
- **Ben's Bites** (~100k subs) — AI news, daily. Pitch via the website's "submit" form. Hit-rate ~10%.
- **TLDR AI** (~500k subs) — same. Lower hit-rate but bigger pop.
- **MLOps Community newsletter** — narrower audience, much higher conversion.
- **Latent Space** (substack) — Swyx's. Personal pitch via X DM works occasionally if you have something genuinely novel.
- **The Pragmatic Engineer** — Gergely covers OSS sometimes. Long shot.

**How to pitch:** 3-line email. *What it is + why it matters + one link.* If you write more than 3 lines, your hit rate drops. They get hundreds of pitches a week; they skim.

---

## YouTube — the long game

Set up a channel. Don't put pressure on yourself to post weekly. **One well-edited video per month** outperforms weekly low-effort content.

**Video ideas in priority order:**
1. **"How I built an open-source LLM safety scanner"** — 8 minutes, code-heavy, your face on camera. Honest postmortem.
2. **"Catching prompt injection in real LLM apps"** — 10 minutes, demo-driven. No face needed, screen recording is fine.
3. **"Building a VS Code extension in 90 minutes"** — tutorial format. Cross-sells the extension.
4. **"What I learned launching on Hacker News"** — 6 minutes, retrospective. Posted ~2 weeks after launch. These do well on YouTube.

YouTube takes 6–12 months to compound. Don't expect immediate wins. But every video is forever, and one going viral can be life-changing.

---

## The "first 100 stars" playbook

Concrete tactics for getting to your first 100 GitHub stars, in order:

1. **Star the repo yourself.** (Embarrassing but real — counts as 1.)
2. **Get 10 friends to star.** Even non-devs. The 10 → 50 jump is mostly psychological — empty repos don't compound.
3. **Post on personal LinkedIn** before any big launch. ~20–50 stars from your existing network.
4. **Post on X / Twitter.** ~10–30 stars depending on follower count.
5. **Submit to r/SideProject.** ~10–50 stars if title is good.
6. **Cross-post on dev.to with the launch article.** ~20–100 stars over the week.
7. **Build the VS Code extension.** Marketplace listings link back; ~50–200 stars over a month.
8. **Show HN.** ~200–2000 stars in 24h if it lands.
9. **Newsletter placements** (Ben's Bites, TLDR). ~100–500 stars per placement.
10. **Word of mouth from contributors.** Compounds slowly. 1–5 stars/day if the project is good.

By the time you've done #1–7 carefully, you're at 100–500 stars without the big launch. By the time you've done #1–9, you're at 1k–3k.

---

## What stars actually mean

Stars are a vanity metric, but they're a useful one — investors and big companies use them as a proxy for "is this real?"

**Useful stars (correlated with actual usage):**
- People who installed via pip and starred.
- People who opened an issue and starred.
- People who forked.

**Vanity stars (low correlation):**
- People who saw the HN post and starred without installing.
- People your friends bullied into starring.

You can't fully separate them, but **forks ÷ stars > 1%** is a good signal. **Issues ÷ stars > 0.5%** is a great signal. If you have 1000 stars and 1 issue, your project is being noticed but not used.

---

## Engagement rituals — what to do every week

- **Monday morning:** triage every issue and PR opened last week. First-response < 24h, even if it's "I see this, looking soon."
- **Tuesday:** write one LinkedIn post.
- **Wednesday:** one X / Twitter thread or quote-engage.
- **Friday afternoon:** ship something. Tag a release. Tweet the changelog.
- **Sunday evening:** review the week's metrics — stars, downloads, installs. Adjust the next week's plan.

This is ~5 hours a week of community work. Sustained over 90 days, it's the difference between a real project and a graveyard repo.

---

## What kills OSS projects

In rough order of frequency:

1. **Founder burnout** — see [`04-OSS_101.md`](04-OSS_101.md).
2. **No first-response on issues for 2+ weeks.** Kills perceived liveness.
3. **One big bad incident** (security disclosure, license fight, abandoned dependency).
4. **Pivoting publicly without telling the community.** People notice when the GitHub goes quiet for a month.
5. **Hubris.** The day you stop responding to non-prestigious users is the day word-of-mouth dies.

The pattern that *makes* OSS projects work:
- Show up every week, even when it's quiet.
- Reply to every issue, even the bad ones.
- Ship something visible every two weeks, even something small.
- Tell stories about the work, not just announce features.

That's it. The "secret" is just consistent presence, indefinitely.

---

## A note on competing with Lakera

Lakera is the closest commercial competitor and they're well-funded and respected. Don't punch up.

**What to do:**
- Reference them positively in your launch posts. "Lakera is great for enterprise — this is the OSS path."
- If they hire you 18 months from now, that's a fine outcome too.
- Their existence helps you. Customers Googling "PII detection LLM" find them and you. You're the open-source option.

**What not to do:**
- Don't shitpost about them. The community notices, and you look small.
- Don't try to be "Lakera but free." Be your own thing.
- Don't compete on detector accuracy. They have more capital for ML. You compete on *the integration surface* — VS Code extension, browser extension, SDK ergonomics, self-host story.

---

## Re-cap

- **HN Show post is your one big shot.** Wait until you're ready, then take it.
- **LinkedIn for ongoing presence.** 2–3 posts/week of builder voice.
- **dev.to for SEO** — one big post at launch, replicate per major feature.
- **VS Code extension is your distribution moat.** Build it well, market it through its own marketplace listing.
- **Show up every week.** Boringly. Consistently. For 18+ months. That's what compounds.

OSS distribution is unglamorous. The founders who win at it are the ones who keep going long after the initial post.
