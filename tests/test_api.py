from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
EXPECTED_ITEMS = [
    {"id": 1, "name": "Keyboard"},
    {"id": 2, "name": "Mouse"},
    {"id": 3, "name": "Monitor"},
]


def test_health_returns_healthy_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_items_returns_fixed_deterministic_list() -> None:
    response = client.get("/api/items")

    assert response.status_code == 200
    assert response.json() == EXPECTED_ITEMS


def test_items_have_unique_positive_integer_ids_and_nonempty_names() -> None:
    response = client.get("/api/items")
    items = response.json()

    assert all(type(item["id"]) is int and item["id"] > 0 for item in items)
    assert len({item["id"] for item in items}) == len(items)
    assert all(isinstance(item["name"], str) and item["name"].strip() for item in items)


def test_read_endpoints_are_repeatable() -> None:
    first_health = client.get("/health")
    second_health = client.get("/health")
    first_items = client.get("/api/items")
    second_items = client.get("/api/items")

    assert first_health.json() == second_health.json()
    assert first_items.json() == second_items.json() == EXPECTED_ITEMS


def test_unknown_route_returns_not_found() -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
