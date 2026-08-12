# MetricCollector — per-platform engagement snapshots

## Summary

Add a `MetricCollector` parallel to the existing `SocialPoster` ABC, with concrete implementations for Bluesky, Mastodon, and Instagram. Each run, after publishing, re-poll normalized engagement counts (`likes`, `reposts`, `comments`) for posts up to 14 days old and append snapshots to the existing `database.json` artifact. `database.json` grows a new top-level `posts[]` table (one row per published post, joined to `posted_pets[]` by `pet_id`) with metric snapshots nested inside each post as a time-series list. No new persistence layer — same artifact, same workflow.

The collector abstraction uses one stable vocabulary across platforms: native likes/favourites map to `likes`, native reposts/reblogs map to `reposts`, and native replies/comments map to `comments`. A separate `shares` field is not persisted; unavailable metrics are stored as `null`.

## Problem Statement

We post pets to three platforms but capture zero feedback on how those posts perform. We don't know which pets get traction, which platform performs best for which species, or whether a given post is dead in the water. Without that data, we can't prioritize, A/B, or build a dashboard later.

## Goals

- Persist per-platform engagement (`likes`, `reposts`, `comments`) for every post we publish. A separate `shares` field is intentionally out of scope.
- Snapshot metrics on a recurring schedule (each scheduled run) so we have a time series, not just latest counts.
- Reuse the existing `database.json` artifact and GH Actions upload/download pattern — no new storage.
- Mirror the existing `SocialPoster` platform layout so adding a new platform is symmetric: one poster + one collector. Collectors share the platform naming and package pattern, but only expose the metric-fetching lifecycle they need.

## Non-Goals

- **Dashboard / UI.** Out of scope for this MVP — planned as a follow-up (likely served from GH Pages in this repo, consuming the same artifact).
- **Slack digests / alerts on metric trends.** Future work.
- **Impressions / views / reach.** Not all platforms expose these (Bluesky doesn't, Mastodon doesn't, Insta requires extra Insights perms). Core engagement only.
- **Backfilling metrics for posts from before this feature ships.** Going forward only.

## Background

Current state (relevant pieces):

- `abstractions.py` defines `SocialPoster` ABC, `Post`, `PostResult(success, post_id, post_url, error_message)`. Each concrete poster returns a `post_id` (and usually `post_url`) on success.
- `main.py::run()` iterates posters, calls `publish()`, but **does not persist the returned `post_id` anywhere.** That's a blocker for metric collection.
- `main.py::pick_pet()` writes one entry per posted pet to `database.json`: `{name, pet_id, posted_at}`. Entries older than 12 weeks are pruned on write.
- `database.json` is a GitHub Actions artifact: `prod.yml` downloads the previous run's artifact, runs `main.py`, then re-uploads (14-day retention in prod, 1 day in dev).
- Per-platform `post_id` shapes:
  - **Bluesky**: `PostResult.post_id` = cid, `post_url` = `at://...` URI. The `at://` URI is what `app.bsky.feed.getPostThread` needs.
  - **Mastodon**: `post_id` = status id (string), `post_url` = public URL. The status id is what `GET /api/v1/statuses/:id` needs.
  - **Instagram**: `post_id` = media id, `post_url` = generic account URL (not per-post). Media id is what `GET /{media-id}` needs.

## Proposed Solution

### Overview

Three layered changes:

1. **Schema evolution** of `database.json` to add a new top-level `posts[]` table joined to `posted_pets[]` by `pet_id`, with metric snapshots nested inside each post entry.
2. **New abstractions** (`MetricCollector` ABC, `PostMetrics` dataclass) added to `abstractions.py`.
3. **New `metric_collectors/` package** mirroring `social_posters/`, with one collector per platform, wired into `main.py` to run after posting.

### Detailed Design

#### Schema: `database.json` evolution

Add a new top-level `posts[]` array alongside the existing `posted_pets[]`. `posted_pets[]` is unchanged (pet metadata only). Each post entry carries its own `pet_id` (foreign key), `platform`, `post_id`, `post_url`, `posted_at`, and a nested `metrics[]` time-series:

```json
{
  "posted_pets": [
    {
      "name": "Fido",
      "pet_id": "rg-12345",
      "posted_at": "2026-05-26T12:00:00+00:00"
    }
  ],
  "posts": [
    {
      "pet_id": "rg-12345",
      "platform": "Bluesky",
      "post_id": "bafyrei...",
      "post_url": "at://did:plc:.../app.bsky.feed.post/3k...",
      "posted_at": "2026-05-26T12:00:00+00:00",
      "metrics": [
        {"collected_at": "2026-05-26T12:00:10+00:00", "likes": 0, "reposts": 0, "comments": 0},
        {"collected_at": "2026-05-26T16:00:10+00:00", "likes": 5, "reposts": 1, "comments": 0}
      ]
    },
    {
      "pet_id": "rg-12345",
      "platform": "Mastodon",
      "post_id": "...",
      "post_url": "...",
      "posted_at": "2026-05-26T12:00:00+00:00",
      "metrics": []
    }
  ]
}
```

**Why `posted_at` is duplicated on the post row**: the collector filters posts by age (14d window) every run. Storing `posted_at` on the post row lets the filter run as a direct scan of `posts[]` without joining back to `posted_pets[]`. The few-bytes redundancy is worth the simpler query and matches how the eventual dashboard will consume the data.

**Backward compat**: existing `database.json` artifacts only have `posted_pets[]`. The new code:

- Treats missing `posts` key as `[]` (no posts to poll, no-op for collector).
- Existing pets stay as-is — there are no historical `post_id`s to back-fill anyway. They age out naturally after 12 weeks.
- New pets get written to both `posted_pets[]` AND `posts[]` in the same transaction (see [Orchestration](#orchestration-mainpy-changes)).

No migration script needed.

**Failed publishes**: if a poster returned `success=False`, no row is appended to `posts[]` for that platform. The collector iterates only what's there.

**Pruning** (both arrays use their own `posted_at` so prune is two independent filters, no join):

- `posted_pets[]`: drop entries with `posted_at` older than 12 weeks (existing behavior).
- `posts[]`: drop entries with `posted_at` older than 12 weeks (new, mirrors pet prune so no orphans accumulate).

Both prunes run on every `record_publish_results` write. The collector never prunes (it only appends).

#### `abstractions.py` additions

```python
@dataclass
class PostMetrics:
    collected_at: str            # ISO8601 UTC, assigned by orchestration
    likes: int | None = None     # likes/favourites
    reposts: int | None = None   # reposts/reblogs; None when unavailable
    comments: int | None = None  # replies/comments


class MetricCollector(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str: ...

    @abstractmethod
    def fetch_metrics(self, post_id: str, post_url: str | None = None) -> PostMetrics | None:
        """
        Return a PostMetrics snapshot for the given post.
        Return None if the post is unreachable (deleted, 404, transient error).
        Caller logs None results and continues — never raises into the caller.
        """
        ...
```

Notes:

- `platform_name` must match the corresponding poster's `platform_name` exactly — that's the join key in `database.json`.
- `post_id` is the platform identifier returned by the poster. `post_url` is an optional API lookup locator; it is required by the Bluesky collector because the public thread endpoint needs the `at://` URI, while Mastodon and Instagram use `post_id`.
- The orchestration layer owns the persisted `collected_at` timestamp so snapshots from one run share a consistent UTC collection time.
- Returning `None` (not raising) is the contract — a flaky network shouldn't crash a whole run.

#### Concrete collectors

One file each under `metric_collectors/`, matching the `social_posters/` layout:

| File | Class | API call | Counts |
|---|---|---|---|
| `metric_collectors/bluesky.py` | `CollectorBluesky` | `GET /xrpc/app.bsky.feed.getPostThread?uri={post_url}` (public, no auth) | `thread.post.{likeCount, repostCount, replyCount}` |
| `metric_collectors/mastodon.py` | `CollectorMastodon` | `mastodon.status(id)` via the `Mastodon` SDK | `status.{favourites_count, reblogs_count, replies_count}` |
| `metric_collectors/instagram.py` | `CollectorInstagram` | `GET {GRAPH_API_BASE}/{media-id}?fields=like_count,comments_count&access_token=...` | `like_count`, `comments_count`. `reposts` → `None` (unavailable from this endpoint) |

Each collector:

- Has `platform_name` returning the same string as its paired poster.
- Reads credentials from the same env vars as its paired poster (Insta needs the access token; Bluesky/Mastodon metric endpoints are public-readable so no creds required).
- Returns `None` on any exception, logs to stdout with platform prefix.

#### Orchestration: `main.py` changes

**Refactor `pick_pet`**: split the responsibility so `pick_pet` chooses the pet without writing post info; a new `record_publish_results(pet, results)` writes the pet entry *including* `posts` after `run()` has results.

Current `pick_pet` writes the entry on selection. Move the write to after publishing so we can include post_ids in the same write. Pruning of >12wk entries still happens at write time.

New shape of `main()`:

```python
def main():
    # ...existing arg parsing...
    try:
        sources = create_sources(...)
        posters = create_posters(...)
        collectors = create_collectors(...)  # new

        pets = fetch_all_pets(sources)
        pet = pick_pet(pets, database_path="database.json")  # no longer writes
        if pet:
            results = publish(pet, posters)                  # existing per-poster loop
            record_publish_results(pet, results, database_path="database.json")  # writes pet + posts

        collect_metrics(collectors, database_path="database.json", window_days=14)  # new
    except Exception:
        notify_slack_of_exception(traceback.format_exc())
        raise
```

`collect_metrics()` responsibilities:

1. Read `database.json`. Treat missing `posts` key as `[]`.
2. Build a `{platform_name: collector}` lookup from the `collectors` list.
3. Compute `cutoff = now_utc - timedelta(days=window_days)`.
4. For each entry in `posts[]` where `posted_at >= cutoff`:
   - Look up the collector by `entry["platform"]`. Skip if not registered.
   - Call `collector.fetch_metrics(entry["post_id"], entry.get("post_url"))`.
   - If non-None, append the snapshot (as a dict with `collected_at` set to now-UTC) to `entry["metrics"]`.
5. Write the file back. **Atomic write**: write to `database.json.tmp` then rename, so a mid-write crash doesn't corrupt the artifact.

Note: `collect_metrics` only appends to `metrics[]` lists; it never adds or removes rows from `posts[]` or `posted_pets[]`. Pruning is `record_publish_results`'s job.

`record_publish_results(pet, results, database_path)` responsibilities:

1. Read `database.json`. Treat missing `posts` key as `[]`.
2. Append to `posted_pets[]`: `{name, pet_id, posted_at}` (same shape as today).
3. For each `result` in `results` where `result.success` is True:
   - Append to `posts[]`: `{pet_id, platform, post_id, post_url, posted_at, metrics: []}`.
   - `platform` is taken from the matching poster's `platform_name`. (`run()` will need to pass `(poster, result)` pairs, not just results.)
4. Prune both arrays: drop entries with `posted_at` older than 12 weeks.
5. Atomic write via `.tmp` rename.

`create_collectors(debug=False)`:

- Mirrors `create_posters`. If debug, returns `[]` (no-op) or a single `CollectorDebug` that just logs. (Lean toward `[]` for simplicity unless we want to exercise the orchestration in dev.)
- Otherwise returns `[CollectorBluesky(), CollectorMastodon(), CollectorInstagram()]`.

#### File-locking / concurrency

Not a concern — each GH Actions run is single-process and downloads its own copy of the artifact. No concurrent writers.

#### GitHub workflow changes

**None required.** The existing `prod.yml` and `dev.yml` already download `database.json` from the previous run and re-upload it. Metric snapshots ride along.

Optional polish: bump prod artifact retention from 14 → 30 days so a few weeks of metric history survives even if a run fails. Defer unless we hit the limit in practice.

#### Error handling

- A collector exception inside `fetch_metrics` returns `None` and is logged. Never raises.
- `collect_metrics()` wraps the whole loop in try/except per pet/platform — one bad entry doesn't kill the rest.
- `collect_metrics()` itself does NOT raise into `main()`. Metric collection is best-effort; if the artifact write fails, log loudly but don't notify Slack (posting succeeded, metrics are just delayed).

#### What about deleted/missing posts?

If a post 404s (user deleted, account suspended), the collector returns `None`. The entry stays in `database.json` with whatever history it has; future runs will keep returning `None` until the pet ages out of the 12-week window.

Optional: after N consecutive `None` results for the same `(pet_id, platform)`, mark the entry as `unreachable: true` and skip it. Defer — not needed for MVP.

## Implementation Plan

Each step independently verifiable.

1. **Add `PostMetrics` dataclass + `MetricCollector` ABC** to `abstractions.py`. Verify: existing tests still pass; importable.
2. **Refactor `pick_pet`** so it picks but does not write. `pick_pet` returns the chosen `AdoptablePet`; no `database.json` writes happen inside it. Verify: existing tests for pick_pet are updated and still pass; dedup logic (skipping previously-posted `pet_id`s) is preserved by reading from `posted_pets[]` in the new pick-only flow.
3. **Add `record_publish_results(pet, results, database_path)`** that writes the pet entry to `posted_pets[]` and one row per successful publish to `posts[]` (with `metrics: []`). Prunes both arrays at 12 weeks. Update `main.py::run()` to pass `(poster, result)` pairs so platform names are available at write time. Verify: post a pet via dev workflow (`--debugposters`) and inspect `database.json` artifact — `posted_pets[]` has one new entry, `posts[]` has N new entries (one per successful publish).
4. **Create `metric_collectors/` package + 3 concrete collectors** (`bluesky.py`, `mastodon.py`, `instagram.py`). Each implements `fetch_metrics(post_id, post_url=None) -> PostMetrics | None`. Verify: unit tests with mocked HTTP responses for each platform.
5. **Add `collect_metrics()` orchestration** to `main.py` + `create_collectors()` factory. Wire after `run()`. Iterates `posts[]` within the 14-day window, appends snapshots to each post's `metrics[]`. Verify: end-to-end dev run shows `posts[i].metrics` growing by one entry per run.
6. **End-to-end verification** on the dev workflow: trigger `dev.yml`, confirm `database.json` artifact contains `posts[]` with one snapshot in `metrics`. Trigger again and confirm a *second* snapshot was appended to the existing post entries (not a new post row).

## Testing Strategy

Unit tests in `tests/`:

- `tests/test_metric_collector_bluesky.py` — mock `requests.get` for `getPostThread`, assert counts mapped correctly, assert `None` returned on 404 / network error.
- `tests/test_metric_collector_mastodon.py` — mock the `Mastodon` SDK's `status()`, assert mapping + None on exception.
- `tests/test_metric_collector_instagram.py` — mock `requests.get` for the graph media endpoint, assert mapping, assert `reposts is None`.
- `tests/test_collect_metrics_orchestration.py` — fake `database.json` + fake collectors, assert: only `posts[]` entries within 14d window are polled; snapshot appended to the correct entry's `metrics[]`; entries with no matching registered collector are skipped; collector returning `None` doesn't append; missing top-level `posts` key is treated as empty.
- `tests/test_record_publish_results.py` — assert `posted_pets[]` gets one new entry; `posts[]` gets one row per successful publish (none for failed); `metrics: []` initialized empty; 12-week prune applied to both arrays independently.

Edge cases covered:

- Post entry with `posted_at` >14d ago → skipped by collector.
- All publishes for a pet failed → `posted_pets[]` gets the entry, `posts[]` gets nothing for that pet (pet still counts for dedup; no metrics ever collected).
- Collector raises → logged, returns None, no snapshot appended, loop continues.
- `database.json` missing or empty → both `pick_pet` and `collect_metrics` no-op gracefully.
- `posts[]` key missing on legacy artifact → treated as `[]`, new writes populate it.
- Mid-write crash → atomic rename via `.tmp` file means previous-known-good file stays intact.
- Pet pruned at 12wk → corresponding `posts[]` rows pruned in the same write (via independent `posted_at` filter, not a join — so even if `posted_at` somehow drifts between pet and post rows, no orphans accumulate).

Manual / workflow verification:

- Run `dev.yml` twice and inspect successive `database.json` artifacts for a growing `metrics` list.
- Eyeball one post's metric history vs the same post in the platform UI to spot-check accuracy.

## Resolved Decisions

- **Metric vocabulary**: persist `likes`, `reposts`, and `comments`. Do not add a separate `shares` field. Platform-native likes/favourites, reposts/reblogs, and replies/comments are normalized into those fields.
- **Unavailable metrics**: persist `null`, not `0`. `null` distinguishes “not exposed by this platform” from a real zero count. Instagram therefore stores `reposts: null`.
- **Dev workflow collector behavior**: `create_collectors(debug=True)` returns `[]`; debug runs exercise posting without making live metric API calls.
