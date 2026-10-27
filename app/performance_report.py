"""Analyze Locust stats CSV exports and compare them with a baseline."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class Metrics:
    requests: int
    failures: int
    failure_rate_pct: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    requests_per_second: float


@dataclass(frozen=True)
class Comparison:
    metric: str
    baseline: float
    current: float
    change_pct: float | None
    limit_pct: float
    regressed: bool


def _number(row: dict[str, str], *names: str, default: float = 0.0) -> float:
    for name in names:
        raw = row.get(name)
        if raw is not None and raw.strip():
            try:
                value = float(raw.replace(",", ""))
            except ValueError as exc:
                raise ValueError(f"Invalid numeric value for {name!r}: {raw!r}") from exc
            if not math.isfinite(value):
                raise ValueError(f"Non-finite numeric value for {name!r}: {raw!r}")
            return value
    return default


def read_locust_stats(path: str | Path) -> Metrics:
    """Read Locust *_stats.csv, preferring its Aggregated row when available."""
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Stats CSV not found: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"Stats CSV has no header: {csv_path}")
        required_groups = (
            ("Request Count", "Requests"),
            ("Failure Count", "Failures"),
            ("Median Response Time", "Median Response Time (ms)"),
            ("95%", "95%ile"),
            ("99%", "99%ile"),
            ("Requests/s", "Current RPS"),
        )
        missing = [
            " / ".join(group)
            for group in required_groups
            if not any(name in reader.fieldnames for name in group)
        ]
        if missing:
            raise ValueError(
                f"Stats CSV is missing required columns: {', '.join(missing)}"
            )
        rows = list(reader)
    if not rows:
        raise ValueError(f"Stats CSV has no data rows: {csv_path}")

    aggregate = next(
        (
            row
            for row in rows
            if row.get("Name", "").strip().lower() in {"aggregated", "total"}
        ),
        None,
    )
    row = aggregate or rows[0]
    requests_value = _number(row, "Request Count", "Requests")
    failures_value = _number(row, "Failure Count", "Failures")
    if not requests_value.is_integer() or not failures_value.is_integer():
        raise ValueError("Request and failure counts must be whole numbers.")
    requests = int(requests_value)
    failures = int(failures_value)
    if requests < 0 or failures < 0 or failures > requests:
        raise ValueError("Request and failure counts are inconsistent.")
    failure_rate = failures / requests * 100 if requests else 0.0
    return Metrics(
        requests=requests,
        failures=failures,
        failure_rate_pct=round(failure_rate, 4),
        median_ms=_number(row, "Median Response Time", "Median Response Time (ms)"),
        p95_ms=_number(row, "95%", "95%ile"),
        p99_ms=_number(row, "99%", "99%ile"),
        requests_per_second=_number(row, "Requests/s", "Current RPS"),
    )


def compare_metrics(
    baseline: Metrics,
    current: Metrics,
    *,
    max_p95_increase_pct: float = 20.0,
    max_p99_increase_pct: float = 20.0,
    max_failure_rate_increase_pct: float = 0.5,
    min_rps_drop_pct: float = 15.0,
) -> list[Comparison]:
    """Return regressions; failure-rate changes use percentage points."""
    limits = (
        max_p95_increase_pct,
        max_p99_increase_pct,
        max_failure_rate_increase_pct,
        min_rps_drop_pct,
    )
    if any(limit < 0 or not math.isfinite(limit) for limit in limits):
        raise ValueError("Regression thresholds must be finite and non-negative.")

    def increase(metric: str, before: float, after: float, limit: float) -> Comparison:
        change = (
            (after - before) / before * 100
            if before > 0
            else (0.0 if after == 0 else None)
        )
        regressed = after > before * (1 + limit / 100) if before > 0 else after > 0
        return Comparison(metric, before, after, change, limit, regressed)

    p95 = increase("p95_ms", baseline.p95_ms, current.p95_ms, max_p95_increase_pct)
    p99 = increase("p99_ms", baseline.p99_ms, current.p99_ms, max_p99_increase_pct)
    failure_delta = current.failure_rate_pct - baseline.failure_rate_pct
    failures = Comparison(
        "failure_rate_pct",
        baseline.failure_rate_pct,
        current.failure_rate_pct,
        round(failure_delta, 4),
        max_failure_rate_increase_pct,
        failure_delta > max_failure_rate_increase_pct,
    )
    rps_change = (
        (current.requests_per_second - baseline.requests_per_second)
        / baseline.requests_per_second
        * 100
        if baseline.requests_per_second > 0
        else None
    )
    throughput = Comparison(
        "requests_per_second",
        baseline.requests_per_second,
        current.requests_per_second,
        round(rps_change, 4) if rps_change is not None else None,
        min_rps_drop_pct,
        baseline.requests_per_second > 0
        and current.requests_per_second
        < baseline.requests_per_second * (1 - min_rps_drop_pct / 100),
    )
    return [p95, p99, failures, throughput]


def build_report(
    current: Metrics,
    baseline: Metrics | None = None,
    *,
    max_p95_increase_pct: float = 20.0,
    max_p99_increase_pct: float = 20.0,
    max_failure_rate_increase_pct: float = 0.5,
    min_rps_drop_pct: float = 15.0,
) -> dict[str, object]:
    limits = (
        max_p95_increase_pct,
        max_p99_increase_pct,
        max_failure_rate_increase_pct,
        min_rps_drop_pct,
    )
    if any(limit < 0 or not math.isfinite(limit) for limit in limits):
        raise ValueError("Regression thresholds must be finite and non-negative.")
    comparisons = (
        compare_metrics(
            baseline,
            current,
            max_p95_increase_pct=max_p95_increase_pct,
            max_p99_increase_pct=max_p99_increase_pct,
            max_failure_rate_increase_pct=max_failure_rate_increase_pct,
            min_rps_drop_pct=min_rps_drop_pct,
        )
        if baseline
        else []
    )
    return {
        "status": "REGRESSION" if any(item.regressed for item in comparisons) else "PASS",
        "current": asdict(current),
        "baseline": asdict(baseline) if baseline else None,
        "comparisons": [asdict(item) for item in comparisons],
        "thresholds": {
            "max_p95_increase_pct": max_p95_increase_pct,
            "max_p99_increase_pct": max_p99_increase_pct,
            "max_failure_rate_increase_percentage_points": max_failure_rate_increase_pct,
            "min_rps_drop_pct": min_rps_drop_pct,
        },
        "notes": [
            "Compare runs only when hardware, software, test duration, and load profile are equivalent.",
            "A short localhost run is a regression signal, not a production capacity benchmark.",
        ],
    }


def render_markdown(report: dict[str, object]) -> str:
    current = report["current"]
    assert isinstance(current, dict)
    lines = [
        "# Performance test report",
        "",
        f"**Status:** {report['status']}",
        "",
        "## Current run",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Requests | {current['requests']} |",
        f"| Failures | {current['failures']} |",
        f"| Failure rate | {current['failure_rate_pct']:.4f}% |",
        f"| Median latency | {current['median_ms']:.2f} ms |",
        f"| p95 latency | {current['p95_ms']:.2f} ms |",
        f"| p99 latency | {current['p99_ms']:.2f} ms |",
        f"| Throughput | {current['requests_per_second']:.2f} requests/s |",
    ]
    comparisons = report["comparisons"]
    if comparisons:
        lines += [
            "",
            "## Baseline comparison",
            "",
            "| Metric | Baseline | Current | Change | Threshold | Result |",
            "|---|---:|---:|---:|---:|---|",
        ]
        for item in comparisons:
            change = item["change_pct"]
            change_text = "n/a" if change is None else f"{change:+.2f}%"
            threshold = (
                f"+{item['limit_pct']:.2f} pp"
                if item["metric"] == "failure_rate_pct"
                else f"{item['limit_pct']:.2f}%"
            )
            result = "REGRESSION" if item["regressed"] else "PASS"
            lines.append(
                f"| {item['metric']} | {item['baseline']:.2f} | "
                f"{item['current']:.2f} | {change_text} | {threshold} | {result} |"
            )
    lines += ["", "## Interpretation", ""]
    lines += [f"- {note}" for note in report["notes"]]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", required=True, help="Current Locust *_stats.csv file")
    parser.add_argument("--baseline", help="Optional Locust *_stats.csv baseline file")
    parser.add_argument("--out", default="reports/performance-report", help="Output path prefix")
    parser.add_argument("--max-p95-increase", type=float, default=20.0)
    parser.add_argument("--max-p99-increase", type=float, default=20.0)
    parser.add_argument("--max-failure-rate-increase", type=float, default=0.5)
    parser.add_argument("--min-rps-drop", type=float, default=15.0)
    args = parser.parse_args(argv)
    try:
        current = read_locust_stats(args.current)
        baseline = read_locust_stats(args.baseline) if args.baseline else None
        report = build_report(
            current,
            baseline,
            max_p95_increase_pct=args.max_p95_increase,
            max_p99_increase_pct=args.max_p99_increase,
            max_failure_rate_increase_pct=args.max_failure_rate_increase,
            min_rps_drop_pct=args.min_rps_drop,
        )
        prefix = Path(args.out)
        prefix.parent.mkdir(parents=True, exist_ok=True)
        prefix.with_suffix(".json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        prefix.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")
        print(f"{report['status']}: reports written to {prefix}.json and {prefix}.md")
        return 1 if report["status"] == "REGRESSION" else 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
