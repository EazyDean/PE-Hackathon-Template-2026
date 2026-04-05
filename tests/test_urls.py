from app.models import ShortUrl, UrlEvent


def test_create_url_returns_json_payload(client, seed_user):
    response = client.post(
        "/api/urls",
        json={
            "user_id": seed_user.id,
            "original_url": "https://example.com/path",
            "title": "Example",
        },
    )
    payload = response.get_json()

    assert response.status_code == 201
    assert payload["user_id"] == seed_user.id
    assert payload["original_url"] == "https://example.com/path"
    assert payload["title"] == "Example"
    assert payload["is_active"] is True
    assert len(payload["short_code"]) == 6
    assert UrlEvent.select().where(UrlEvent.event_type == "created").count() == 1


def test_duplicate_creates_get_different_short_codes(client, seed_user):
    first = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/one"},
    )
    second = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/one"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.get_json()["short_code"] != second.get_json()["short_code"]


def test_create_url_retries_after_generated_short_code_collision(client, seed_user, monkeypatch):
    client.post(
        "/api/urls",
        json={
            "user_id": seed_user.id,
            "original_url": "https://example.com/existing",
            "short_code": "Retry1",
        },
    )

    generated_codes = iter(["Retry1", "Retry2"])
    monkeypatch.setattr(
        "app.routes.urls._generate_short_code",
        lambda length=6: next(generated_codes),
    )

    response = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/retry"},
    )

    assert response.status_code == 201
    assert response.get_json()["short_code"] == "Retry2"


def test_create_url_rejects_malformed_json(client):
    response = client.post(
        "/api/urls",
        data='{"user_id": 1',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_json"


def test_create_url_rejects_raw_string_json(client):
    response = client.post(
        "/api/urls",
        data='"just-a-string"',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_json"


def test_create_url_rejects_array_json(client):
    response = client.post(
        "/api/urls",
        data='["not", "an", "object"]',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_json"


def test_list_urls_rejects_nonexistent_user_id_query(client):
    response = client.get("/api/urls?user_id=9999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_create_url_rejects_invalid_user(client):
    response = client.post(
        "/api/urls",
        json={"user_id": 9999, "original_url": "https://example.com/missing"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_create_url_rejects_missing_required_fields(client):
    response = client.post("/api/urls", json={"user_id": 1})

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"
    assert "original_url" in response.get_json()["message"]


def test_create_url_rejects_unsupported_fields(client, seed_user):
    response = client.post(
        "/api/urls",
        json={
            "user_id": seed_user.id,
            "original_url": "https://example.com/extra",
            "unexpected": True,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["details"] == {"fields": ["unexpected"]}


def test_create_url_rejects_wrong_field_types(client, seed_user):
    response = client.post(
        "/api/urls",
        json={
            "user_id": str(seed_user.id),
            "original_url": "https://example.com/types",
            "is_active": "true",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_create_url_rejects_nonpositive_user_id(client):
    response = client.post(
        "/api/urls",
        json={"user_id": 0, "original_url": "https://example.com/zero"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_create_url_rejects_duplicate_manual_short_code(client, seed_user):
    first = client.post(
        "/api/urls",
        json={
            "user_id": seed_user.id,
            "original_url": "https://example.com/first",
            "short_code": "Alpha1",
        },
    )
    second = client.post(
        "/api/urls",
        json={
            "user_id": seed_user.id,
            "original_url": "https://example.com/second",
            "short_code": "Alpha1",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.get_json()["error"] == "conflict"


def test_get_url_rejects_nonexistent_numeric_id(client):
    response = client.get("/api/urls/9999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_get_url_by_numeric_id_alias(client, seed_user):
    create_response = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/by-id"},
    )
    url_id = create_response.get_json()["id"]

    response = client.get(f"/api/urls/{url_id}")

    assert response.status_code == 200
    assert response.get_json()["id"] == url_id


def test_get_unknown_route_returns_json_not_found(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_update_and_delete_flow(client, seed_user):
    create_response = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/start"},
    )
    short_code = create_response.get_json()["short_code"]

    patch_response = client.patch(
        f"/api/urls/{short_code}",
        json={"title": "Updated", "is_active": False},
    )
    delete_response = client.delete(f"/api/urls/{short_code}", json={"reason": "expired"})
    payload = delete_response.get_json()

    assert patch_response.status_code == 200
    assert patch_response.get_json()["title"] == "Updated"
    assert patch_response.get_json()["is_active"] is False
    assert delete_response.status_code == 200
    assert payload["short_code"] == short_code
    assert payload["is_active"] is False
    assert ShortUrl.get(ShortUrl.short_code == short_code).is_active is False


def test_update_rejects_unknown_fields(client, seed_user):
    create_response = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/update"},
    )
    short_code = create_response.get_json()["short_code"]

    response = client.patch(f"/api/urls/{short_code}", json={"user_id": seed_user.id})

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_update_rejects_malformed_json(client, seed_user):
    create_response = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/update-json"},
    )
    short_code = create_response.get_json()["short_code"]

    response = client.patch(
        f"/api/urls/{short_code}",
        data='{"title": "broken"',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_json"


def test_update_rejects_non_object_json_body(client, seed_user):
    create_response = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/update-array"},
    )
    short_code = create_response.get_json()["short_code"]

    response = client.patch(
        f"/api/urls/{short_code}",
        data='["not", "an", "object"]',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_json"


def test_update_rejects_nonexistent_url(client):
    response = client.patch("/api/urls/missing01", json={"title": "Updated"})

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_delete_rejects_null_json_body(client, seed_user):
    create_response = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/delete-null"},
    )
    short_code = create_response.get_json()["short_code"]

    response = client.delete(
        f"/api/urls/{short_code}",
        data="null",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_json"


def test_delete_rejects_nonexistent_url(client):
    response = client.delete("/api/urls/missing01", json={"reason": "expired"})

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_method_not_allowed_returns_json_shape(client):
    response = client.post("/health")

    assert response.status_code == 405
    assert response.get_json()["error"] == "method_not_allowed"
    assert "message" in response.get_json()


def test_server_error_returns_json_shape(client):
    response = client.get("/_test/error")

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"] == "internal_server_error"
    assert "message" in payload
