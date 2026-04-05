import json
import logging
import sys
from datetime import datetime, timezone
from time import perf_counter

from flask import Response, current_app, g, has_request_context, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "shortener_http_requests_total",
    "Total number of HTTP requests handled by the app.",
    ["method", "route", "status_code"],
)
ERROR_COUNT = Counter(
    "shortener_http_errors_total",
    "Total number of HTTP responses with 4xx or 5xx status codes.",
    ["method", "route", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "shortener_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
REQUESTS_IN_PROGRESS = Gauge(
    "shortener_http_requests_in_progress",
    "Number of HTTP requests currently being handled.",
)

LOGGING_FORMATTED_HANDLER_MARKER = "_structured_json_handler"
METRICS_EXCLUDED_PATHS = {"/metrics"}
class JSONFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in ("status_code", "duration_ms", "response_size_bytes", "route"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)

        if has_request_context():
            payload.update(
                {
                    "request_id": getattr(g, "request_id", None),
                    "app_instance": current_app.config.get("APP_INSTANCE_NAME"),
                    "method": request.method,
                    "path": request.path,
                    "query_string": request.query_string.decode("utf-8"),
                    "remote_addr": request.headers.get("X-Forwarded-For", request.remote_addr),
                    "endpoint": request.endpoint,
                    "user_agent": request.headers.get("User-Agent"),
                }
            )

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def _metric_route():
    if request.path in METRICS_EXCLUDED_PATHS:
        return None
    if request.url_rule is not None:
        return request.url_rule.rule
    return "unmatched"


def _configure_logger(app):
    logger = logging.getLogger(app.name)
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    logger.setLevel(level)
    logger.propagate = False

    if not any(getattr(handler, LOGGING_FORMATTED_HANDLER_MARKER, False) for handler in logger.handlers):
        logger.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        setattr(handler, LOGGING_FORMATTED_HANDLER_MARKER, True)
        logger.addHandler(handler)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def init_observability(app):
    _configure_logger(app)

    @app.before_request
    def _start_request_observability():
        g.request_started_at = perf_counter()
        g._metrics_gauge_active = True
        REQUESTS_IN_PROGRESS.inc()

    @app.after_request
    def _record_request_observability(response):
        started_at = getattr(g, "request_started_at", None)
        duration_seconds = max(perf_counter() - started_at, 0.0) if started_at else 0.0
        duration_ms = round(duration_seconds * 1000, 3)
        route = _metric_route()
        status_code = str(response.status_code)

        if route is not None:
            REQUEST_COUNT.labels(request.method, route, status_code).inc()
            REQUEST_LATENCY.labels(request.method, route).observe(duration_seconds)
            if response.status_code >= 400:
                ERROR_COUNT.labels(request.method, route, status_code).inc()

        level = logging.INFO
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING

        app.logger.log(
            level,
            "request completed",
            extra={
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "response_size_bytes": response.calculate_content_length() or 0,
                "route": route or "excluded",
            },
        )
        return response

    @app.teardown_request
    def _finish_request_observability(exception):
        if getattr(g, "_metrics_gauge_active", False):
            REQUESTS_IN_PROGRESS.dec()
            g._metrics_gauge_active = False

    @app.route("/metrics", methods=["GET"])
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
