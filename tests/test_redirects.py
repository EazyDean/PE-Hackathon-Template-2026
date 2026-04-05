from app.models import UrlEvent


def test_redirect_logs_visited_event(client, seed_user):
    create_response = client.post(
        "/api/urls",
        json={"user_id": seed_user.id, "original_url": "https://example.com/redirect"},
    )
    short_code = create_response.get_json()["short_code"]

    response = client.get(f"/{short_code}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com/redirect"
    assert UrlEvent.select().where(UrlEvent.event_type == "visited").count() == 1


def test_redirect_unknown_short_code_returns_json_not_found(client):
    response = client.get("/missing01", follow_redirects=False)

    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"
    assert UrlEvent.select().where(UrlEvent.event_type == "visited").count() == 0


def test_inactive_redirect_returns_json_error(client, seed_user):
    create_response = client.post(
        "/api/urls",
        json={
            "user_id": seed_user.id,
            "original_url": "https://example.com/inactive",
            "is_active": False,
        },
    )
    short_code = create_response.get_json()["short_code"]

    response = client.get(f"/{short_code}", follow_redirects=False)

    assert response.status_code == 410
    assert response.get_json()["error"] == "inactive"


def test_inactive_redirect_does_not_log_visited_event(client, seed_user):
    create_response = client.post(
        "/api/urls",
        json={
            "user_id": seed_user.id,
            "original_url": "https://example.com/inactive-no-log",
            "is_active": False,
        },
    )
    short_code = create_response.get_json()["short_code"]

    client.get(f"/{short_code}", follow_redirects=False)

    assert UrlEvent.select().where(UrlEvent.event_type == "visited").count() == 0
