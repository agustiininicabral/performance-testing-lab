# Performance Testing Lab

A reproducible QA portfolio project combining a deterministic FastAPI service, API contract tests, Python quality gates, and bounded Locust load-smoke tests. The included CI workflow and Windows helper target loopback only; they do not load-test public services.

## What this demonstrates

- API status, response contract, deterministic data, unique IDs, and unknown-route checks.
- Ruff formatting and lint checks, pytest, and dependency consistency in CI.
- Locust checks response payloads rather than treating every HTTP 200 as success.
- A CI load-smoke job that starts the local API and runs two simulated users for 10 seconds.
- A Windows runner with a health pre-check, bounded parameters, and CSV output.

## Requirements and setup

Use Python 3.12. In PowerShell:

    python -m venv .venv
    ./.venv/Scripts/Activate.ps1
    python -m pip install -r requirements-dev.txt

Validate the environment:

    python -m pip check
    python -m ruff format --check app tests load_tests
    python -m ruff check app tests load_tests
    python -m pytest -q

## API

Start the API in one terminal. It binds only to the local loopback interface:

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

- GET /health returns a JSON object with status healthy.
- GET /api/items returns three deterministic sample items.

The unit tests use FastAPI TestClient in-process; they do not require a running server or Internet access.

## Local load test on Windows

Keep the API running, then open a second PowerShell terminal from the repository root. The default profile uses five simulated users for 30 seconds:

    ./scripts/run_load_test.ps1

Use a smaller smoke profile or a longer local run:

    ./scripts/run_load_test.ps1 -Users 2 -SpawnRate 1 -RunTime 10s
    ./scripts/run_load_test.ps1 -Users 10 -SpawnRate 2 -RunTime 2m

The helper limits users to 1–50, spawn rate to 1–10, and duration to 10 seconds, 30 seconds, 1, 2, or 5 minutes. It verifies the local health endpoint before starting Locust. CSV output is written under results/ and is intentionally excluded from Git.

For direct Locust usage:

    python -m locust -f load_tests/locustfile.py --headless --users 2 --spawn-rate 1 --run-time 30s

The scenario weights /health three times as heavily as /api/items and uses a 5-second request timeout. PERF_TEST_HOST can configure the target when running Locust directly. Only test systems you own or have explicit permission to test; the supplied PowerShell helper always uses 127.0.0.1.

## CI behavior

Every push and pull request runs two jobs:

1. Quality: install development dependencies, run pip check, Ruff format/lint, and pytest.
2. Load smoke: start the local API and run a bounded Locust scenario with two users for 10 seconds.

CI smoke tests confirm that the demo API and load scenario work together without recorded failures. They are not a benchmark, capacity estimate, production SLA, or performance guarantee.

## Interpreting results

Review total requests, failures, throughput, and median/p95/p99 latency in Locust output or generated CSV files. Compare runs only when the machine, Python version, and load profile are held constant. Repeat runs and document the environment. Do not treat a short localhost smoke test as a production baseline.

## Project structure

- app/main.py — deterministic FastAPI endpoints.
- tests/test_api.py — API contract and repeatability checks.
- load_tests/locustfile.py — validated Locust user behavior.
- scripts/run_load_test.ps1 — bounded Windows load-test runner.
- .github/workflows/tests.yml — quality gates and CI load smoke.
