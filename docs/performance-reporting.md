# Performance reports and regression gates

The report command reads Locust's `*_stats.csv` export and produces a JSON report plus a Markdown summary. It uses the Locust `Aggregated` row when available; for a CSV without that row it uses the first data row. Do not combine endpoint-only rows and assume their percentiles can be mathematically aggregated: percentiles cannot be reconstructed by averaging endpoint percentiles.

## Generate a report

After a Locust run with `--csv results/run`, run:

```powershell
python -m app.performance_report --current results/run_stats.csv --out reports/current
```

Compare two equivalent runs:

```powershell
python -m app.performance_report --current results/current_stats.csv --baseline results/baseline_stats.csv --out reports/comparison
```

Exit codes: `0` means no configured regression was detected (or no baseline was supplied); `1` means one or more regression gates were exceeded; `2` means the input or configuration was invalid. Reports are written as `reports/comparison.json` and `reports/comparison.md`.

## Default gates

- p95 latency may not increase by more than 20%.
- p99 latency may not increase by more than 20%.
- Failure rate may not increase by more than 0.5 percentage points.
- Throughput may not drop by more than 15%.

Override a gate with `--max-p95-increase`, `--max-p99-increase`, `--max-failure-rate-increase`, or `--min-rps-drop`. Thresholds must be finite and non-negative. These are configurable example defaults, not universal SLOs. Tune them for a stable test environment and application requirements. A baseline with zero latency/RPS is not a useful performance baseline; zero-to-positive latency is treated as a regression.

## Synthetic demo

The committed files in `examples/` are small, synthetic Locust-format examples intended to demonstrate a passing comparison and a failing regression gate. They are not measured performance of a real service.

```powershell
python -m app.performance_report --current examples/current_stats_regression.csv --baseline examples/baseline_stats.csv --out reports/demo
if ($LASTEXITCODE -ne 1) { throw "Expected the synthetic regression demo to exit 1; got $LASTEXITCODE" }
```

Demonstrate a comparison that stays within the default thresholds:

```powershell
python -m app.performance_report --current examples/current_stats_pass.csv --baseline examples/baseline_stats.csv --out reports/demo-pass
if ($LASTEXITCODE -ne 0) { throw "Expected the passing demo to exit 0; got $LASTEXITCODE" }
```

## Comparability and limitations

Only compare runs with the same request mix, user count, spawn rate, duration, software version, hardware, and similar background load. The report is a simple gate over Locust's aggregate statistics, not a statistical significance test. Repeat runs and investigate variance before treating a small difference as a real regression. It does not estimate production capacity or replace monitoring and profiling.
