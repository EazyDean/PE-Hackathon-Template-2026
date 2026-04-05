import logging

from peewee import DatabaseError, IntegrityError, OperationalError
from werkzeug.exceptions import BadRequest, HTTPException, MethodNotAllowed, NotFound

from app.routes.urls import APIError, json_error, urls_bp

logger = logging.getLogger(__name__)


def register_routes(app):
    app.register_blueprint(urls_bp)

    @app.errorhandler(APIError)
    def _handle_api_error(error):
        return json_error(error.status_code, error.code, error.message, error.details)

    @app.errorhandler(BadRequest)
    def _handle_bad_request(error):
        return json_error(400, "bad_request", str(error.description))

    @app.errorhandler(NotFound)
    def _handle_not_found(error):
        return json_error(404, "not_found", "Resource was not found.")

    @app.errorhandler(MethodNotAllowed)
    def _handle_method_not_allowed(error):
        return json_error(405, "method_not_allowed", "Method is not allowed for this endpoint.")

    @app.errorhandler(IntegrityError)
    def _handle_integrity_error(error):
        return json_error(409, "conflict", "Request conflicts with stored data.")

    @app.errorhandler(OperationalError)
    def _handle_operational_error(error):
        logger.exception("Database operational error during request")
        return json_error(503, "database_unavailable", "Database is temporarily unavailable.")

    @app.errorhandler(DatabaseError)
    def _handle_database_error(error):
        logger.exception("Database error during request")
        return json_error(500, "database_error", "A database error occurred while handling the request.")

    @app.errorhandler(HTTPException)
    def _handle_http_exception(error):
        if error.code == 400:
            return json_error(400, "bad_request", str(error.description))
        if error.code == 415:
            return json_error(400, "invalid_json", "Request body must contain valid JSON.")
        return json_error(error.code or 500, "http_error", str(error.description))

    @app.errorhandler(Exception)
    def _handle_unexpected_error(error):
        logger.exception("Unhandled application error")
        return json_error(500, "internal_server_error", "An unexpected server error occurred.")
