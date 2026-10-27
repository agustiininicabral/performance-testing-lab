# Performance Testing Lab

A small QA portfolio project with a deterministic local API and a Locust scenario for measuring its read-only endpoints. Load tests target loopback by default and do not depend on public services.

## Requirements

- Python 3.12 (validated locally with Python 3.12.10)
- Direct dependencies pinned in `requirements.txt`

Create an isolated environment and install the project dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

The requirements file pins direct packages; pip resolves their transitive dependencies during installation.

## API

Start the API in one terminal. It binds only to the local loopback interface:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- `GET http://127.0.0.1:8000/health` returns `{"status":"healthy"}`.
- `GET http://127.0.0.1:8000/api/items` returns a fixed list of three items.

## Unit tests

The pytest tests use FastAPI's in-process `TestClient`. They do not start a server or access the Internet.

```powershell
python -m pip check
python -m ruff format --check app tests load_tests
python -m ruff check app tests load_tests
python -m pytest -q
```

GitHub Actions runs dependency consistency, Ruff formatting/lint checks, and these unit tests on pushes and pull requests. CI does not run load tests. `requirements-dev.txt` includes the runtime dependencies and a pinned Ruff version; `pyproject.toml` defines the lint rules.

## Local load test

With the API running, use a second terminal for a short, controlled Locust run:

```powershell
python -m locust -f load_tests/locustfile.py --headless --users 2 --spawn-rate 1 --run-time 30s --stop-timeout 5
```

The scenario targets `http://127.0.0.1:8000`, waits 1–2 seconds between tasks, and applies a 5-second timeout to each request. It checks HTTP 200 and basic JSON content for both endpoints. Invalid responses and request errors are recorded as Locust failures.

### Example local smoke-run measurements

A brief 30-second run against localhost with two simulated users recorded the following sample:

| Endpoint | Requests | Failures | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `/api/items` | 20 | 0 | 2 ms | 3 ms | 3 ms |
| `/health` | 21 | 0 | 2 ms | 9 ms | 11 ms |
| Aggregate | 41 | 0 | 2 ms | 3 ms | 11 ms |

Locust reports these percentiles as approximations. This is one short localhost smoke run; its results vary with the machine and environment. They do not establish maximum capacity, production performance, or a service-level guarantee.
