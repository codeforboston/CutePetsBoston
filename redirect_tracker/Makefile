.PHONY: start format lint lock-requirements migrate psql

start:
	docker compose up -d app-local

format:
	docker compose run devbox ruff format

lint:
	docker compose run devbox ruff check

lock-requirements:
	docker compose run --rm lock-requirements

migrate:
	docker compose run devbox alembic upgrade head

psql:
	docker compose exec postgres psql -U postgres -d redirect_tracker
