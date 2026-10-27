import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.performance_report import (
    Metrics,
    build_report,
    compare_metrics,
    read_locust_stats,
    render_markdown,
)

FIELDS = [
    "Type",
    "Name",
    "Request Count",
    "Failure Count",
    "Median Response Time",
    "95%",
    "99%",
    "Requests/s",
]


def write_stats(
    path: Path,
    *,
    requests: int = 100,
    failures: int = 0,
    median: float = 10,
    p95: float = 20,
    p99: float = 30,
    rps: float = 10,
) -> Path:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "Type": "",
                "Name": "Aggregated",
                "Request Count": requests,
                "Failure Count": failures,
                "Median Response Time": median,
                "95%": p95,
                "99%": p99,
                "Requests/s": rps,
            }
        )
    return path


def test_reads_aggregated_locust_stats(tmp_path: Path) -> None:
    metrics = read_locust_stats(
        write_stats(tmp_path / "run_stats.csv", failures=2, p95=44)
    )
    assert metrics.requests == 100
    assert metrics.failures == 2
    assert metrics.failure_rate_pct == 2.0
    assert metrics.p95_ms == 44


def test_rejects_missing_or_empty_stats(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_locust_stats(tmp_path / "missing.csv")
    empty = tmp_path / "empty.csv"
    empty.write_text("Type,Name,Request Count\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no data rows"):
        read_locust_stats(empty)


def test_rejects_inconsistent_counts(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="inconsistent"):
        read_locust_stats(
            write_stats(tmp_path / "bad.csv", requests=2, failures=3)
        )


def test_detects_latency_failure_rate_and_throughput_regressions() -> None:
    baseline = Metrics(100, 0, 0, 10, 100, 200, 10)
    current = Metrics(100, 2, 2, 15, 130, 250, 8)
    results = compare_metrics(baseline, current)
    assert [item.metric for item in results if item.regressed] == [
        "p95_ms",
        "p99_ms",
        "failure_rate_pct",
        "requests_per_second",
    ]


def test_build_report_passes_within_thresholds() -> None:
    baseline = Metrics(100, 0, 0, 10, 100, 200, 10)
    current = Metrics(100, 0, 0, 10, 110, 210, 9)
    report = build_report(current, baseline)
    assert report["status"] == "PASS"
    assert "Baseline comparison" in render_markdown(report)


def test_cli_writes_json_and_markdown_and_exits_one_on_regression(
    tmp_path: Path,
) -> None:
    baseline = write_stats(
        tmp_path / "baseline_stats.csv", p95=100, p99=200, rps=10
    )
    current = write_stats(
        tmp_path / "current_stats.csv", p95=150, p99=300, rps=5
    )
    prefix = tmp_path / "reports" / "result"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.performance_report",
            "--current",
            str(current),
            "--baseline",
            str(baseline),
            "--out",
            str(prefix),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    payload = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
    assert payload["status"] == "REGRESSION"
    assert "REGRESSION" in prefix.with_suffix(".md").read_text(encoding="utf-8")


def test_cli_returns_two_for_bad_input(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.performance_report",
            "--current",
            str(tmp_path / "missing.csv"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "ERROR:" in result.stderr



def test_rejects_missing_required_columns(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.csv"
    malformed.write_text(
        "Name,Request Count\nAggregated,10\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="missing required columns"):
        read_locust_stats(malformed)


def test_rejects_fractional_request_counts(tmp_path: Path) -> None:
    malformed = tmp_path / "fractional.csv"
    malformed.write_text(
        (
            "Name,Request Count,Failure Count,Median Response Time,95%,99%,Requests/s\n"
            "Aggregated,10.5,0,10,20,30,5\n"
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="whole numbers"):
        read_locust_stats(malformed)


def test_rejects_negative_threshold_even_without_baseline() -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        build_report(
            Metrics(10, 0, 0, 5, 10, 20, 3), max_p95_increase_pct=-1
        )
