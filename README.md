# CutePetsBoston

# About

Posts a random adoptable pet from the Boston MSPCA to different social media feeds.

It should be easily extendable to other shelters and social media feeds for various locations.

## Github Actions

This Project runs on github actions and runs periodically.

Team notes:

- [Meta account ecosystem](docs/meta-account-ecosystem.md): account setup, the developer portal, access tokens, and GitHub secrets.
- [Instagram debugging](docs/instagram-debugging.md): connection checks, test posts, logs, and troubleshooting.

## Development

### Install uv

On macOS or Linux, use the standalone installer:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Alternatively, if you use Homebrew:

```sh
brew install uv
```

On Windows, run this in PowerShell:

```powershell
winget install --id=astral-sh.uv -e
```

Open a new terminal after installation and verify that uv is available:

```sh
uv --version
```

See the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/)
for other installation methods.

### Set up the project

From the repository root, install the locked development environment:

```sh
make install
```

If Make is unavailable (for example, in Windows PowerShell), run:

```sh
uv sync --locked --dev
git config core.hooksPath .githooks
```

The `--dev` flag explicitly includes development tools such as Ruff, Pyright, and pytest.
Run Git directly: it does not need the Python environment managed by `uv run`.
The pre-commit hook calls `make format`, which runs Ruff through `uv run`.

uv manages `.venv` and uses Python 3.14 from `.python-version`. No environment activation is needed.
The Make targets use `--locked` to reject stale lockfiles.

Add runtime dependencies with `uv add PACKAGE` and development tools with
`uv add --dev PACKAGE`. Commit both `pyproject.toml` and `uv.lock` after dependency
changes. Use `uv lock` after editing dependency declarations manually.

- `make lint`: run Ruff lint checks, check formatting, and run Pyright.
- `make format`: sort imports and format Python files with Ruff.
- `make test`: run the pytest suite. The live API test is skipped unless
  `CUTEPETSBOSTON_RESCUEGROUPS_API_KEY` is set.

Pyright starts in basic mode. Ruff and Pyright exclude vendored code.

## Set up your environment variables

Required:
- `CUTEPETSBOSTON_RESCUEGROUPS_API_KEY`

Optional for Instagram posting:
- `INSTAGRAM_BUSINESS_ACCOUNT_ID` (or `INSTAGRAM_TEST_BUSINESS_ACCOUNT_ID`)
- `INSTAGRAM_PAGE_ACCESS_TOKEN` (or `INSTAGRAM_TEST_PAGE_ACCESS_TOKEN`)

Instagram tokens are renewed weekly by the **Refresh Instagram Tokens** workflow.
An administrator must first configure its GitHub App credentials; see
[automatic token renewal](docs/meta-account-ecosystem.md#automatic-token-renewal) for setup and recovery.

Optional for Bluesky posting:
- `BLUESKY_HANDLE` (or `BLUESKY_TEST_HANDLE`)
- `BLUESKY_PASSWORD` (or `BLUESKY_TEST_PASSWORD`)

Optional for Mastodon posting:
- `MASTODON_TOKEN` (map this to the appropriate production or test-account secret in the runtime environment)
- `MASTODON_API_BASE_URL` (defaults to `https://mastodon.social`)

Optional platform selection:
- `POSTER_PLATFORMS` to limit posting to specific platforms, for example `mastodon` or `bluesky,mastodon`

## File organization

- `main.py`: orchestrates fetching pets and publishing posts.
- `abstractions.py`: shared interfaces and data models.
- `source_*.py`: pet source implementations (ingest from APIs).
- `poster_*.py`: social media poster implementations.
- `manually_test_post.py`: CLI for manual posting with sample data.

# How to run the script

    uv run --locked python main.py --debugsources --debugposters

To run only the Mastodon poster locally or in GitHub Actions:

    POSTER_PLATFORMS=mastodon uv run --locked python main.py

## Adoption statuses

Refresh statuses in a downloaded database artifact without publishing any posts:

```sh
uv run --locked python refresh_pet_statuses.py --database-path database.json
uv run --locked python metrics_dashboard.py
```

The refresh command reads `CUTEPETSBOSTON_RESCUEGROUPS_API_KEY` from the environment.
The dashboard command reads `database.json` in the working directory and writes
`dashboard.html`; open that file in a browser to search, sort, and page through
the adoption-status table. Its JavaScript and styles load from a CDN.

Production runs these commands sequentially after posting, including when posting
fails. Non-adopted pets are checked once a day. After a week of consistently
missing source records, checks become weekly; a recovered record returns to daily
checks. Timeouts and service errors interrupt that missing-record streak and are
retried the next day. Failed lookups preserve the last known status and its
observation time. A source report of Adopted is final and ends further checks.

Pet records and existing engagement data are retained. The table shows the last
successfully observed status, not a guaranteed current status or the actual
adoption date. Pets without a known status appear as Unknown.

The workflow restores the latest completed production run with a database artifact,
including failed runs that saved status updates. Artifacts expire after 14 days;
if scheduled runs are interrupted longer than that, restore a saved database artifact
before resuming to avoid losing the archive.

# History

This project was originally started by [Becky Boone](https://github.com/boonrs) and [Drew](https://github.com/drewrwilson) during their fellowship at Code for America in 2014.

## Sister Projects

- CutePetsDenver
