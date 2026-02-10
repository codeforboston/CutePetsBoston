# CutePetsBoston

# About

Posts a random adoptable pet from the Boston MSPCA to different social media feeds.

It should be easily extendable to other shelters and social media feeds for various locations.

## Github Actions

This Project runs on github actions and runs periodically.

## Set up your environment variables

Required:
- `RESCUEGROUPS_API_KEY`

Optional for Instagram posting:
- `INSTAGRAM_USERNAME`
- `INSTAGRAM_PASSWORD`

Optional for Bluesky posting:
- `BLUESKY_HANDLE` (or `BLUESKY_TEST_HANDLE`)
- `BLUESKY_PASSWORD` (or `BLUESKY_TEST_PASSWORD`)

## File organization

- `main.py`: orchestrates fetching pets and publishing posts.
- `abstractions.py`: shared interfaces and data models.
- `source_*.py`: pet source implementations (ingest from APIs).
- `poster_*.py`: social media poster implementations.
- `manually_test_post.py`: CLI for manual posting with sample data.

# How to run the script

    python main.py

# History

This project was originally started by [Becky Boone](https://github.com/boonrs) and [Drew](https://github.com/drewrwilson) during their fellowship at Code for America in 2014.

## Sister Projects

- CutePetsDenver
