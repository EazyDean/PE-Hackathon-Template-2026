import pytest


def test_create_user_returns_json_payload(client):
    response = client.post(
        "/api/users",
        json={"username": "new-user", "email": "new-user@example.com"},
    )
    payload = response.get_json()

    assert response.status_code == 201
    assert payload["username"] == "new-user"
    assert payload["email"] == "new-user@example.com"
    assert "id" in payload


def test_create_user_rejects_malformed_json(client):
    response = client.post(
        "/api/users",
        data='{"username": "bad"',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_json"


@pytest.mark.parametrize("raw_body", ['"just-a-string"', '["not", "an", "object"]', "null"])
def test_create_user_rejects_non_object_json(client, raw_body):
    response = client.post(
        "/api/users",
        data=raw_body,
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_json"


@pytest.mark.parametrize(
    ("payload", "expected_field"),
    [
        ({"email": "missing-username@example.com"}, "username"),
        ({"username": "missing-email"}, "email"),
    ],
)
def test_create_user_rejects_missing_required_fields(client, payload, expected_field):
    response = client.post("/api/users", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"
    assert expected_field in response.get_json()["message"]


@pytest.mark.parametrize(
    "payload",
    [
        {"username": 123, "email": "typed@example.com"},
        {"username": "typed", "email": 123},
        {"username": "typed", "email": "not-an-email"},
    ],
)
def test_create_user_rejects_wrong_types_and_invalid_email(client, payload):
    response = client.post("/api/users", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_create_user_rejects_duplicate_email(client):
    first = client.post(
        "/api/users",
        json={"username": "first", "email": "duplicate@example.com"},
    )
    second = client.post(
        "/api/users",
        json={"username": "second", "email": "duplicate@example.com"},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.get_json()["error"] == "conflict"


def test_get_user_rejects_nonexistent_user(client):
    response = client.get("/api/users/9999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_list_user_urls_rejects_nonexistent_user(client):
    response = client.get("/api/users/9999/urls")

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"
