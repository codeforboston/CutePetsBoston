# Redirect & Pages pipeline

How a posted pet's link gets minted, persisted, and served. The same Pages
pipeline also persists and publishes the analytics page.

Implements RFC 0001 (`rfcs/0001-url-redirect-system.md`). Files involved:
`.github/workflows/prod.yml`, `deploy-pages.yml`, `publish-pages.yml`,
`redirects.py`, `database.py`, `metrics_dashboard.py`, `docs/r/index.html`.

---

## Current flow

Two entry points, one shared body. `deploy-pages.yml` has no steps of its own —
it exists only to own a trigger and a permission set, then delegates.

```
 ENTRY A                              ENTRY B
 push to master touching docs/**      schedule: 0 */4 * * *
 or Pages workflow files              (or workflow_dispatch)
 deploy-pages.yml                     prod.yml
        │                                    │
        │                                    ▼
        │                      ┌───────────────────────────────┐
        │                      │ job 1  run-cute-pets          │
        │                      │ token: contents READ          │
        │                      │                               │
        │                      │  fetch pets (RescueGroups)    │
        │                      │  pick one not posted in 12w   │
        │                      │  mint slug, swap adoption     │
        │                      │    URL for /r/?id=<slug>      │
        │                      │  post to Mastodon/Bluesky/IG  │
        │                      │                               │
        │                      │  ⇧ artifact database.json     │
        │                      │  ⇧ artifact redirects-mapping │
        │                      │  ⇧ artifact analytics-page    │
        │                      └───────────────┬───────────────┘
        │                                      │ needs
        │                                      ▼
        │                      ┌───────────────────────────────┐
        │                      │ job 2  publish-redirects      │
        │                      │ if: !cancelled()              │
        │                      │ token: contents WRITE         │
        │                      │        pages/id-token write   │
        │                      └───────────────┬───────────────┘
        │                                      │
   uses: publish-pages.yml            uses: publish-pages.yml
   (no artifacts)                     with: mapping_artifact:
        │                                     redirects-mapping
        │                                   analytics_artifact:
        │                                     analytics-page
        └──────────────────┬───────────────────┘
                           ▼
   ╔══════════════════════════════════════════════════════╗
   ║  publish-pages.yml   (reusable, on: workflow_call)   ║
   ║  concurrency: pages-publish   ← both callers queue   ║
   ║  environment: github-pages                           ║
   ║  declares NO permissions — inherits the caller's     ║
   ╠══════════════════════════════════════════════════════╣
   ║  1  checkout master                    → docs/       ║
   ║  2  download mapping artifact          [if passed]   ║
   ║  2b download analytics artifact        [if passed]   ║
   ║  3  checkout gh-pages                  → authority   ║
   ║  4  merge  jq -s '.[0] * .[1]' minted previous       ║
   ║            gh-pages wins conflicts ⇒ append-only     ║
   ║  4b copy fresh analytics.html into gh-pages          ║
   ║  5  commit + push to gh-pages          [if passed]   ║
   ║  6  assemble _site/ = docs/ + redirects.json         ║
   ║                     + analytics.html                 ║
   ║  7  upload-pages-artifact                            ║
   ║  8  deploy-pages                                     ║
   ╚══════════════════════════════════════════════════════╝
                           │
                           ▼
                 www.cutepetsboston.com
                 ├─ /                 index.html
                 ├─ /r/?id=<slug>     interstitial
                 ├─ /redirects.json   the mapping
                 └─ /analytics.html   analytics page
```

### Redirect contract

- Redirect minting is enabled only when `REDIRECTS_ENABLED` is truthy; local and
  development runs keep the original adoption URL.
- A RescueGroups `pet_id` becomes the slug. URL-safe IDs pass through unchanged;
  IDs that need sanitizing receive a short SHA-256 suffix so distinct IDs cannot
  collide.
- New mappings are written to the local `redirects.json` and uploaded as the
  `redirects-mapping` artifact. Existing mappings are never overwritten or
  deleted; the `gh-pages` copy is authoritative if a collision is encountered.
- Only `http` and `https` adoption targets are accepted. A missing pet ID, unsafe
  target, or unreadable local mapping falls back to the original adoption URL so
  redirect data cannot block a social post.
- The `/r/` interstitial validates the slug and target again in the browser before
  using `location.replace()`.

### What runs when

| Trigger | Mints a slug? | Writes gh-pages? | Deploys Pages? |
|---|---|---|---|
| `docs/**` or Pages workflow pushed to master | no | no (uses existing assets) | yes |
| cron, every 4 hours | yes | yes | yes |
| successful prod run without a new redirect | no | yes (analytics) | yes |

Both workflows also support `workflow_dispatch` for an explicit run. Changes to
`metrics_dashboard.py` are reflected on the next successful production run (or a
manual production dispatch), not by the docs-only deployment. The cron path
deploys ~6×/day because each successful run normally mints a new slug and
refreshes analytics. Entry A exists for site changes made between posts;
it passes no artifacts and therefore reuses the durable `gh-pages` assets.

### Why the split

`gh-pages` is the durable Pages store: `redirects.json` is append-only, while
`analytics.html` is replaced only when a fresh page is available. `_site` is
rebuilt from scratch on every deploy. Anything that must survive a deploy has to
live on `gh-pages`, not be assembled directly from an artifact.

### Permissions and serialization

The posting job has only `actions: read` and `contents: read`. It handles the
external API responses and social credentials but cannot push repository changes.
The publishing job is the only job with `contents: write`, `pages: write`, and
`id-token: write`. The reusable workflow inherits those caller permissions rather
than declaring broader ones itself.

Both `prod.yml` and `deploy-pages.yml` use the `pages-publish` concurrency group.
A scheduled post and a docs deployment therefore queue behind one another instead
of racing while reading or updating `gh-pages`.

---

## Analytics page

The production path collects engagement metrics, then `main.run` renders
`analytics.html` from the carried-forward `database.json`. The page contains
platform-filtered Plotly charts for the top ten pets by maximum and total likes,
reposts, and comments. `prod.yml` uploads the page as the `analytics-page`
artifact, and `publish-pages.yml` persists it to `gh-pages` before folding it
into `_site`. The artifact is retained for one day because the publishing job
consumes it immediately; `gh-pages/analytics.html` is the durable copy.

Analytics is generated in the read-only posting job and passed to the publishing
job as an optional artifact. The publishing job copies a fresh page to
`gh-pages/analytics.html`; if no fresh artifact is available, it keeps the last
good page. Pages is then assembled from `docs/`, `gh-pages/redirects.json`, and
`gh-pages/analytics.html`.

### The trap to avoid

Do **not** assemble the analytics page straight from the artifact into `_site`.
`_site` is rebuilt from nothing on every deploy, and Entry A passes no artifacts
— so a docs-only push would publish a site with the analytics page **missing**,
and it would stay missing until the next cron run four hours later. This is the
same failure shape as the mapping wipe that the `jq` merge exists to prevent.

Read step 6 above: `_site` takes both files from the **gh-pages checkout**, never
directly from the artifact. The artifact's only job is to update gh-pages in step
4b. Whatever gh-pages holds is what gets published, so a deploy triggered by any
path serves the last good analytics page.

### Retention question

**Retention — how far back can the page show?** Not limited by artifact expiry.
The chain carries history forward: each run downloads the previous run's
`database.json`, appends to it, and re-uploads with a fresh 14 days. While runs
keep succeeding, nothing is lost to retention.

The real ceiling is a prune in code. `record_publish_results` (`main.py:188`)
trims both `posted_pets` and `posts` to a rolling 12 weeks on *every* run, and
writes the trimmed file back into the artifact that carries forward:

```
day 0       posted → recorded in posted_pets + posts
days 0-14   collect_metrics appends a snapshot each run (window_days=14)
days 14-84  static; still in the file, no new snapshots
day 84      pruned by the 12-week cutoff — gone permanently
```

So analytics history tops out at **12 weeks**. That cutoff exists for `pick_pet`,
which reads `posted_pets` to avoid reposting a pet within 12 weeks; `posts` and
their `metrics` arrays are collateral, swept along because both share the one
cutoff. Showing a longer window means decoupling the two — the repost window has
no reason to match the analytics window.

The 14-day number bites in one case only: the chain keys off `--status success`
(`prod.yml:53`), and a run counts as failed if *any* job fails. Such a run is
skipped by the next run's lookup, orphaning its records; 14+ consecutive days of
failures expires the last good artifact and resets history to empty.

**Where the page is built.** Rendering in job 1 keeps it on the read-only token,
which is right — it reads `database.json` and writes HTML, no repo access needed.
The alternative, rendering inside `publish-pages.yml`, would need the data
artifact plumbed in anyway and would run on the elevated token for no benefit.
