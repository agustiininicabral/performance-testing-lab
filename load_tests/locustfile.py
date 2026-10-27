from locust import HttpUser, between, task


class LocalApiUser(HttpUser):
    host = "http://127.0.0.1:8000"
    wait_time = between(1, 2)

    @task
    def get_health(self) -> None:
        with self.client.get(
            "/health",
            timeout=5,
            catch_response=True,
        ) as response:
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

    @task
    def get_items(self) -> None:
        with self.client.get(
            "/api/items",
            timeout=5,
            catch_response=True,
        ) as response:
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
                    and isinstance(item.get("id"), int)
                    and isinstance(item.get("name"), str)
                    for item in payload
                )
            )
            if not valid_items:
                response.failure(
                    "Expected a list of three items with integer id and string name"
                )
