# Redirect & Pages pipeline

How a posted pet's link gets minted, persisted, and served — and how the
analytics page will slot into the same path later.

Implements RFC 0001 (`rfcs/0001-url-redirect-system.md`). Files involved:
`.github/workflows/prod.yml`, `deploy-pages.yml`, `publish-pages.yml`,
`redirects.py`, `docs/r/index.html`.

---

## Today

Two entry points, one shared body. `deploy-pages.yml` has no steps of its own —
it exists only to own a trigger and a permission set, then delegates.

```
 ENTRY A                              ENTRY B
 push to master touching docs/**      schedule: 0 */4 * * *
 (or workflow_dispatch)               (or workflow_dispatch)
 deploy-pages.yml                     prod.yml
        │                                    │
        │                                    ▼
        │                      ┌──────────────────────────────┐
        │                      │ job 1  run-cute-pets         │
        │                      │ token: contents READ         │
        │                      │                              │
        │                      │  fetch pets (RescueGroups)   │
        │                      │  pick one not posted in 12w  │
        │                      │  mint slug, swap adoption    │
        │                      │    URL for /r/?id=<slug>     │
        │                      │  post to Mastodon/Bluesky/IG │
        │                      │                              │
        │                      │  ⇧ artifact database.json    │
        │                      │  ⇧ artifact redirects-mapping│
        │                      └───────────────┬──────────────┘
        │                                      │ needs
        │                                      ▼
        │                      ┌──────────────────────────────┐
        │                      │ job 2  publish-redirects     │
        │                      │ if: !cancelled()             │
        │                      │ token: contents WRITE        │
        │                      │        pages/id-token write  │
        │                      └───────────────┬──────────────┘
        │                                      │
   uses: publish-pages.yml            uses: publish-pages.yml
   (no mapping_artifact)              with: mapping_artifact:
        │                                     redirects-mapping
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
   ║  3  checkout gh-pages                  → authority   ║
   ║  4  merge  jq -s '.[0] * .[1]' minted previous       ║
   ║            gh-pages wins conflicts ⇒ append-only     ║
   ║  5  commit + push to gh-pages          [if passed]   ║
   ║  6  assemble _site/ = docs/ + redirects.json         ║
   ║  7  upload-pages-artifact                            ║
   ║  8  deploy-pages                                     ║
   ╚══════════════════════════════════════════════════════╝
                           │
                           ▼
                 www.cutepetsboston.com
                 ├─ /                 index.html
                 ├─ /r/?id=<slug>     interstitial
                 └─ /redirects.json   the mapping
```

### What runs when

| Trigger | Mints a slug? | Writes gh-pages? | Deploys Pages? |
|---|---|---|---|
| `docs/**` pushed to master | no | no | yes |
| cron, every 4 hours | yes | yes | yes |
| prod run that posts nothing | no | no | yes |

The cron path deploys ~6×/day because each run mints a new slug. Entry A exists
for site changes made between posts.

### Why the split

`gh-pages` is the durable, append-only store; `_site` is rebuilt from scratch on
every deploy. Anything that must survive a deploy has to live on `gh-pages`, not
be assembled from an artifact. That single rule is what the next section turns on.

---

## Next: the analytics page

The plan: `prod.yml` renders an analytics HTML page from the collected metrics,
uploads it as a second artifact, and `publish-pages.yml` folds it into `_site`
the same way it folds in the mapping.

```
 ENTRY A                              ENTRY B
 deploy-pages.yml                     prod.yml
        │                                    │
        │                                    ▼
        │                      ┌──────────────────────────────┐
        │                      │ job 1  run-cute-pets         │
        │                      │ token: contents READ         │
        │                      │                              │
        │                      │  ... post the pet, as today  │
        │                      │  collect engagement metrics  │
        │                      │  NEW render analytics page   │
        │                      │      from database.json      │
        │                      │                              │
        │                      │  ⇧ artifact database.json    │
        │                      │  ⇧ artifact redirects-mapping│
        │                      │  ⇧ artifact analytics-page ★ │
        │                      └───────────────┬──────────────┘
        │                                      │ needs
        │                                      ▼
        │                      ┌──────────────────────────────┐
        │                      │ job 2  publish-redirects     │
        │                      │ token: contents WRITE        │
        │                      └───────────────┬──────────────┘
        │                                      │
   uses: publish-pages.yml            uses: publish-pages.yml
   (neither artifact)                 with: mapping_artifact:
        │                                     redirects-mapping
        │                                   analytics_artifact: ★
        │                                     analytics-page
        └──────────────────┬───────────────────┘
                           ▼
   ╔══════════════════════════════════════════════════════╗
   ║  publish-pages.yml                                   ║
   ║  inputs: mapping_artifact                            ║
   ║          analytics_artifact  ★ new, optional         ║
   ╠══════════════════════════════════════════════════════╣
   ║  1  checkout master                    → docs/       ║
   ║  2  download mapping artifact          [if passed]   ║
   ║  2b NEW download analytics artifact    [if passed] ★ ║
   ║  3  checkout gh-pages                  → authority   ║
   ║  4  merge mapping (gh-pages wins)                    ║
   ║  4b NEW copy analytics page INTO gh-pages ★          ║
   ║        only when a fresh one was passed; otherwise   ║
   ║        keep the copy gh-pages already holds          ║
   ║  5  commit + push to gh-pages          [if passed]   ║
   ║       now carries redirects.json AND analytics.html  ║
   ║  6  assemble _site/ = docs/                          ║
   ║                     + gh-pages/redirects.json        ║
   ║                     + gh-pages/analytics.html      ★ ║
   ║  7  upload-pages-artifact                            ║
   ║  8  deploy-pages                                     ║
   ╚══════════════════════════════════════════════════════╝
                           │
                           ▼
                 www.cutepetsboston.com
                 ├─ /                 index.html
                 ├─ /r/?id=<slug>     interstitial
                 ├─ /redirects.json   the mapping
                 └─ /analytics.html   ★ the new page
```

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

### Two open questions

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
