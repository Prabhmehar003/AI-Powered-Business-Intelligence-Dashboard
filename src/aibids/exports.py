"""Export processed marts to Tableau-ready CSVs and dashboard data assets."""

from __future__ import annotations

import json
from datetime import datetime

from .config import DASHBOARD_ASSETS_DIR, PROCESSED_DIR, TABLEAU_DIR
from .io_utils import as_float, as_int, read_csv, read_json, write_csv, write_json
from .qa import AnalyticsQA, sample_questions


def _number_or_text(key: str, value: str):
    text_fields = {
        "date",
        "order_date",
        "customer_id",
        "customer_segment",
        "product_id",
        "product_name",
        "category",
        "region",
        "channel",
        "order_status",
        "model",
        "event_id",
        "metric",
        "severity",
        "explanation",
        "action_hint",
        "last_order_date",
        "top_category",
        "value_band",
    }
    if key in text_fields:
        return value
    if value == "":
        return None
    try:
        if "." in value:
            return round(float(value), 4)
        return int(value)
    except ValueError:
        return value


def _typed_rows(rows: list[dict]) -> list[dict]:
    return [{key: _number_or_text(key, value) for key, value in row.items()} for row in rows]


def _sum(rows: list[dict], key: str) -> float:
    return sum(as_float(row[key]) for row in rows)


def _int_sum(rows: list[dict], key: str) -> int:
    return sum(as_int(row[key]) for row in rows)


def _summary(daily: list[dict], forecast: list[dict], anomalies: list[dict]) -> dict:
    revenue = _sum(daily, "net_revenue")
    profit = _sum(daily, "gross_profit")
    orders = _int_sum(daily, "orders")
    spend = _sum(daily, "marketing_spend")
    return {
        "dateStart": daily[0]["date"],
        "dateEnd": daily[-1]["date"],
        "revenue": round(revenue, 2),
        "grossProfit": round(profit, 2),
        "orders": orders,
        "units": _int_sum(daily, "units"),
        "avgOrderValue": round(revenue / orders if orders else 0, 2),
        "marginRate": round(profit / revenue if revenue else 0, 4),
        "marketingSpend": round(spend, 2),
        "roas": round(revenue / spend if spend else 0, 4),
        "forecastNext30": round(sum(as_float(row["forecast_revenue"]) for row in forecast[:30]), 2),
        "anomalyCount": len(anomalies),
        "highSeverityAnomalies": sum(1 for row in anomalies if row["severity"] == "High"),
    }


def export_dashboard_assets() -> dict[str, int]:
    daily = read_csv(PROCESSED_DIR / "daily_totals.csv")
    breakdown = read_csv(PROCESSED_DIR / "daily_breakdown.csv")
    forecast = read_csv(PROCESSED_DIR / "forecast_daily.csv")
    anomalies = read_csv(PROCESSED_DIR / "anomaly_events.csv")
    category_summary = read_csv(PROCESSED_DIR / "category_summary.csv")
    region_summary = read_csv(PROCESSED_DIR / "region_summary.csv")
    channel_summary = read_csv(PROCESSED_DIR / "channel_summary.csv")
    customer_segments = read_csv(PROCESSED_DIR / "customer_segments.csv")
    marketing_daily = read_csv(PROCESSED_DIR / "marketing_daily.csv")
    forecast_summary = read_json(PROCESSED_DIR / "forecast_summary.json")

    qa = AnalyticsQA()
    qa_payload = [{"question": question, **qa.answer(question)} for question in sample_questions()]

    payload = {
        "generatedAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "summary": _summary(daily, forecast, anomalies),
        "forecastSummary": forecast_summary,
        "daily": _typed_rows(daily),
        "breakdown": _typed_rows(breakdown),
        "forecast": _typed_rows(forecast),
        "anomalies": _typed_rows(anomalies),
        "categorySummary": _typed_rows(category_summary),
        "regionSummary": _typed_rows(region_summary),
        "channelSummary": _typed_rows(channel_summary),
        "marketingDaily": _typed_rows(marketing_daily),
        "customerSegments": _typed_rows(customer_segments[:250]),
        "qaSamples": qa_payload,
    }
    DASHBOARD_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    (DASHBOARD_ASSETS_DIR / "dashboard_data.js").write_text(
        "window.DASHBOARD_DATA = "
        + json.dumps(payload, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    write_json(PROCESSED_DIR / "dashboard_payload.json", payload)
    return {
        "daily": len(daily),
        "breakdown": len(breakdown),
        "forecast": len(forecast),
        "anomalies": len(anomalies),
    }


def export_tableau_pack() -> dict[str, int]:
    exports = {
        "tableau_sales_model.csv": read_csv(PROCESSED_DIR / "enriched_orders.csv"),
        "tableau_daily_metrics.csv": read_csv(PROCESSED_DIR / "daily_totals.csv"),
        "tableau_daily_breakdown.csv": read_csv(PROCESSED_DIR / "daily_breakdown.csv"),
        "tableau_forecast.csv": read_csv(PROCESSED_DIR / "forecast_daily.csv"),
        "tableau_anomaly_events.csv": read_csv(PROCESSED_DIR / "anomaly_events.csv"),
        "tableau_customer_segments.csv": read_csv(PROCESSED_DIR / "customer_segments.csv"),
    }
    counts = {}
    for filename, rows in exports.items():
        path = TABLEAU_DIR / filename
        write_csv(path, rows, list(rows[0].keys()) if rows else [])
        counts[filename] = len(rows)
    write_json(TABLEAU_DIR / "tableau_manifest.json", counts)
    return counts
