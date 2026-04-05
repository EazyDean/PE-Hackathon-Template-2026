import pytest

from app.routes.urls import APIError
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
