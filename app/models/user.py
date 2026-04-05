from datetime import datetime

from peewee import AutoField, CharField, DateTimeField

from app.database import BaseModel


class User(BaseModel):
    id = AutoField()
    username = CharField(index=True)
    email = CharField(unique=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "users"
