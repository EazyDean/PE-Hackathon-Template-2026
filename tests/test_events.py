def test_event_listing_includes_created_and_visited_events(client, seed_user):
    create_response = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/events"},
    )
    short_code = create_response.get_json()["short_code"]

    client.get(f"/{short_code}", follow_redirects=False)
    response = client.get(f"/api/urls/{short_code}/events")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["short_code"] == short_code
    assert payload["count"] == 2
    assert [item["event_type"] for item in payload["items"]] == ["created", "visited"]


def test_list_events_rejects_invalid_url_id_query(client):
    response = client.get("/api/events?url_id=0")

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_query"


def test_list_events_rejects_nonexistent_url_id_query(client):
    response = client.get("/api/events?url_id=9999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_delete_inactive_url_is_idempotent_for_deleted_event_logging(client, seed_user):
    create_response = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/delete-once"},
    )
    short_code = create_response.get_json()["short_code"]

    first_delete = client.delete(f"/api/urls/{short_code}", json={"reason": "expired"})
    second_delete = client.delete(f"/api/urls/{short_code}", json={"reason": "expired"})

    assert first_delete.status_code == 200
    assert second_delete.status_code == 200
    assert client.get(f"/api/urls/{short_code}/events").get_json()["count"] == 2
