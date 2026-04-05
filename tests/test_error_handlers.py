from flask import Flask
from peewee import DatabaseError, IntegrityError, OperationalError
from werkzeug.exceptions import BadRequest, MethodNotAllowed, NotFound

from app.routes import register_routes
from app.routes.urls import APIError


def build_error_app():
    app = Flask(__name__)
    app.config.update(TESTING=False)
    register_routes(app)

    @app.get("/api-error")
    def api_error():
        raise APIError(418, "teapot", "Short and stout.")

    @app.get("/integrity-error")
    def integrity_error():
        raise IntegrityError("duplicate")

    @app.get("/operational-error")
    def operational_error():
        raise OperationalError("db down")

    @app.get("/database-error")
    def database_error():
        raise DatabaseError("db failed")

    @app.get("/generic-error")
    def generic_error():
        raise RuntimeError("boom")

    @app.get("/raise-not-found")
    def raise_not_found():
        raise NotFound()

    @app.get("/raise-bad-request")
    def raise_bad_request():
        raise BadRequest("Bad payload.")

    @app.get("/raise-method-not-allowed")
    def raise_method_not_allowed():
        raise MethodNotAllowed(valid_methods=["POST"])

    return app


def test_api_error_handler_returns_json():
    client = build_error_app().test_client()
    response = client.get("/api-error")

    assert response.status_code == 418
    assert response.get_json() == {"error": "teapot", "message": "Short and stout."}


def test_integrity_error_handler_returns_conflict_json():
    client = build_error_app().test_client()
    response = client.get("/integrity-error")

    assert response.status_code == 409
    assert response.get_json()["error"] == "conflict"


def test_operational_error_handler_returns_service_json():
    client = build_error_app().test_client()
    response = client.get("/operational-error")

    assert response.status_code == 503
    assert response.get_json()["error"] == "database_unavailable"


def test_database_error_handler_returns_json():
    client = build_error_app().test_client()
    response = client.get("/database-error")

    assert response.status_code == 500
    assert response.get_json()["error"] == "database_error"


def test_generic_error_handler_returns_json():
    client = build_error_app().test_client()
    response = client.get("/generic-error")

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal_server_error"


def test_http_error_handlers_return_json():
    client = build_error_app().test_client()

    bad_request = client.get("/raise-bad-request")
    not_found = client.get("/raise-not-found")
    wrong_method = client.get("/raise-method-not-allowed")

    assert bad_request.status_code == 400
    assert bad_request.get_json()["error"] == "bad_request"
    assert not_found.status_code == 404
    assert not_found.get_json()["error"] == "not_found"
    assert wrong_method.status_code == 405
    assert wrong_method.get_json()["error"] == "method_not_allowed"
