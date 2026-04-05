from datetime import datetime

from peewee import AutoField, CharField, DateTimeField, ForeignKeyField
from playhouse.postgres_ext import BinaryJSONField

from app.database import BaseModel
from app.models.short_url import ShortUrl
from app.models.user import User


class UrlEvent(BaseModel):
    id = AutoField()
    url = ForeignKeyField(ShortUrl, backref="events", on_delete="CASCADE")
    user = ForeignKeyField(User, backref="events", on_delete="CASCADE")
    event_type = CharField(max_length=32, index=True)
    timestamp = DateTimeField(default=datetime.utcnow, index=True)
    details = BinaryJSONField(default=dict)

    class Meta:
        table_name = "events"
