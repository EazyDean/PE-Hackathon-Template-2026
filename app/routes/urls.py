import re
import secrets
from datetime import datetime
from urllib.parse import urlparse

from flask import Blueprint, jsonify, redirect, request
from peewee import DoesNotExist, IntegrityError

from app.cache import get_cache_stats
from app.cache import get_url_snapshot as get_cached_url_snapshot
from app.cache import invalidate_url_snapshot
from app.cache import write_url_snapshot
from app.database import db
from app.models import ShortUrl, UrlEvent, User

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
SHORT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{3,32}$")
ALLOWED_DELETE_REASONS = {"duplicate", "user_requested", "expired", "policy_cleanup"}
RESERVED_PATHS = {"api", "events", "health", "internal", "metrics", "ready", "urls", "users"}
MAX_SHORT_CODE_INSERT_RETRIES = 8

urls_bp = Blueprint("urls", __name__)


class APIError(Exception):
    def __init__(self, status_code, code, message, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def _timestamp(value):
    return value.strftime(TIMESTAMP_FORMAT)


def _db_error_code(error):
    cause = getattr(error, "__cause__", None)
    return getattr(cause, "pgcode", None)


def _db_error_text(error):
    cause = getattr(error, "__cause__", None)
    return str(cause or error).lower()


def _is_unique_violation(error, field_hint=None):
    if _db_error_code(error) == "23505":
        if field_hint is None:
            return True
        error_text = _db_error_text(error)
        return (
            field_hint in error_text
            or "duplicate key" in error_text
            or "unique constraint" in error_text
        )
    return False


def _bool_param(value):
    lowered = value.lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    raise APIError(400, "invalid_query", "Boolean query parameters must be true or false.")


def _short_link(short_code):
    return f"{request.url_root.rstrip('/')}/{short_code}"


def serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": _timestamp(user.created_at),
    }


def serialize_short_url(short_url):
    return {
        "id": short_url.id,
        "user_id": short_url.user_id,
        "short_code": short_url.short_code,
        "short_url": _short_link(short_url.short_code),
        "original_url": short_url.original_url,
        "title": short_url.title,
        "is_active": short_url.is_active,
        "created_at": _timestamp(short_url.created_at),
        "updated_at": _timestamp(short_url.updated_at),
    }


def snapshot_short_url(short_url):
    return {
        "id": short_url.id,
        "user_id": short_url.user_id,
        "short_code": short_url.short_code,
        "original_url": short_url.original_url,
        "title": short_url.title,
        "is_active": short_url.is_active,
        "created_at": _timestamp(short_url.created_at),
        "updated_at": _timestamp(short_url.updated_at),
    }


def serialize_short_url_snapshot(snapshot):
    return {
        "id": snapshot["id"],
        "user_id": snapshot["user_id"],
        "short_code": snapshot["short_code"],
        "short_url": _short_link(snapshot["short_code"]),
        "original_url": snapshot["original_url"],
        "title": snapshot.get("title"),
        "is_active": snapshot["is_active"],
        "created_at": snapshot["created_at"],
        "updated_at": snapshot["updated_at"],
    }


def serialize_event(event):
    return {
        "id": event.id,
        "url_id": event.url_id,
        "user_id": event.user_id,
        "event_type": event.event_type,
        "timestamp": _timestamp(event.timestamp),
        "details": event.details,
    }


def json_error(status_code, code, message, details=None):
    payload = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status_code


def _reject_unknown_fields(payload, allowed_fields):
    unknown_fields = sorted(set(payload) - set(allowed_fields))
    if unknown_fields:
        raise APIError(
            400,
            "validation_error",
            "Request body contains unsupported fields.",
            {"fields": unknown_fields},
        )


def _parse_json_body(*, required=True):
    if not request.data:
        if required:
            raise APIError(400, "invalid_json", "Request body must be a JSON object.")
        return {}

    try:
        payload = request.get_json(force=False, silent=False)
    except Exception as exc:
        raise APIError(400, "invalid_json", "Request body must contain valid JSON.") from exc

    if payload is None:
        raise APIError(400, "invalid_json", "Request body must be a JSON object.")

    if not isinstance(payload, dict):
        raise APIError(400, "invalid_json", "Request body must be a JSON object.")

    return payload


def _require_field(payload, field_name):
    if field_name not in payload:
        raise APIError(400, "validation_error", f"'{field_name}' is required.")
    return payload[field_name]


def _require_string(payload, field_name, *, allow_null=False):
    value = _require_field(payload, field_name)
    if value is None:
        if allow_null:
            return None
        raise APIError(400, "validation_error", f"'{field_name}' is required.")
    if not isinstance(value, str):
        raise APIError(400, "validation_error", f"'{field_name}' must be a string.")
    value = value.strip()
    if not value and not allow_null:
        raise APIError(400, "validation_error", f"'{field_name}' must not be empty.")
    return value or None


def _optional_string(payload, field_name, *, allow_null=True, blank_to_none=False):
    if field_name not in payload:
        return None
    value = payload[field_name]
    if value is None:
        if allow_null:
            return None
        raise APIError(400, "validation_error", f"'{field_name}' must be a string.")
    if not isinstance(value, str):
        raise APIError(400, "validation_error", f"'{field_name}' must be a string.")
    value = value.strip()
    if not value:
        if blank_to_none:
            return None
        raise APIError(400, "validation_error", f"'{field_name}' must not be empty.")
    return value


def _require_positive_int(payload, field_name):
    value = _require_field(payload, field_name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise APIError(400, "validation_error", f"'{field_name}' must be an integer.")
    if value <= 0:
        raise APIError(400, "validation_error", f"'{field_name}' must be a positive integer.")
    return value


def _optional_bool(payload, field_name, *, default=None):
    if field_name not in payload:
        return default
    value = payload[field_name]
    if not isinstance(value, bool):
        raise APIError(400, "validation_error", f"'{field_name}' must be a boolean.")
    return value


def _validate_original_url(original_url):
    parsed = urlparse(original_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise APIError(400, "validation_error", "'original_url' must be a valid http or https URL.")
    return original_url


def _validate_short_code(short_code):
    if short_code in RESERVED_PATHS:
        raise APIError(400, "validation_error", "'short_code' conflicts with a reserved path.")
    if not SHORT_CODE_PATTERN.fullmatch(short_code):
        raise APIError(
            400,
            "validation_error",
            "'short_code' must be 3-32 alphanumeric characters.",
        )
    return short_code


def _validate_email(email):
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise APIError(400, "validation_error", "'email' must be a valid email address.")
    return email


def _parse_positive_int_query(value, field_name):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise APIError(400, "invalid_query", f"'{field_name}' must be an integer.") from exc
    if parsed <= 0:
        raise APIError(400, "invalid_query", f"'{field_name}' must be a positive integer.")
    return parsed


def _get_user_or_404(user_id):
    if user_id <= 0:
        raise APIError(400, "validation_error", "'user_id' must be a positive integer.")
    try:
        return User.get_by_id(user_id)
    except DoesNotExist as exc:
        raise APIError(404, "not_found", f"User '{user_id}' does not exist.") from exc


def _get_short_url_by_id_or_404(url_id):
    if url_id <= 0:
        raise APIError(400, "validation_error", "'url_id' must be a positive integer.")
    try:
        return ShortUrl.get_by_id(url_id)
    except DoesNotExist as exc:
        raise APIError(404, "not_found", f"URL '{url_id}' does not exist.") from exc


def _get_short_url_or_404(identifier):
    short_url = ShortUrl.get_or_none(ShortUrl.short_code == identifier)
    if short_url is not None:
        return short_url

    if identifier.isdigit():
        return _get_short_url_by_id_or_404(int(identifier))

    if not SHORT_CODE_PATTERN.fullmatch(identifier):
        raise APIError(
            400,
            "validation_error",
            "'short_code' must be 3-32 alphanumeric characters.",
        )

    raise APIError(404, "not_found", f"Short code '{identifier}' was not found.")


def _parse_existing_user_id_query(value, field_name="user_id"):
    user_id = _parse_positive_int_query(value, field_name)
    _get_user_or_404(user_id)
    return user_id


def _normalize_delete_reason(value):
    if not isinstance(value, str):
        raise APIError(400, "validation_error", "'reason' must be a string.")
    reason = value.strip()
    if not reason:
        raise APIError(400, "validation_error", "'reason' must not be empty.")
    if reason not in ALLOWED_DELETE_REASONS:
        raise APIError(
            400,
            "validation_error",
            "'reason' must be one of duplicate, user_requested, expired, or policy_cleanup.",
        )
    return reason


def _generate_short_code(length=6):
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    for _ in range(32):
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if candidate not in RESERVED_PATHS and not ShortUrl.select().where(
            ShortUrl.short_code == candidate
        ).exists():
            return candidate
    raise APIError(503, "code_generation_failed", "Unable to allocate a unique short code.")


def _log_event(short_url, event_type, *, details=None, timestamp=None):
    return UrlEvent.create(
        url=short_url,
        user=short_url.user,
        event_type=event_type,
        timestamp=timestamp or datetime.utcnow(),
        details=details or {},
    )


def _log_event_for_snapshot(snapshot, event_type, *, details=None, timestamp=None):
    return UrlEvent.create(
        url=snapshot["id"],
        user=snapshot["user_id"],
        event_type=event_type,
        timestamp=timestamp or datetime.utcnow(),
        details=details or {},
    )


def _create_short_url_record(*, user, original_url, title, is_active, short_code=None):
    manual_short_code = short_code is not None
    retries = 1 if manual_short_code else MAX_SHORT_CODE_INSERT_RETRIES

    for _ in range(retries):
        candidate = short_code or _generate_short_code()
        short_code_exists = ShortUrl.select().where(ShortUrl.short_code == candidate).exists()
        if short_code_exists:
            if manual_short_code:
                raise APIError(409, "conflict", f"Short code '{candidate}' already exists.")
            continue

        now = datetime.utcnow().replace(microsecond=0)
        try:
            with db.atomic():
                short_url = ShortUrl.create(
                    user=user,
                    short_code=candidate,
                    original_url=original_url,
                    title=title,
                    is_active=is_active,
                    created_at=now,
                    updated_at=now,
                )
                _log_event(
                    short_url,
                    "created",
                    details={"short_code": candidate, "original_url": original_url},
                    timestamp=now,
                )
                return short_url
        except IntegrityError as exc:
            if _is_unique_violation(exc):
                if manual_short_code:
                    raise APIError(409, "conflict", f"Short code '{candidate}' already exists.") from exc
                continue
            raise

    raise APIError(503, "code_generation_failed", "Unable to allocate a unique short code.")


@urls_bp.route("/urls", methods=["GET"])
@urls_bp.route("/api/urls", methods=["GET"])
def list_urls():
    query = ShortUrl.select().order_by(ShortUrl.id)

    user_id = request.args.get("user_id")
    if user_id is not None:
        user_id = _parse_existing_user_id_query(user_id, "user_id")
        query = query.where(ShortUrl.user_id == user_id)

    active = request.args.get("active")
    if active is None:
        active = request.args.get("is_active")
    if active is not None:
        query = query.where(ShortUrl.is_active == _bool_param(active))

    items = [serialize_short_url(short_url) for short_url in query]
    return jsonify({"count": len(items), "items": items})


@urls_bp.route("/users", methods=["GET"])
@urls_bp.route("/api/users", methods=["GET"])
def list_users():
    query = User.select().order_by(User.id)
    items = [serialize_user(user) for user in query]
    return jsonify({"count": len(items), "items": items})


@urls_bp.route("/users", methods=["POST"])
@urls_bp.route("/api/users", methods=["POST"])
def create_user():
    payload = _parse_json_body()
    _reject_unknown_fields(payload, {"email", "username"})

    username = _require_string(payload, "username")
    email = _validate_email(_require_string(payload, "email"))
    now = datetime.utcnow().replace(microsecond=0)

    try:
        user = User.create(username=username, email=email, created_at=now)
    except IntegrityError as exc:
        if _is_unique_violation(exc, "email"):
            raise APIError(409, "conflict", f"Email '{email}' already exists.") from exc
        raise

    return jsonify(serialize_user(user)), 201


@urls_bp.route("/users/<int:user_id>", methods=["GET"])
@urls_bp.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = _get_user_or_404(user_id)
    payload = serialize_user(user)
    payload["url_count"] = user.urls.count()
    return jsonify(payload)


@urls_bp.route("/users/<int:user_id>/urls", methods=["GET"])
@urls_bp.route("/api/users/<int:user_id>/urls", methods=["GET"])
def list_user_urls(user_id):
    user = _get_user_or_404(user_id)
    items = [serialize_short_url(short_url) for short_url in user.urls.order_by(ShortUrl.id)]
    return jsonify({"user": serialize_user(user), "count": len(items), "items": items})


@urls_bp.route("/urls", methods=["POST"])
@urls_bp.route("/api/urls", methods=["POST"])
def create_url():
    payload = _parse_json_body()
    _reject_unknown_fields(payload, {"is_active", "original_url", "short_code", "title", "user_id"})

    user_id = _require_positive_int(payload, "user_id")
    original_url = _validate_original_url(_require_string(payload, "original_url"))
    title = _optional_string(payload, "title", allow_null=True, blank_to_none=True)
    is_active = _optional_bool(payload, "is_active", default=True)

    if "short_code" in payload and payload["short_code"] is not None:
        short_code = _validate_short_code(_require_string(payload, "short_code"))
    else:
        short_code = None

    user = _get_user_or_404(user_id)

    short_url = _create_short_url_record(
        user=user,
        original_url=original_url,
        title=title,
        is_active=is_active,
        short_code=short_code,
    )
    write_url_snapshot(snapshot_short_url(short_url))

    return jsonify(serialize_short_url(short_url)), 201


@urls_bp.route("/urls/<string:short_code>", methods=["GET"])
@urls_bp.route("/api/urls/<string:short_code>", methods=["GET"])
def get_url(short_code):
    snapshot, cache_status = get_cached_url_snapshot(short_code)
    if snapshot is None:
        short_url = _get_short_url_or_404(short_code)
        snapshot = snapshot_short_url(short_url)
        write_url_snapshot(snapshot)

    payload = serialize_short_url_snapshot(snapshot)
    payload["event_count"] = UrlEvent.select().where(UrlEvent.url_id == snapshot["id"]).count()
    response = jsonify(payload)
    response.headers["X-Cache"] = cache_status
    return response


@urls_bp.route("/urls/<string:short_code>", methods=["PATCH"])
@urls_bp.route("/api/urls/<string:short_code>", methods=["PATCH"])
def update_url(short_code):
    short_url = _get_short_url_or_404(short_code)
    payload = _parse_json_body()
    _reject_unknown_fields(payload, {"is_active", "original_url", "title"})
    if not payload:
        raise APIError(400, "validation_error", "At least one mutable field is required.")

    changes = {}
    if "original_url" in payload:
        changes["original_url"] = _validate_original_url(_require_string(payload, "original_url"))
    if "title" in payload:
        changes["title"] = _optional_string(payload, "title", allow_null=True, blank_to_none=True)
    if "is_active" in payload:
        changes["is_active"] = _optional_bool(payload, "is_active")

    changed_fields = []
    for field_name, new_value in changes.items():
        if getattr(short_url, field_name) != new_value:
            changed_fields.append((field_name, new_value))

    if not changed_fields:
        return jsonify(serialize_short_url(short_url))

    now = datetime.utcnow().replace(microsecond=0)
    with db.atomic():
        for field_name, new_value in changed_fields:
            setattr(short_url, field_name, new_value)
        short_url.updated_at = now
        short_url.save()

        for field_name, new_value in changed_fields:
            _log_event(
                short_url,
                "updated",
                details={"field": field_name, "new_value": new_value},
                timestamp=now,
            )

    updated_snapshot = snapshot_short_url(short_url)
    invalidate_url_snapshot(updated_snapshot)
    write_url_snapshot(updated_snapshot)
    return jsonify(serialize_short_url(short_url))


@urls_bp.route("/urls/<string:short_code>", methods=["DELETE"])
@urls_bp.route("/api/urls/<string:short_code>", methods=["DELETE"])
def delete_url(short_code):
    short_url = _get_short_url_or_404(short_code)
    payload = _parse_json_body(required=False)
    _reject_unknown_fields(payload, {"reason"})

    reason = _normalize_delete_reason(payload.get("reason", "user_requested"))

    if short_url.is_active:
        now = datetime.utcnow().replace(microsecond=0)
        with db.atomic():
            short_url.is_active = False
            short_url.updated_at = now
            short_url.save()
            _log_event(short_url, "deleted", details={"reason": reason}, timestamp=now)

        deleted_snapshot = snapshot_short_url(short_url)
        invalidate_url_snapshot(deleted_snapshot)
        write_url_snapshot(deleted_snapshot)

    return jsonify(serialize_short_url(short_url))


@urls_bp.route("/urls/<string:short_code>/events", methods=["GET"])
@urls_bp.route("/api/urls/<string:short_code>/events", methods=["GET"])
def list_url_events(short_code):
    short_url = _get_short_url_or_404(short_code)
    query = short_url.events.order_by(UrlEvent.timestamp, UrlEvent.id)
    items = [serialize_event(event) for event in query]
    return jsonify({"short_code": short_url.short_code, "count": len(items), "items": items})


@urls_bp.route("/events", methods=["GET"])
@urls_bp.route("/api/events", methods=["GET"])
def list_events():
    query = UrlEvent.select().order_by(UrlEvent.timestamp, UrlEvent.id)

    short_code = request.args.get("short_code")
    if short_code:
        short_url = _get_short_url_or_404(short_code)
        query = query.where(UrlEvent.url_id == short_url.id)

    url_id = request.args.get("url_id")
    if url_id is not None:
        short_url = _get_short_url_by_id_or_404(_parse_positive_int_query(url_id, "url_id"))
        query = query.where(UrlEvent.url_id == short_url.id)

    user_id = request.args.get("user_id")
    if user_id is not None:
        user_id = _parse_existing_user_id_query(user_id, "user_id")
        query = query.where(UrlEvent.user_id == user_id)

    event_type = request.args.get("event_type")
    if event_type:
        query = query.where(UrlEvent.event_type == event_type)

    items = [serialize_event(event) for event in query]
    return jsonify({"count": len(items), "items": items})


@urls_bp.route("/internal/cache/stats", methods=["GET"])
@urls_bp.route("/api/internal/cache/stats", methods=["GET"])
def cache_stats():
    return jsonify(get_cache_stats())


@urls_bp.route("/<string:short_code>", methods=["GET"])
def resolve_short_code(short_code):
    if short_code in RESERVED_PATHS:
        raise APIError(404, "not_found", "Resource was not found.")

    snapshot, cache_status = get_cached_url_snapshot(short_code)
    if snapshot is None:
        short_url = _get_short_url_or_404(short_code)
        snapshot = snapshot_short_url(short_url)
        write_url_snapshot(snapshot)

    if not snapshot["is_active"]:
        raise APIError(410, "inactive", f"Short code '{short_code}' is inactive.")

    now = datetime.utcnow().replace(microsecond=0)
    with db.atomic():
        _log_event_for_snapshot(
            snapshot,
            "visited",
            details={
                "destination": snapshot["original_url"],
                "referrer": request.referrer,
                "user_agent": request.headers.get("User-Agent"),
            },
            timestamp=now,
        )

    response = redirect(snapshot["original_url"], code=302)
    response.headers["X-Cache"] = cache_status
    return response
