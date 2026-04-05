from datetime import datetime

from peewee import AutoField, BooleanField, CharField, DateTimeField, ForeignKeyField, TextField

from app.database import BaseModel
from app.models.user import User


class ShortUrl(BaseModel):
    id = AutoField()
    user = ForeignKeyField(User, backref="urls", on_delete="CASCADE")
    short_code = CharField(max_length=32, unique=True, index=True)
    original_url = TextField()
    title = CharField(max_length=255, null=True)
    is_active = BooleanField(default=True, index=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "urls"
