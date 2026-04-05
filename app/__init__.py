import os
import socket
import uuid

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request

from app.cache import init_cache
from app.database import check_database_connection, create_tables, init_db
from app.observability import init_observability
from app.routes import register_routes


def _flag(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def create_app(config=None):
    load_dotenv()

    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_NAME=os.environ.get("DATABASE_NAME", "hackathon_db"),
        DATABASE_HOST=os.environ.get("DATABASE_HOST", "localhost"),
        DATABASE_PORT=int(os.environ.get("DATABASE_PORT", 5432)),
        DATABASE_USER=os.environ.get("DATABASE_USER", "postgres"),
        DATABASE_PASSWORD=os.environ.get("DATABASE_PASSWORD", "postgres"),
        APP_INSTANCE_NAME=os.environ.get("APP_INSTANCE_NAME", socket.gethostname()),
        LOG_LEVEL=os.environ.get("LOG_LEVEL", "INFO"),
        CACHE_ENABLED=_flag(os.environ.get("CACHE_ENABLED"), default=True),
        CACHE_TTL_SECONDS=int(os.environ.get("CACHE_TTL_SECONDS", 300)),
        REDIS_URL=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        REDIS_TIMEOUT_SECONDS=float(os.environ.get("REDIS_TIMEOUT_SECONDS", 0.5)),
        PROPAGATE_EXCEPTIONS=False,
        AUTO_CREATE_TABLES=_flag(os.environ.get("AUTO_CREATE_TABLES"), default=True),
        AUTO_LOAD_SEED_DATA=_flag(os.environ.get("AUTO_LOAD_SEED_DATA"), default=False),
        RESET_DATABASE_ON_STARTUP=_flag(
            os.environ.get("RESET_DATABASE_ON_STARTUP"),
            default=False,
        ),
        SEED_DIRECTORY=os.environ.get(
            "SEED_DIRECTORY",
            os.path.join(os.path.dirname(__file__), "seed"),
        ),
    )
    if config:
        app.config.update(config)

    init_db(app)
    init_cache(app)

    from app import models  # noqa: F401 - registers models with Peewee

    if app.config["AUTO_CREATE_TABLES"]:
        create_tables(safe=True)

    if app.config["AUTO_LOAD_SEED_DATA"]:
        from app.seed.loader import load_seed_data

        load_seed_data(
            seed_directory=app.config["SEED_DIRECTORY"],
            reset=app.config["RESET_DATABASE_ON_STARTUP"],
        )

    @app.before_request
    def _assign_request_id():
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex

    @app.after_request
    def _attach_request_id(response):
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        response.headers["X-App-Instance"] = app.config["APP_INSTANCE_NAME"]
        return response

    init_observability(app)
    register_routes(app)

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    @app.route("/ready")
    def ready():
        if check_database_connection():
            return jsonify(status="ok", database="ok")
        return jsonify(status="degraded", database="unavailable"), 503

    return app
