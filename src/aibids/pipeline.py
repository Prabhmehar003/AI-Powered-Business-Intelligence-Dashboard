"""End-to-end pipeline orchestration."""

from __future__ import annotations

from .anomalies import detect_anomalies
from .config import ensure_directories
from .data_generator import generate_demo_data
from .exports import export_dashboard_assets, export_tableau_pack
from .forecast import forecast_daily_revenue
from .ingest import ingest_raw_data


def run_pipeline(generate_raw: bool = True) -> dict:
    ensure_directories()
    result = {}
    if generate_raw:
        result["raw"] = generate_demo_data()
    result["processed"] = ingest_raw_data()
    result["forecast"] = forecast_daily_revenue()
    result["anomalies"] = detect_anomalies()
    result["dashboard"] = export_dashboard_assets()
    result["tableau"] = export_tableau_pack()
    return result
