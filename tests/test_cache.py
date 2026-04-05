from flask import Flask

from app.cache import CACHE_STATS_KEY
from app.cache import get_cache_stats
from app.cache import get_url_snapshot
from app.cache import write_url_snapshot


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.operations = []

    def set(self, key, value, ex=None):
        self.operations.append(("set", key, value, ex))
        return self

    def hincrby(self, key, field_name, amount):
        self.operations.append(("hincrby", key, field_name, amount))
        return self

    def delete(self, key):
        self.operations.append(("delete", key))
        return self

    def execute(self):
        for operation in self.operations:
            if operation[0] == "set":
                _, key, value, _ = operation
                self.client.data[key] = value
            elif operation[0] == "hincrby":
                _, key, field_name, amount = operation
                bucket = self.client.hashes.setdefault(key, {})
                bucket[field_name] = int(bucket.get(field_name, 0)) + amount
            elif operation[0] == "delete":
                _, key = operation
                self.client.data.pop(key, None)
        self.operations.clear()
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.hashes = {}

    def get(self, key):
        return self.data.get(key)

    def hgetall(self, key):
        return self.hashes.get(key, {})

    def hincrby(self, key, field_name, amount):
        bucket = self.hashes.setdefault(key, {})
        bucket[field_name] = int(bucket.get(field_name, 0)) + amount
        return bucket[field_name]

    def pipeline(self):
        return FakePipeline(self)


def test_cache_stats_report_disabled_when_cache_client_missing():
    app = Flask(__name__)
    app.config["CACHE_TTL_SECONDS"] = 123
    app.extensions = {"cache_client": None}

    with app.app_context():
        stats = get_cache_stats()

    assert stats == {
        "enabled": False,
        "ttl_seconds": 123,
        "hits": 0,
        "misses": 0,
        "writes": 0,
        "invalidations": 0,
    }


def test_get_url_snapshot_fails_open_on_bad_cached_json():
    app = Flask(__name__)
    app.config["CACHE_TTL_SECONDS"] = 300
    client = FakeRedis()
    client.data["url:code:abc123"] = "{not-json"
    app.extensions = {"cache_client": client}

    with app.app_context():
        snapshot, cache_status = get_url_snapshot("abc123")

    assert snapshot is None
    assert cache_status == "BYPASS"


def test_write_url_snapshot_persists_keys_and_updates_stats():
    app = Flask(__name__)
    app.config["CACHE_TTL_SECONDS"] = 60
    client = FakeRedis()
    app.extensions = {"cache_client": client}
    snapshot = {
        "id": 7,
        "short_code": "abc123",
        "user_id": 2,
        "original_url": "https://example.com",
        "title": "Example",
        "is_active": True,
        "created_at": "2026-01-01 00:00:00",
        "updated_at": "2026-01-01 00:00:00",
    }

    with app.app_context():
        assert write_url_snapshot(snapshot) is True
        by_code, cache_status = get_url_snapshot("abc123")
        by_id, _ = get_url_snapshot("7")
        stats = get_cache_stats()

    assert cache_status == "HIT"
    assert by_code["id"] == 7
    assert by_id["short_code"] == "abc123"
    assert stats["writes"] == 1
    assert stats["hits"] == 2
    assert stats["misses"] == 0
    assert client.hashes[CACHE_STATS_KEY]["writes"] == 1
