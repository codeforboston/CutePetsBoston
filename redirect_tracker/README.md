# redirect_tracker
A simple FastAPI application to log and redirect URL clicks on CutePetsBoston's posts.

## File Organization
- `main.py`: entrypoint for application, REST endpoint definitions.
- `alembic`: database migration configuration and versions.
- `redirect_tracker/dto.py`: data models validated via Pydantic.
- `redirect_tracker/model.py`: SQLAlchemy models.
- `redirect_tracker/session.py`: SQLAlchemy session implementations.

## Development
- `make start`: starts application for development.
- `make format`: formats project using ruff.
- `make lint`: lints project using ruff.
- `make lock-requirements`: locks requirement versions into `requirements.lock`.
- `make migrate`: applies all database migrations.
- `make psql`: opens a `psql` instance for your local database.
