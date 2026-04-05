import json
import logging

from flask import Flask, g

from app.observability import JSONFormatter
from app.observability import init_observability


def build_observability_app():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        APP_INSTANCE_NAME="test-observability-app",
        LOG_LEVEL="INFO",
    )
    init_observability(app)
    return app


def test_metrics_endpoint_exposes_prometheus_metrics():
    app = build_observability_app()
    client = app.test_client()

    response = client.get("/metrics")

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "text/plain" in response.headers["Content-Type"]
    assert "shortener_http_requests_total" in body
    assert "shortener_http_request_duration_seconds" in body
    assert "shortener_http_requests_in_progress" in body


def test_json_formatter_includes_request_context_and_extra_fields():
    app = Flask(__name__)
    formatter = JSONFormatter()

    with app.test_request_context(
        "/api/urls?active=true",
        headers={"User-Agent": "pytest", "X-Forwarded-For": "203.0.113.1"},
    ):
        g.request_id = "req-123"
        app.config["APP_INSTANCE_NAME"] = "web-test"
        record = logging.LogRecord("app", logging.INFO, __file__, 10, "request completed", (), None)
        record.status_code = 200
        record.duration_ms = 12.5
        record.response_size_bytes = 256
        record.route = "/api/urls"

        payload = json.loads(formatter.format(record))

    assert payload["message"] == "request completed"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-123"
    assert payload["app_instance"] == "web-test"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/urls"
    assert payload["query_string"] == "active=true"
    assert payload["remote_addr"] == "203.0.113.1"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 12.5
    assert payload["response_size_bytes"] == 256


def test_metrics_endpoint_skips_database_connection():
    app = build_observability_app()

    response = app.test_client().get("/metrics")

    assert response.status_code == 200
