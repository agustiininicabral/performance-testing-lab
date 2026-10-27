# Performance Testing Lab

A reproducible QA portfolio project combining a deterministic FastAPI service, bounded Locust load tests, and a report generator that detects performance regressions against a baseline. The supplied runner targets loopback only; do not load-test systems without authorization.

## What this demonstrates

- API contract checks for status, response shape, deterministic data, unique IDs, and unknown routes.
- Python dependency, formatting, lint, and pytest quality gates in GitHub Actions.
- A bounded CI load smoke test against a local demo API.
- Locust CSV analysis with median, p95/p99 latency, failure rate, and throughput.
- Configurable regression gates with machine-readable JSON and human-readable Markdown reports.
- Synthetic fixtures that demonstrate regression detection without depending on external services.

## Requirements and setup

Use Python 3.12. In PowerShell:

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip check
python -m ruff format --check app tests load_tests
python -m ruff check app tests load_tests
python -m pytest -q
```

## API and load test

Start the API in one terminal:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- `GET /health` returns `{"status":"healthy"}`.
- `GET /api/items` returns three deterministic sample items.

In a second terminal, run a bounded load test (default five users for 30 seconds):

```powershell
./scripts/run_load_test.ps1
# Short smoke profile
./scripts/run_load_test.ps1 -Users 2 -SpawnRate 1 -RunTime 10s
```

The helper constrains users to 1–50, spawn rate to 1–10, and duration to a short allowlist. It checks the local health endpoint first and writes Locust CSV files under `results/`.

## Generate and compare reports

Create a report from a Locust run:

```powershell
python -m app.performance_report --current results/performance_stats.csv --out reports/current
```

Compare a current run against a baseline:

```powershell
python -m app.performance_report --current results/current_stats.csv --baseline results/baseline_stats.csv --out reports/comparison
```

The tool writes JSON and Markdown reports. Exit code `0` means no configured regression was detected, `1` means a regression gate failed, and `2` indicates invalid input. Default gates: p95/p99 latency increase over 20%, failure-rate increase over 0.5 percentage points, or throughput drop over 15%. See [performance reporting documentation](docs/performance-reporting.md).

Run a synthetic comparison that should pass, without starting the API:

```powershell
python -m app.performance_report --current examples/current_stats_pass.csv --baseline examples/baseline_stats.csv --out reports/demo-pass
if ($LASTEXITCODE -ne 0) { throw "Expected the passing demo to exit 0; exit code was $LASTEXITCODE" }
```

Run the synthetic regression demonstration without starting the API:

```powershell
python -m app.performance_report --current examples/current_stats_regression.csv --baseline examples/baseline_stats.csv --out reports/demo
if ($LASTEXITCODE -ne 1) { throw "Expected a detected regression; exit code was $LASTEXITCODE" }
```

The sample data is synthetic and does not represent a measured benchmark.

## CI behavior

GitHub Actions runs dependency checks, Ruff, unit tests, and a two-user/10-second Locust smoke test against the local API. The report tests run as part of pytest. These checks validate the demo and test scenario; they are not production benchmarks, capacity estimates, or SLA guarantees.

## Project structure

- `app/main.py` — deterministic FastAPI endpoints.
- `app/performance_report.py` — Locust CSV parsing, regression comparison, JSON/Markdown report CLI.
- `tests/` — API and report parser/CLI/regression tests.
- `load_tests/locustfile.py` — Locust user behavior.
- `scripts/run_load_test.ps1` — bounded Windows load-test runner.
- `examples/` — synthetic CSVs for repeatable report demonstrations.
- `docs/performance-reporting.md` — thresholds, usage, and limitations.
- `.github/workflows/tests.yml` — quality gates and CI load smoke.

## Safety and interpretation

Only load-test systems you own or have explicit permission to test. Keep comparisons on equivalent environments and profiles. A short localhost run is useful for smoke testing and regression signals, not a production capacity forecast.
