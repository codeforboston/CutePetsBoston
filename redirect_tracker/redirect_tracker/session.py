import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

POSTGRES_USER_VAR = "POSTGRES_USER"
POSTGRES_USER_DEFAULT = "postgres"

POSTGRES_PASSWORD_VAR = "POSTGRES_PASSWORD"
POSTGRES_PASSWORD_DEFAULT = "postgres"

POSTGRES_HOST_VAR = "POSTGRES_HOST"
POSTGRES_HOST_DEFAULT = "postgres"

POSTGRES_PORT_VAR = "PORTGRES_PORT"
POSTGRES_PORT_DEFAULT = "5432"

POSTGRES_DATABASE_VAR = "POSTGRES_DB"
POSTGRES_DATABASE_DEFAULT = "redirect_tracker"


def get_connection_str() -> str:
    user = os.getenv(POSTGRES_USER_VAR, POSTGRES_USER_DEFAULT)
    password = os.getenv(POSTGRES_PASSWORD_VAR, POSTGRES_PASSWORD_DEFAULT)
    host = os.getenv(POSTGRES_HOST_VAR, POSTGRES_HOST_DEFAULT)
    port = os.getenv(POSTGRES_PORT_VAR, POSTGRES_PORT_DEFAULT)
    database = os.getenv(POSTGRES_DATABASE_VAR, POSTGRES_DATABASE_DEFAULT)

    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


engine = create_engine(get_connection_str())


def get_session() -> Generator:
    with Session(engine) as session:
        yield session
