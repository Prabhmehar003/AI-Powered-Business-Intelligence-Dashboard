"""Detect anomalies in revenue, margin, and marketing efficiency."""

from __future__ import annotations

from statistics import median

from .config import PROCESSED_DIR
from .io_utils import as_float, read_csv, write_csv, write_json


ANOMALY_FIELDS = [
    "event_id",
    "date",
    "metric",
    "value",
    "expected",
    "deviation_pct",
    "severity",
    "explanation",
    "action_hint",
]


def _mad(values: list[float]) -> float:
    center = median(values)
    deviations = [abs(value - center) for value in values]
    return median(deviations) or 1.0


def _severity(score: float) -> str:
    if abs(score) >= 5.2:
        return "High"
    if abs(score) >= 3.6:
        return "Medium"
    return "Low"


def _event(
    event_number: int,
    date_value: str,
    metric: str,
    value: float,
    expected: float,
    score: float,
    explanation: str,
    action_hint: str,
) -> dict:
    deviation = (value - expected) / expected if expected else 0.0
    return {
        "event_id": f"A-{event_number:04d}",
        "date": date_value,
        "metric": metric,
        "value": f"{value:.2f}",
        "expected": f"{expected:.2f}",
        "deviation_pct": f"{deviation:.4f}",
        "severity": _severity(score),
        "explanation": explanation,
        "action_hint": action_hint,
    }


def _robust_score(value: float, window: list[float]) -> tuple[float, float]:
    expected = median(window)
    score = 0.6745 * (value - expected) / _mad(window)
    return expected, score


def detect_anomalies(window_size: int = 28) -> dict[str, int]:
    daily_rows = read_csv(PROCESSED_DIR / "daily_totals.csv")
    daily_rows.sort(key=lambda row: row["date"])
    events = []
    event_number = 1

    metrics = [
        (
            "net_revenue",
            "Revenue moved materially away from its recent baseline.",
            "Check stock availability, large campaigns, discounting, and order source mix.",
        ),
        (
            "margin_rate",
            "Gross margin rate moved materially away from its recent baseline.",
            "Inspect discount depth, return rate, shipping cost, and product mix.",
        ),
        (
            "roas",
            "Marketing efficiency moved materially away from its recent baseline.",
            "Review paid spend, traffic quality, landing-page conversion, and channel allocation.",
        ),
    ]

    for index in range(window_size, len(daily_rows)):
        current = daily_rows[index]
        history = daily_rows[index - window_size : index]
        for metric, explanation, action_hint in metrics:
            window = [as_float(row[metric]) for row in history]
            value = as_float(current[metric])
            expected, score = _robust_score(value, window)
            threshold = 3.2 if metric == "net_revenue" else 3.6
            if abs(score) >= threshold:
                events.append(
                    _event(
                        event_number,
                        current["date"],
                        metric,
                        value,
                        expected,
                        score,
                        explanation,
                        action_hint,
                    )
                )
                event_number += 1

    events.sort(
        key=lambda row: (
            {"High": 0, "Medium": 1, "Low": 2}[row["severity"]],
            row["date"],
            row["metric"],
        )
    )
    write_csv(PROCESSED_DIR / "anomaly_events.csv", events, ANOMALY_FIELDS)
    write_json(
        PROCESSED_DIR / "anomaly_summary.json",
        {
            "events": len(events),
            "high_severity": sum(1 for row in events if row["severity"] == "High"),
            "medium_severity": sum(1 for row in events if row["severity"] == "Medium"),
            "window_days": window_size,
        },
    )
    return {
        "events": len(events),
        "high_severity": sum(1 for row in events if row["severity"] == "High"),
        "medium_severity": sum(1 for row in events if row["severity"] == "Medium"),
    }
