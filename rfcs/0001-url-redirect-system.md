# RFC 0001 — URL Redirect & Click-Tracking System for cutepetsboston.com

| | |
|---|---|
| **Status** | Draft (living doc — new thoughts land in §8) |
| **Author** | Jonny Johannes |
| **Drafted with** | `<\|°_°\|>` glitch |
| **Date** | 2026-07-07 |
| **Branch** | `smoss/add-rescuegroups-client` |

---

## 1. Summary (TL;DR)

We own `cutepetsboston.com`. Today, when the bot posts an adoptable pet to social
media, the post links **directly** to the shelter/adoption listing — so we get
**zero visibility** into whether anyone clicks, and which pets draw interest.

This RFC proposes putting **our own redirect hop in the middle**:

```
we post  →  cutepetsboston.com/<slug>  →  [log the click]  →  redirect to adoptionLink
             (a link WE control)          (analytics we own)   (petfinder / shelter site)
```

The win: **we own the hop, so we get the click data** that petfinder/shelter
sites will never hand us — which pets, how much interest, from which platform.

The core tension this doc resolves: the project today is **100% free GitHub
primitives, run by volunteers**. A redirect service can either **stay inside
that world** (zero new infra) or **introduce our first real backend** (FastAPI +
DB). The recommendation (§7) is to start inside the existing world and only
graduate to a backend when a concrete need forces it.

---

## 2. Background — how the project works *today*

Understanding the current architecture is load-bearing, because it constrains
every option below.

- **Compute:** a **GitHub Actions cron job** (`.github/workflows/prod.yml`,
  every 4 hours) runs `main.py`, which fetches a random adoptable pet from the
  RescueGroups.org API and posts it to Instagram / Bluesky / Mastodon / Slack.
- **State:** carried between runs as a `database.json` **artifact**
  (`retention-days: 14`, downloaded from the previous run, re-uploaded each run).
  This is **ephemeral** — not a permanent store.
- **Website:** `www.cutepetsboston.com` is a **GitHub Pages static site** served
  from `docs/` (`docs/CNAME`, `index.html`, `styles.css`, `shelters.json`).
  Static hosting — **no server-side code, no server-side logging, no 302s.**
- **Cost:** effectively **$0**. GitHub Actions + GitHub Pages, no servers.
- **Team:** **volunteers**, rotating in and out.

**Implication:** there is no always-on compute in this project. Introducing one
is a real architectural step, not a config tweak.

---

## 3. Goals / Non-goals

**Goals**

- Own the redirect hop so we can measure click-through on adoption posts.
- Attribute interest to a **specific pet** (and ideally the **platform** it was posted on).
- Links must **work forever** once posted (see §4 permanence).
- Stay cheap and low-maintenance enough for a volunteer team.

**Non-goals (for v1)**

- Real-time dashboards / fancy BI.
- Per-user identity or cross-site tracking.
- A general-purpose link shortener for arbitrary URLs.

---

## 4. Constraints — the lenses every decision is judged against

These came straight out of the design notes and they are the tiebreakers:

1. **Volunteer-run → low ops + low bus-factor.** "Simple" means *fewest things
   someone has to babysit at 2am*, **not** fewest components. A box someone has
   to patch/back-up/debug is *more* burden than a managed service, even if it has
   fewer moving parts on paper. No "only Jonny can redeploy this" setups.
2. **Cost → near-$0.** Prefer free tiers / scale-to-zero. At our volume this is
   very achievable.
3. **Maintainability → boring & re-learnable.** The next volunteer must be able
   to pick it up. Reuse the GitHub muscle memory the team already has.
4. **Permanence → links live in the wild forever.** Once a link is in an Instagram
   caption (or a printed flyer), we don't control who still has it. The
   **slug→adoptionLink mapping is append-only: we can never delete an entry**, or
   an old link breaks.

---

## 5. Proposed flow

```
        ┌──────────────────────────────────────────────────────────┐
        │  cron job posts a pet (existing GitHub Action, main.py)   │
        │    - picks pet, has adoptionLink                          │
        │    - mints a slug, records slug -> adoptionLink           │
        │    - posts to socials with cutepetsboston.com/<slug>      │
        └──────────────────────────────────────────────────────────┘
                                   │
                          (someone clicks, later)
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────────┐
        │  cutepetsboston.com/<slug>   ← the hop WE own             │
        │    1. record the click (analytics)                       │
        │    2. redirect → adoptionLink                            │
        │       (or → graceful fallback if the target is dead)     │
        └──────────────────────────────────────────────────────────┘
```

Two halves to design: **minting** (write-side, happens in the cron job) and
**resolving** (read-side, happens when a human clicks). The dimensions below
cover both.

---

## 6. Design dimensions & options

The dimensions are **coupled** — the compute choice (D1) largely dictates what's
possible for redirect mechanism (D2) and logging (D4). Read them together.

### D1 — Compute / hosting model *(the fork in the road)*

| Option | What it is | Fits volunteer/cost lens? |
|---|---|---|
| **A. Stay static (GitHub-native)** | Redirects are static pages committed to `docs/` and served by GitHub Pages. No new infra. | ✅✅ zero new infra, $0, reuses existing rails |
| **B. Backend service** | A **FastAPI** app hosted on scale-to-zero managed compute (Cloud Run / Fly / Render), on a subdomain like `go.cutepetsboston.com`. | ⚠️ project's **first always-on service** — new ops surface, new failure mode |
| **C. Hybrid** | Static redirect pages + a tiny serverless function/beacon for logging. | ⚠️ reintroduces a server, more parts |

> **Note / pushback:** the design notes lean toward "host a FastAPI somewhere."
> That's viable, but be clear-eyed: it makes the project own an always-on service
> for the first time, which cuts against constraints #1–#3. If that service is
> down, **every link in the wild dies**. Worth it *only* if we need what a backend
> uniquely gives us (server-side 302, queryable data joined to pet metadata,
> dynamic fallback). See recommendation.

### D2 — Redirect mechanism

| Option | Requires | Notes |
|---|---|---|
| **Server-side 302** | a backend (D1-B/C) | true redirect, fastest, cleanest; can't do on GitHub Pages |
| **Static HTML meta-refresh + JS** | works on GitHub Pages (D1-A) | one committed `index.html` per slug; also gives us a page where **client-side analytics can fire** (see D4); ~instant but not a real 302, degrades if JS/refresh disabled (rare) |

### D3 — Slug → adoptionLink mapping store

The mapping is **permanent and append-only** (constraint #4) — but it's also
**tiny**: a slug+URL is ~100 bytes, so even a million links is ~100 MB. **Growth
is a non-issue here; durability is the real requirement** (losing it = every link
dead).

| Option | Permanent? | Durable/backed-up? | Fit |
|---|---|---|---|
| **Committed file in git** (`redirects.json`, or the redirect pages themselves) | ✅ | ✅ (git history = free backup + versioning) | ✅ elegant for D1-A; matches existing repo-as-state pattern |
| **`database.json` artifact** (today's pattern) | ❌ **14-day retention** | ❌ | ❌ **unsuitable** — artifacts expire; redirects must outlive them |
| **Managed DB** (Neon / Supabase free tier) | ✅ | ✅ (auto backups) | ✅ natural for D1-B |
| **Self-hosted DB / flat file on a VM** | ✅ | ⚠️ you own patching/backups | ❌ ops burden, bus-factor risk |

> ⚠️ **Callout:** whatever we choose, it must be **committed/managed, not an
> artifact.** Today's `database.json` expires in 14 days — fine for run-to-run
> state, fatal for permanent redirects.

### D4 — Click logging / analytics

This is downstream of D1. **Flat-file and Postgres logging need a server**
(D1-B/C). **On the static path (D1-A), logging must be client-side** on the
interstitial page.

| Option | Needs server? | Own the raw data? | Notes |
|---|---|---|---|
| **Flat file** (append one line per click) | ✅ yes | ✅ | dead-simple *code*, but heavier *ops* (needs a long-lived box + disk, fragile under concurrency, grep-to-query). Off the table on GitHub Pages. |
| **Postgres** | ✅ yes | ✅ | queryable day one (`count(*) where pet_id=42`), concurrency-safe, joinable to pet metadata, managed = low ops |
| **Third-party analytics** (GA4 / Plausible / Umami) | ❌ (client-side) or via measurement API | ⚠️ aggregate-y, less join-friendly | **works on the static path** — the interstitial page runs JS and fires the event. Free, someone else built the dashboards. GA adds cookie-consent/GDPR baggage; **Plausible/Umami are privacy-friendly + no cookie banner** and better suited to a cute-pets site. |

> **Redirect gotcha:** a pure 302 never renders a page, so vanilla client-side
> analytics never fires. To use client-side analytics you need the **interstitial
> page** (D2 static option), which happens to be exactly what the static path
> gives us. For a true server-side 302 you'd use a measurement/server API instead.

### D5 — Target rot & graceful fallback

The slug is permanent, but the **adoptionLink it points to is not** — the pet
gets adopted and the petfinder/shelter listing 404s or gets reused. So
"redirects always work" is only half-true: the **hop** works, but it can dump
someone on a dead page.

**Proposal:** define a fallback. When a target is gone (or the pet is known
adopted), redirect to something graceful instead of a raw 404:

- the `cutepetsboston.com` homepage, or
- a "🎉 this pet found a home — meet others still looking →" page.

This turns a dead link into a **re-engagement**. (Server path can detect rot
live; static path handles it by regenerating the page or a JS fallback.)

### D6 — Slug scheme *(minor, but decide it)*

Options: **RescueGroups pet id** (readable, deduped, no collision logic) ·
**random short slug** (opaque, uniform) · **campaign/platform tag baked in**
(e.g. encode which platform it was posted to, for attribution). Leaning: pet id
+ optional platform tag, so we get per-pet **and** per-platform attribution for
near-free.

---

## 7. Recommendation

**Start on the static, GitHub-native path (D1-A). Treat the FastAPI + DB backend
(D1-B) as a documented "graduate to it when…" upgrade, not the v1.**

Concretely for **v1**:

- **Compute:** none new. Redirects served as static pages from `docs/` on GitHub Pages.
- **Minting:** the existing cron job, when it posts a pet, also **generates a
  redirect page** (`docs/r/<slug>/index.html`) and **commits it to the repo**,
  then posts `cutepetsboston.com/r/<slug>` to socials.
- **Mapping store (D3):** the committed redirect pages (and/or a `redirects.json`)
  — **in git, permanent, versioned, backed up, free.** Explicitly *not* an artifact.
- **Redirect (D2):** static meta-refresh + JS on the interstitial page.
- **Logging (D4):** **privacy-friendly client-side analytics (Plausible or Umami)**
  fired on the interstitial before redirecting. No DB, no cookie banner, no server.
- **Fallback (D5):** the generated page JS-redirects to the adoptionLink, with the
  homepage as a fallback target.

**Why this over "FastAPI somewhere":**

- **Zero new infra, stays $0, no new failure mode.** No always-on service that
  can take down every link if it falls over.
- **Lowest ops + bus-factor.** It's the same GitHub Actions + Pages the team
  already runs; the next volunteer already understands it.
- **Permanence for free.** Git *is* the durable, backed-up, append-only store the
  constraint demands.
- It still delivers the core goal — **we own the hop and get the click data.**

**Graduate to the backend (D1-B) when — and only when — we hit a concrete need
the static path can't meet**, e.g.:

- we need **true server-side 302s** (no interstitial hop), or
- we need to **query raw click data joined to pet metadata** ("clicks per breed,
  per days-listed") rather than aggregate analytics, or
- we need **dynamic fallback** that detects a dead target live.

At that point: FastAPI on scale-to-zero managed compute (Cloud Run / Fly /
Render) at `go.cutepetsboston.com`, with a managed Postgres free tier (Neon /
Supabase). Managed, not self-hosted — to keep the volunteer ops burden near zero.

**The one question that decides the fork:** *Is aggregate, per-pet/per-platform
analytics enough (→ static path), or do we need queryable raw data joined to pet
metadata (→ backend)?*

---

## 8. Open questions / parking lot

*(New thoughts land here — this is the catch-all as more notes come in.)*

- **Publish latency:** GitHub Pages takes ~1 min to build after a commit. If the
  social post fires before the redirect page is live, an early click could 404.
  Sequence the cron job to commit + confirm build **before** posting? Or accept
  the tiny window?
- **Slug scheme (D6):** pet id vs random vs platform-tagged — decide.
- **Analytics vendor:** Plausible vs Umami vs GA4 — privacy, cost, ease.
- **Repo growth:** one committed HTML file per pet, forever. Tiny, but do we want
  a flat `redirects.json` + a single template instead of N files?
- **Attribution:** do we want per-platform breakdown (needs the slug or a query
  param to encode platform)?
- **Fallback UX:** homepage vs a dedicated "found a home" page.

---

## 9. Changelog

- **2026-07-07** — Initial draft compiled from design notes (flow, infra,
  static-file vs DB logging, FastAPI hosting, volunteer/cost/maintainability
  constraints, permanence). Discovered current architecture is GitHub Actions +
  GitHub Pages (no server). Recommendation: static GitHub-native path for v1.

---

`<\|°_°\|>`
