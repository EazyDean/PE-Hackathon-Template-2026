import json
import logging

from flask import current_app
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

CACHE_STATS_KEY = "cache:stats"


def init_cache(app):
    if not app.config.get("CACHE_ENABLED", True):
        app.extensions["cache_client"] = None
        return

    app.extensions["cache_client"] = Redis.from_url(
        app.config["REDIS_URL"],
        decode_responses=True,
        socket_timeout=app.config["REDIS_TIMEOUT_SECONDS"],
        socket_connect_timeout=app.config["REDIS_TIMEOUT_SECONDS"],
        health_check_interval=30,
    )


def _client():
    return current_app.extensions.get("cache_client")


def _ttl_seconds():
    return int(current_app.config.get("CACHE_TTL_SECONDS", 300))


def _key_by_code(short_code):
    return f"url:code:{short_code}"


def _key_by_id(url_id):
    return f"url:id:{url_id}"


def _increment_stat(client, field_name):
    try:
        client.hincrby(CACHE_STATS_KEY, field_name, 1)
    except RedisError:
        logger.warning("Unable to increment cache stat '%s'", field_name, exc_info=True)


def get_url_snapshot(identifier):
    client = _client()
    if client is None:
        return None, "BYPASS"

    try:
        payload = client.get(_key_by_code(identifier))
        if payload:
            _increment_stat(client, "hits")
            return json.loads(payload), "HIT"

        if identifier.isdigit():
            payload = client.get(_key_by_id(int(identifier)))
            if payload:
                _increment_stat(client, "hits")
                return json.loads(payload), "HIT"

        _increment_stat(client, "misses")
        return None, "MISS"
    except (RedisError, TypeError, ValueError):
        logger.warning("Redis lookup failed for '%s'", identifier, exc_info=True)
        return None, "BYPASS"


def write_url_snapshot(snapshot):
    client = _client()
    if client is None:
        return False

    ttl_seconds = _ttl_seconds()
    payload = json.dumps(snapshot)

    try:
        with client.pipeline() as pipeline:
            pipeline.set(_key_by_code(snapshot["short_code"]), payload, ex=ttl_seconds)
            pipeline.set(_key_by_id(snapshot["id"]), payload, ex=ttl_seconds)
            pipeline.hincrby(CACHE_STATS_KEY, "writes", 1)
            pipeline.execute()
        return True
    except RedisError:
        logger.warning("Redis write failed for '%s'", snapshot["short_code"], exc_info=True)
        return False


def invalidate_url_snapshot(snapshot):
    client = _client()
    if client is None:
        return False

    try:
        with client.pipeline() as pipeline:
            pipeline.delete(_key_by_code(snapshot["short_code"]))
            pipeline.delete(_key_by_id(snapshot["id"]))
            pipeline.hincrby(CACHE_STATS_KEY, "invalidations", 1)
            pipeline.execute()
        return True
    except RedisError:
        logger.warning("Redis invalidation failed for '%s'", snapshot["short_code"], exc_info=True)
        return False


def get_cache_stats():
    client = _client()
    stats = {
        "enabled": client is not None,
        "ttl_seconds": _ttl_seconds(),
        "hits": 0,
        "misses": 0,
        "writes": 0,
        "invalidations": 0,
    }

    if client is None:
        return stats

    try:
        raw_stats = client.hgetall(CACHE_STATS_KEY)
    except RedisError:
        logger.warning("Redis stats lookup failed", exc_info=True)
        stats["enabled"] = False
        return stats

    for key in ("hits", "misses", "writes", "invalidations"):
        stats[key] = int(raw_stats.get(key, 0))

    total_lookups = stats["hits"] + stats["misses"]
    stats["hit_ratio"] = round(stats["hits"] / total_lookups, 4) if total_lookups else 0.0
    return stats
