# Adoption status reporting

The first-contribution scope and user-facing behavior below are agreed. Implementation notes identify the remaining engineering work, rather than additional features.

## Intended outcome

Show reported adoption statuses for previously posted pets in the analytics dashboard hosted on GitHub Pages. The existing notebook demonstrates status retrieval; the contribution needs a repeatable refresh rather than only a one-time enrichment.

Collect, retain, and expose the data needed to examine adoption outcomes alongside engagement over time. Calculating adoption rates or implementing trend analysis is deferred; the current goal is to make the underlying data available for inspection in the dashboard.

## First contribution

Keep the PR focused on displaying adoption statuses in the existing dashboard: retrieve and save statuses through a standalone command, invoke it for due pets in the existing sequential workflow, and add a searchable table with one row per pet. Include the necessary observation times, scheduling state, preservation of known statuses, and tests of this behavior.

Preserve existing data with minimal retention edits. Do not add engagement compaction, new engagement views, rate calculations, homepage changes, or a dashboard framework migration. Broader architecture changes require a demonstrated need to deliver the adoption-status feature.

## Agreed requirements

- Target daily automated status refreshes for tracked pets that have not reached Adopted. The dashboard may therefore lag the adoption source by about a day during normal operation; failed lookups or stale source data can make an observation older.
- After a week of consistently missing animal records, reduce that pet's lookups to weekly while preserving its last known status and successful observation time. Return to daily lookups if its record becomes available again. Timeouts and service errors do not establish a missing record or count toward this backoff.
- An unavailable lookup must not erase a previously known status with null or imply that the pet was adopted.
- Save and display the time each status was last successfully observed. Failed lookups must not advance this observation time. For Adopted, retain the first successful observation of that state; this is not a claim about the actual adoption date.
- Treat Adopted as a final tracked state, reached only through an explicit report from the adoption source. Preserve that state and stop subsequent status lookups for the pet. Later shelter corrections or returns to availability will therefore not be reflected.
- Keep all previously posted pets and their tracked statuses in the database without an age cutoff, including pets not confirmed adopted. The existing 12-week pruning of pet records must change.
- A posted pet means a distinct pet with at least one successful platform publication. Correcting the existing recording of fully failed publication attempts belongs to a separate, noncritical issue; it is not a prerequisite for this contribution.
- Preserve existing saved engagement data initially; implementing the agreed two-week compaction policy belongs to a follow-up contribution.
- Provide a standalone status-refresh command that operates on the supplied database without publishing any social posts or requiring social posting credentials.
- Run status refreshes as a separate step in the existing production workflow, sequentially with posting against the same database file. The four-hour workflow schedule checks which pets are due; it must not cause four-hour status polling. Do not introduce a second scheduled database writer.
- Status refreshes must be able to run when posting fails. Persist their successful updates and make them available to subsequent runs and dashboard generation even when posting fails.
- The main dashboard table has one row per pet and exactly five columns: Name, Pet ID, Posted date, Adoption status, and Status last observed. Include search, sorting, and pagination. Platform posts must not create duplicate pet rows.

## Deferred work

- Engagement-history compaction and new engagement displays.
- Adoption-rate calculations and trend analysis.
- Homepage pagination and adoption badges.
- Streamlit or another dashboard framework migration.
- Fixing the publication-recording bug, tracked by the user's separate issue. Existing `posted_pets` records may include failed attempts and must not be presented as a verified count of successfully featured pets.

## Follow-up engagement retention policy

Keep detailed engagement time series during the first 14 days after publication, then compact each post's history to its latest saved snapshot. Preserve that snapshot and the post's identity indefinitely.

Engagement snapshots contain cumulative counts. For example, observations of 2, 5, and 7 likes leave a last observed count of 7, not a sum of 14. Retaining a summary per post preserves the association with a pet and platform for future comparisons.

The retained snapshot describes the last successful observation within the collection window, not a guaranteed measurement exactly at day 14 or a lifetime total. The persisted representation and treatment of posts without observations remain to be specified.

## Implementation notes

- Extend the existing pet records with optional status metadata. Existing database files must remain readable; pets without a known status display Unknown. Keep unknown statuses distinct from explicit source reports.
- Optional pet fields are `status_id`, `status_name`, `status_observed_at`, `status_checked_at`, and `status_missing_since`. The successful observation time is separate from the latest attempt and missing-record scheduling state, so failed lookups do not appear to verify the saved status.
- Populate historical pets through the same refresh command against the authoritative database. The notebook is reference logic; scratch database files must not replace production state, and its previously observed adoption count is not a guaranteed current result.
- Show the adoption table even when there are no published-post metrics. The current dashboard returns early in that case; the new table must not depend on engagement data being available.
- Recover the latest completed workflow run with a nonexpired database artifact, including failed runs that saved updates. Upload the database even after a posting failure. Discovery/download errors stop posting rather than silently creating replacement state; a first run without a previous artifact can start normally.
- Extract only the required lookup logic from the notebook. Use the existing RescueGroups credential, a bounded request timeout, and per-run status metadata caching; a failure for one pet must not erase other pets' saved statuses.

## Table implementation

Use ITables to generate the five-column table as an HTML fragment embedded in the existing generated dashboard. Its `to_html_datatable` export supports this approach; validate the exported table in a browser as part of implementation. Generate table data from the database during the workflow, so visitors receive it with the page.

Sources: [ITables HTML export](https://itables.org/apps/html.html), [ITables quick start](https://itables.org/index.html).

## Acceptance checks for the first contribution

- The standalone command refreshes due pets without publishing posts, skips Adopted pets, and applies the agreed daily/weekly policy.
- Successful lookups update the saved status and observation time; unsuccessful lookups preserve both. Missing IDs trigger no API request.
- Historical records without status fields remain visible as Unknown. Multiple platform posts do not multiply pet rows.
- The generated dashboard shows the five-column table, including when engagement data is absent, with working search, sorting, and pagination in a browser.
- Status updates survive a posting failure and are available to the next workflow run and dashboard generation.
- The diff is limited to the lookup command, necessary schema/retention and workflow edits, dashboard integration, dependency/lockfile changes for ITables, focused tests, and usage documentation. Existing exploratory files are not part of the contribution.

## Repository observations before this contribution

- `main.py` generates the analytics dashboard after posting and collecting engagement metrics.
- `.github/workflows/prod.yml` schedules posting every four hours and passes `database.json` between runs as an artifact.
- `main.py::record_publish_results()` removes pet and post records older than 12 weeks.
- `web/index.html` reads a Mastodon RSS feed and displays at most eight pet cards. It does not read the database.

See [the glossary](../../CONTEXT.md) for the distinction between a pet, a published post, a reported adoption status, and a status lookup.
