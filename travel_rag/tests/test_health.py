from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_reports_server_is_running() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.text == "server is running"


def test_health_check_reports_service_as_ready() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "travel-rag"}
