# Code review — `redirect-test`

Branch `redirect-test` (2 commits) against `62d76b5`:

- `8b51d17` Post redirect links instead of raw adoption URLs
- `7b6b401` Add tests for redirect link minting

Reviewed 2026-08-05 via `/code-review`.

> **Note on finding 7:** it does not hold up on inspection. It claims both CNAME
> files declare the apex domain; in fact `/CNAME` is `cutepetsboston.com` but
> `/docs/CNAME` is `www.cutepetsboston.com`, which matches `SITE_URL`. The two
> CNAME files disagreeing with each other is worth resolving, but there is no
> unresolvable-link risk as described. Every other finding below was left as
> written by the reviewer.

## Verification performed

- Reproduced the `git pull --rebase` failure locally: with staged changes it exits **128** (`error: cannot pull with rebase: Your index contains uncommitted changes`), and `git add <missing path>` exits **128** (`fatal: pathspec ... did not match any files`).
- `git ls-remote --heads origin` → **50 branches, zero named `gh-pages`**.

## Findings

**1. `.github/workflows/prod.yml:88` — CRITICAL. `git pull --rebase` runs with staged changes and always fails, so the redirect mapping is never pushed.** The script does `git add docs/redirects.json`, confirms the index is dirty, and then runs `git pull --rebase origin gh-pages` *before* `git commit`. Git refuses to rebase with a dirty index and exits 128; with the default `bash -e` shell the step fails and `git commit`/`git push` never execute. Net effect on every single prod run that has a new pet: the post goes out with `https://www.cutepetsboston.com/r/?id=<pet_id>` but `redirects.json` on gh-pages never gains the entry, so every posted link lands on "This pet's listing is no longer available." Move `git commit` before `git pull --rebase`.

**2. `.github/workflows/pages-sync.yml:46` — HIGH. Same commit-after-pull ordering bug.** `git add -A` then `git pull --rebase origin gh-pages` before `git commit` → step exits 128 whenever there is anything to sync, i.e. the workflow fails in exactly the case it exists for. Site content never syncs to gh-pages.

**3. `.github/workflows/prod.yml:26` — CRITICAL. The `gh-pages` branch does not exist, and this step is now a hard dependency of the posting job.** `actions/checkout` with `ref: gh-pages` fails with `fatal: couldn't find remote ref gh-pages`, which aborts the job *before* the "Call RescueGroups API" step — so merging this stops all pet posting every 4 hours, not just the redirects. Neither new workflow can bootstrap the branch (pages-sync also checks it out with `ref: gh-pages`). The branch has to be created out-of-band before merge, or the checkout needs to tolerate its absence.

**4. `.github/workflows/prod.yml:84` — MEDIUM. `git add docs/redirects.json` fails hard when the file doesn't exist.** Because the step is `if: '!cancelled()'`, it runs after a failed python step too. If `main.py` dies before `mint_redirect_url` (RescueGroups outage, `SystemExit` from `run()`, no eligible pet), `gh-pages/docs/redirects.json` is absent and `git add` exits 128 with `pathspec ... did not match any files` — masking the real failure with a confusing second one. Also fails on the first run against a fresh gh-pages. Guard with a file-existence check.

**5. `main.py:108` — HIGH. `posters_are_real` keys off poster class instead of "will this mapping actually be published", which breaks dev posts.** `dev.yml` supports `debugposters=false` to post to the real *test* accounts. In that path `posters_are_real` is True, so redirects are minted, but dev.yml has no gh-pages checkout, no `REDIRECTS_JSON_PATH`, and no commit step — the mapping is written to `docs/redirects.json` on the ephemeral runner and thrown away. Every test-account post gets a permanently dead `/r/?id=...` link. The guard should be "is a publishable redirects path configured" (e.g. `REDIRECTS_JSON_PATH` set), not `isinstance(..., PosterDebug)`.

**6. `docs/r/index.html:45` — MEDIUM (security). `location.replace(url)` navigates to an unvalidated, third-party-sourced URL.** Values in `redirects.json` come from `pet.adoption_url`, which for the RescueGroups source is the shelter-supplied `adoptionUrl` attribute; `rescue_groups.py:238` only rejects the literal bare-scheme strings (`"http:"`, `"https://"`, …). A shelter record with `adoptionUrl: "javascript:…"` therefore gets minted into `redirects.json` and executed as script on `cutepetsboston.com` when a follower clicks the link. Validate with `new URL(url)` and allow only `http:`/`https:` before replacing.

**7. `config.py:5` — MEDIUM. `SITE_URL` uses a `www.` host that appears nowhere else in the repo.** Both `/CNAME` and `/docs/CNAME` declare the apex `cutepetsboston.com`. GitHub Pages only serves/redirects `www.` if a DNS record for it exists. If it doesn't, every link this PR posts (`https://www.cutepetsboston.com/r/?id=…`) is unresolvable — and it's unrecoverable after the fact, since the URL is already in published posts. Confirm the `www` DNS record or use the apex.

> *(See note at top — this finding is incorrect; `/docs/CNAME` is the `www.` host.)*

**8. `.github/workflows/prod.yml:88` — MEDIUM. Shallow checkout + racing concurrency groups make the rebase unreliable even once ordering is fixed.** Both gh-pages checkouts use the default `fetch-depth: 1`; `git pull --rebase` on a shallow clone whose remote has advanced can fail to find a merge base. Additionally `prod.yml` uses concurrency group `${{ github.workflow }}-${{ github.ref }}` while `pages-sync.yml` uses `gh-pages-deploy`, so the two can push to gh-pages simultaneously. Use `fetch-depth: 0` and a shared concurrency group across both workflows.

**9. `main.py:109` — MEDIUM. The mapping is published strictly *after* the post goes out.** `mint_redirect_url` returns, all three posters publish, and only then does the workflow commit + push to gh-pages, followed by a Pages rebuild and CDN cache TTL. Anyone clicking the link during that window (easily several minutes, and permanently if the push step fails per finding 1) is told "This pet's listing is no longer available." Push the mapping before publishing, or have the page retry with a cache-busting fetch on miss.

**10. `main.py:167` — LOW. `slug = str(pet.pet_id)` with no validation.** `pet_id` is `str | None` and `pick_pet` (main.py:143) only filters on `image_url`/`adoption_url`. `SourceManual._build_pet` defaults it to `""`, so a record with no `id` yields slug `""` → posted link `/r/?id=` → the page's `if (!id)` branch sends every visitor home; a `None` yields the literal key `"None"`, which append-only then binds permanently to the first id-less pet, so a later id-less pet's link points at the wrong shelter listing. Skip minting (or skip the pet) when `pet_id` is falsy.

**11. `main.py:184` — LOW. The slug is interpolated into the query string unencoded.** `f"{SITE_URL}/r/?id={slug}"` has no `urllib.parse.quote`, while the page validates against `/^[a-zA-Z0-9_-]+$/`. Any pet id containing `&`, `#`, `+`, or a space produces a link that either truncates or fails validation and bounces the visitor home.

**12. `main.py:176` — LOW. Append-only interacts badly with the 12-week `database.json` prune.** `pick_pet` drops posted-pet records older than 12 weeks, so a pet can be selected and posted again. On the second post the slug already exists, so the *new* post links to the URL captured months earlier — likely dead by then. Consider minting a fresh slug (e.g. `pet_id` + date) when the mapping already holds a different current URL.

**13. `.github/workflows/pages-sync.yml:35` — LOW. The scheme assumes Pages is configured for `gh-pages` branch, `/docs` folder, which is not the current configuration.** Pages today is served from `master` (root `CNAME` + `docs/CNAME` + `docs/index.html`), and nothing in this PR flips the source. Until it's flipped, `redirects.json` is only on gh-pages and is never served. If it's flipped to gh-pages **root** rather than **/docs**, `/r/?id=…` 404s (the files would live at `/docs/r/`). Worth calling out in the PR description as a required manual step.

**14. `docs/r/index.html:40` — LOW. Every redirect click downloads the entire mapping.** `redirects.json` is append-only and never pruned; at one post every 4 hours with `indent=4` it grows roughly 200-300 KB/year forever, all fetched on each click. Consider per-slug files (`/r/<id>.json`) or periodic pruning of entries older than the useful link lifetime.

## Manual steps required before merge

- Create the `gh-pages` branch out-of-band (findings 3, 13).
- Flip the GitHub Pages source to `gh-pages` branch, `/docs` folder (finding 13).
- Confirm the `www` DNS record, or reconcile `/CNAME` and `/docs/CNAME` (finding 7).
