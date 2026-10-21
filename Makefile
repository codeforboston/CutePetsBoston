.PHONY: install lint format test

install:
	uv sync --locked
	git config core.hooksPath .githooks

lint:
	uv run --locked ruff check .
	uv run --locked ruff format --check .
	uv run --locked pyright

format:
	uv run --locked ruff check --select I --fix .
	uv run --locked ruff format .

test:
	uv run --locked pytest
