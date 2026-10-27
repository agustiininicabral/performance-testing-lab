# Performance Testing Lab

A reproducible QA portfolio project combining a deterministic FastAPI service, contract-oriented unit tests, static linting, and bounded Locust smoke tests. The default target is loopback only; no public service is load-tested by the included workflow or PowerShell helper.

## What this demonstrates

- API checks for status codes, response contracts, deterministic data, unique identifiers, and unknown routes.
- Python quality gates with Ruff, pytest, and pip dependency consistency checks.
- A Locust scenario that validates response bodies instead of counting every HTTP 200 as success.
- A CI load-smoke job that starts the local API and runs two simulated users for 10 seconds.
- A Windows helper with bounded parameters and a pre-flight health check.

## Requirements and setup

Use Python 3.12. In PowerShell:

    python -m venv .venv
    .\\.venv\\Scripts\\Activate.ps1
    python -m pip install -r requirements.txt

Validate the environment and run the checks:

    python -m pip check
    python -m ruff check app tests load_tests
    python -m pytest -q

## API

Start the API in one terminal. It binds to the local loopback interface:

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

- GET /health returns {"status":"healthy"}.
- GET /api/items returns three deterministic sample items.

The test suite uses FastAPI TestClient in-process and does not need a running server or Internet access.

## Load testing on Windows

Keep the API running, then open a second PowerShell terminal from the repository root. The default run is five users for 30 seconds:

    .\\scripts\\run_load_test.ps1

Choose a bounded profile with parameters:

    .\\scripts\\run_load_test.ps1 -Users 2 -SpawnRate 1 -RunTime 10s
    .\\scripts\\run_load_test.ps1 -Users 10 -SpawnRate 2 -RunTime 2m

The helper restricts the user count to 1–50, spawn rate to 1–10, and duration to a small set of supported values. It checks the local health endpoint before starting Locust. CSV output is written with the results/performance prefix; these generated files are intentionally not committed.

For direct Locust usage:

    python -m locust -f load_tests/locustfile.py --headless --users 2 --spawn-rate 1 --run-time 30s

The scenario weights /health three times as heavily as /api/items, uses a 5-second request timeout, and validates the response payloads. PERF_TEST_HOST can configure the host when running Locust directly; use only systems you own or have explicit permission to test. The included PowerShell helper always targets 127.0.0.1.

## CI behavior

Every push and pull request runs two jobs:

1. Quality: install pinned direct dependencies, run pip check, Ruff, and pytest.
2. Load smoke: start the local API and run a short, bounded Locust test with two users.

CI smoke results only confirm that the scenario can exercise the demo service without recorded failures. They are not a benchmark, capacity estimate, production SLA, or performance guarantee.

## Reading results responsibly

Review total requests, failures, throughput, and median/p95/p99 latency from the Locust output or CSV files. Run comparisons on the same machine with the same Python version and profile. Repeat runs and report the environment and configuration. Do not compare one short localhost run with production measurements or treat sample numbers as universal baselines.

## Project structure

- app/main.py — deterministic FastAPI endpoints.
- tests/test_api.py — API contract and repeatability checks.
- load_tests/locustfile.py — validated Locust user behavior.
- scripts/run_load_test.ps1 — bounded Windows load-test runner.
- .github/workflows/tests.yml — quality gates and CI load smoke.
