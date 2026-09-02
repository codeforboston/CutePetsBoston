# CutePetsBoston

# About

Posts a random adoptable pet from the Boston MSPCA to different social media feeds.

It should be easily extendable to other shelters and social media feeds for various locations.

## Github Actions

This Project runs on github actions and runs periodically.

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

    python main.py

To run only the Mastodon poster locally or in GitHub Actions:

    POSTER_PLATFORMS=mastodon python main.py

# History

This project was originally started by [Becky Boone](https://github.com/boonrs) and [Drew](https://github.com/drewrwilson) during their fellowship at Code for America in 2014.

## Sister Projects

- CutePetsDenver
