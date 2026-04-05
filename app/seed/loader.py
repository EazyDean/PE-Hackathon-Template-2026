import csv
import json
from datetime import datetime
from pathlib import Path

from peewee import chunked

from app.database import create_tables, db, drop_tables
from app.models import ShortUrl, UrlEvent, User

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_timestamp(value):
    return datetime.strptime(value, TIMESTAMP_FORMAT)


def _parse_bool(value):
    return str(value).strip().lower() == "true"


def _read_csv(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_users(rows, batch_size):
    payload = [
        {
            "id": int(row["id"]),
            "username": row["username"],
            "email": row["email"],
            "created_at": _parse_timestamp(row["created_at"]),
        }
        for row in rows
    ]
    for batch in chunked(payload, batch_size):
        User.insert_many(batch).execute()


def _load_urls(rows, batch_size):
    payload = [
        {
            "id": int(row["id"]),
            "user": int(row["user_id"]),
            "short_code": row["short_code"],
            "original_url": row["original_url"],
            "title": row["title"] or None,
            "is_active": _parse_bool(row["is_active"]),
            "created_at": _parse_timestamp(row["created_at"]),
            "updated_at": _parse_timestamp(row["updated_at"]),
        }
        for row in rows
    ]
    for batch in chunked(payload, batch_size):
        ShortUrl.insert_many(batch).execute()


def _load_events(rows, batch_size):
    payload = [
        {
            "id": int(row["id"]),
            "url": int(row["url_id"]),
            "user": int(row["user_id"]),
            "event_type": row["event_type"],
            "timestamp": _parse_timestamp(row["timestamp"]),
            "details": json.loads(row["details"]),
        }
        for row in rows
    ]
    for batch in chunked(payload, batch_size):
        UrlEvent.insert_many(batch).execute()


def load_seed_data(seed_directory=None, *, reset=False, batch_size=200):
    seed_path = Path(seed_directory or Path(__file__).resolve().parent)

    if reset:
        drop_tables(safe=True)
    create_tables(safe=True)

    users_path = seed_path / "users.csv"
    urls_path = seed_path / "urls.csv"
    events_path = seed_path / "events.csv"

    with db.atomic():
        if reset:
            _load_users(_read_csv(users_path), batch_size)
            _load_urls(_read_csv(urls_path), batch_size)
            _load_events(_read_csv(events_path), batch_size)
            return

        if not User.select().exists():
            _load_users(_read_csv(users_path), batch_size)
        if not ShortUrl.select().exists():
            _load_urls(_read_csv(urls_path), batch_size)
        if not UrlEvent.select().exists():
            _load_events(_read_csv(events_path), batch_size)


if __name__ == "__main__":
    load_seed_data(reset=True)
