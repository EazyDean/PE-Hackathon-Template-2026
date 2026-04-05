from unittest.mock import patch


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_health_response_includes_request_id_header(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_ready_endpoint_reports_database_up(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_ready_endpoint_reports_database_down(client):
    with patch("app.check_database_connection", return_value=False):
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.get_json() == {"status": "degraded", "database": "unavailable"}
