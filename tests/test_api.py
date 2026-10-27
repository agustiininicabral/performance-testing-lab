from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_healthy_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_items_returns_fixed_deterministic_list() -> None:
    response = client.get("/api/items")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "Keyboard"},
        {"id": 2, "name": "Mouse"},
        {"id": 3, "name": "Monitor"},
    ]
