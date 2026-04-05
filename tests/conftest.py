import os
import sys
from pathlib import Path

import psycopg2
import pytest
from psycopg2 import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.database import create_tables, db, drop_tables
from app.models import User


def _database_settings(database_name):
    return {
        "dbname": database_name,
        "host": os.environ.get("DATABASE_HOST", "localhost"),
        "port": int(os.environ.get("DATABASE_PORT", 5432)),
        "user": os.environ.get("DATABASE_USER", "postgres"),
        "password": os.environ.get("DATABASE_PASSWORD", "postgres"),
    }


def _ensure_database_exists(database_name):
    admin_database = os.environ.get("TEST_DATABASE_ADMIN", "postgres")
    connection = psycopg2.connect(**_database_settings(admin_database))
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
            if cursor.fetchone():
                return
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
            )
    finally:
        connection.close()


@pytest.fixture(scope="session")
def app():
    database_name = os.environ.get("TEST_DATABASE_NAME", "hackathon_test_db")
    try:
        _ensure_database_exists(database_name)
    except psycopg2.OperationalError as exc:
        pytest.skip(f"PostgreSQL is not available for tests: {exc}")

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_NAME": database_name,
            "AUTO_CREATE_TABLES": False,
            "AUTO_LOAD_SEED_DATA": False,
        }
    )

    @app.get("/_test/error")
    def _test_error():
        raise RuntimeError("boom")

    return app


@pytest.fixture()
def clean_database(app):
    drop_tables(safe=True)
    create_tables(safe=True)
    yield
    if not db.is_closed():
        db.close()


@pytest.fixture()
def client(app, clean_database):
    return app.test_client()


@pytest.fixture()
def seed_user(clean_database):
    return User.create(username="test-user", email="test-user@example.com")
