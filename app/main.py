from fastapi import FastAPI

app = FastAPI(title="Performance Testing Lab API")

_ITEMS = [
    {"id": 1, "name": "Keyboard"},
    {"id": 2, "name": "Mouse"},
    {"id": 3, "name": "Monitor"},
]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/api/items")
def list_items() -> list[dict[str, int | str]]:
    return _ITEMS
