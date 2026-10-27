import os

from locust import HttpUser, between, task


class LocalApiUser(HttpUser):
    host = os.getenv("PERF_TEST_HOST", "http://127.0.0.1:8000").rstrip("/")
    wait_time = between(1, 2)

    @task(3)
    def get_health(self) -> None:
        with self.client.get("/health", timeout=5, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Expected HTTP 200, got {response.status_code}")
                return
            try:
                payload = response.json()
            except ValueError:
                response.failure("Response body is not valid JSON")
                return
            if not isinstance(payload, dict) or payload.get("status") != "healthy":
                response.failure("Expected JSON object with status='healthy'")

    @task(2)
    def get_items(self) -> None:
        with self.client.get("/api/items", timeout=5, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Expected HTTP 200, got {response.status_code}")
                return
            try:
                payload = response.json()
            except ValueError:
                response.failure("Response body is not valid JSON")
                return
            valid_items = (
                isinstance(payload, list)
                and len(payload) == 3
                and all(
                    isinstance(item, dict)
                    and type(item.get("id")) is int
                    and isinstance(item.get("name"), str)
                    and bool(item.get("name", "").strip())
                    for item in payload
                )
            )
            if not valid_items:
                response.failure("Expected three items with integer ids and non-empty names")
