# CutePetsBoston

# About

Posts a random adoptable pet from the Boston MSPCA to different social media feeds.

It should be easily extendable to other shelters and social media feeds for various locations.

## Github Actions

This Project runs on github actions and runs periodically.

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

If Make is unavailable (for example, in Windows PowerShell), run `uv sync --locked` directly.

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

# History

This project was originally started by [Becky Boone](https://github.com/boonrs) and [Drew](https://github.com/drewrwilson) during their fellowship at Code for America in 2014.

## Sister Projects

- CutePetsDenver
