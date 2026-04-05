import os

from dotenv import load_dotenv
from flask import Flask, jsonify

from app.database import create_tables, init_db
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

    from app import models  # noqa: F401 - registers models with Peewee

    if app.config["AUTO_CREATE_TABLES"]:
        create_tables(safe=True)

    if app.config["AUTO_LOAD_SEED_DATA"]:
        from app.seed.loader import load_seed_data

        load_seed_data(
            seed_directory=app.config["SEED_DIRECTORY"],
            reset=app.config["RESET_DATABASE_ON_STARTUP"],
        )

    register_routes(app)

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    return app
