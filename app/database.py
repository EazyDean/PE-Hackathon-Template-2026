import os

from flask import request
from peewee import DatabaseProxy, Model
from playhouse.postgres_ext import PostgresqlExtDatabase

db = DatabaseProxy()
DB_OPTIONAL_ENDPOINTS = {"health", "ready", "metrics"}


class BaseModel(Model):
    class Meta:
        database = db


def init_db(app):
    database = PostgresqlExtDatabase(
        app.config.get("DATABASE_NAME", os.environ.get("DATABASE_NAME", "hackathon_db")),
        host=app.config.get("DATABASE_HOST", os.environ.get("DATABASE_HOST", "localhost")),
        port=int(app.config.get("DATABASE_PORT", os.environ.get("DATABASE_PORT", 5432))),
        user=app.config.get("DATABASE_USER", os.environ.get("DATABASE_USER", "postgres")),
        password=app.config.get(
            "DATABASE_PASSWORD",
            os.environ.get("DATABASE_PASSWORD", "postgres"),
        ),
    )
    db.initialize(database)

    @app.before_request
    def _db_connect():
        if request.endpoint in DB_OPTIONAL_ENDPOINTS:
            return
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()


def get_models():
    from app.models import ALL_MODELS

    return ALL_MODELS


def create_tables(*, safe=True):
    models = get_models()
    if db.is_closed():
        db.connect(reuse_if_open=True)
    db.create_tables(models, safe=safe)


def drop_tables(*, safe=True):
    models = list(reversed(get_models()))
    if db.is_closed():
        db.connect(reuse_if_open=True)
    db.drop_tables(models, safe=safe)


def check_database_connection():
    opened_here = False
    try:
        if db.is_closed():
            db.connect(reuse_if_open=True)
            opened_here = True
        db.execute_sql("SELECT 1")
        return True
    except Exception:
        return False
    finally:
        if opened_here and not db.is_closed():
            db.close()
