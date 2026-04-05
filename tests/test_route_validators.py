from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from peewee import IntegrityError

from app.routes.urls import APIError
from app.routes.urls import _create_short_url_record
from app.routes.urls import _normalize_delete_reason
from app.routes.urls import _parse_positive_int_query
from app.routes.urls import _reject_unknown_fields
from app.routes.urls import _validate_email
from app.routes.urls import _validate_original_url
from app.routes.urls import _validate_short_code


def test_validate_original_url_accepts_http_and_https():
    assert _validate_original_url("https://example.com/path") == "https://example.com/path"
    assert _validate_original_url("http://example.com/path") == "http://example.com/path"


@pytest.mark.parametrize("value", ["ftp://example.com/file", "example.com/path", ""])
def test_validate_original_url_rejects_invalid_values(value):
    with pytest.raises(APIError) as error:
        _validate_original_url(value)

    assert error.value.status_code == 400
    assert error.value.code == "validation_error"


@pytest.mark.parametrize("reserved_path", ["health", "ready", "internal", "metrics"])
def test_validate_short_code_rejects_reserved_path(reserved_path):
    with pytest.raises(APIError) as error:
        _validate_short_code(reserved_path)

    assert error.value.status_code == 400
    assert error.value.code == "validation_error"


@pytest.mark.parametrize("value", ["ab", "bad-code", "contains space", "!!!!!!"])
def test_validate_short_code_rejects_invalid_shape(value):
    with pytest.raises(APIError) as error:
        _validate_short_code(value)

    assert error.value.status_code == 400


def test_validate_email_rejects_invalid_shape():
    with pytest.raises(APIError) as error:
        _validate_email("not-an-email")

    assert error.value.status_code == 400
    assert error.value.code == "validation_error"


def test_parse_positive_int_query_rejects_zero_and_non_numbers():
    for raw_value in ("0", "-1", "not-a-number"):
        with pytest.raises(APIError) as error:
            _parse_positive_int_query(raw_value, "user_id")

        assert error.value.status_code == 400


def test_normalize_delete_reason_trims_and_accepts_known_value():
    assert _normalize_delete_reason(" expired ") == "expired"


def test_normalize_delete_reason_rejects_unknown_value():
    with pytest.raises(APIError) as error:
        _normalize_delete_reason("oops")

    assert error.value.status_code == 400
    assert error.value.code == "validation_error"


def test_reject_unknown_fields_reports_field_list():
    with pytest.raises(APIError) as error:
        _reject_unknown_fields({"user_id": 1, "extra": True}, {"user_id"})

    assert error.value.status_code == 400
    assert error.value.details == {"fields": ["extra"]}


def test_create_short_url_record_retries_generated_code_on_unique_violation(monkeypatch):
    fake_user = SimpleNamespace(id=1)
    created = []

    class FakeDatabaseCause(Exception):
        def __init__(self, pgcode):
            super().__init__(pgcode)
            self.pgcode = pgcode

    class FakeShortCodeField:
        def __eq__(self, other):
            return other

    class FakeSelectQuery:
        def where(self, candidate):
            self.candidate = candidate
            return self

        def exists(self):
            return False

    def fake_create(**kwargs):
        if not created:
            error = IntegrityError("duplicate")
            error.__cause__ = FakeDatabaseCause("23505")
            created.append("collision")
            raise error
        return SimpleNamespace(user=fake_user, short_code=kwargs["short_code"])

    fake_short_url_model = SimpleNamespace(
        short_code=FakeShortCodeField(),
        select=lambda: FakeSelectQuery(),
        create=fake_create,
    )

    monkeypatch.setattr("app.routes.urls.db", SimpleNamespace(atomic=lambda: nullcontext()))
    monkeypatch.setattr("app.routes.urls.ShortUrl", fake_short_url_model)
    monkeypatch.setattr("app.routes.urls._log_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "app.routes.urls._generate_short_code",
        lambda length=6: "Retry1" if len(created) == 0 else "Retry2",
    )

    short_url = _create_short_url_record(
        user=fake_user,
        original_url="https://example.com/retry",
        title=None,
        is_active=True,
    )

    assert short_url.short_code == "Retry2"


def test_create_short_url_record_skips_existing_generated_code_before_insert(monkeypatch):
    fake_user = SimpleNamespace(id=1)
    created_codes = []

    class FakeShortCodeField:
        def __eq__(self, other):
            return other

    class FakeSelectQuery:
        def __init__(self):
            self.candidate = None

        def where(self, candidate):
            self.candidate = candidate
            return self

        def exists(self):
            return self.candidate == "Retry1"

    def fake_create(**kwargs):
        created_codes.append(kwargs["short_code"])
        return SimpleNamespace(user=fake_user, short_code=kwargs["short_code"])

    fake_short_url_model = SimpleNamespace(
        short_code=FakeShortCodeField(),
        select=lambda: FakeSelectQuery(),
        create=fake_create,
    )

    generated_codes = iter(["Retry1", "Retry2"])

    monkeypatch.setattr("app.routes.urls.db", SimpleNamespace(atomic=lambda: nullcontext()))
    monkeypatch.setattr("app.routes.urls.ShortUrl", fake_short_url_model)
    monkeypatch.setattr("app.routes.urls._log_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "app.routes.urls._generate_short_code",
        lambda length=6: next(generated_codes),
    )

    short_url = _create_short_url_record(
        user=fake_user,
        original_url="https://example.com/retry",
        title=None,
        is_active=True,
    )

    assert short_url.short_code == "Retry2"
    assert created_codes == ["Retry2"]
