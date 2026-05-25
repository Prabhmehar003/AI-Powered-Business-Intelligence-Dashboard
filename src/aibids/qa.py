"""Natural-language Q&A over the generated BI marts."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta

from .config import PROCESSED_DIR
from .io_utils import as_float, as_int, read_csv, read_json


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


class AnalyticsQA:
    """A compact deterministic analytics assistant for dashboard Q&A."""

    def __init__(self, processed_dir=PROCESSED_DIR):
        self.processed_dir = processed_dir
        self.daily = read_csv(processed_dir / "daily_totals.csv")
        self.breakdown = read_csv(processed_dir / "daily_breakdown.csv")
        self.categories = sorted({row["category"] for row in self.breakdown})
        self.regions = sorted({row["region"] for row in self.breakdown})
        self.channels = sorted({row["channel"] for row in self.breakdown})
        self.forecast = read_csv(processed_dir / "forecast_daily.csv")
        self.anomalies = read_csv(processed_dir / "anomaly_events.csv")
        self.forecast_summary = read_json(processed_dir / "forecast_summary.json")
        self.min_date = min(datetime.strptime(row["date"], "%Y-%m-%d").date() for row in self.daily)
        self.max_date = max(datetime.strptime(row["date"], "%Y-%m-%d").date() for row in self.daily)

    def answer(self, question: str) -> dict:
        normalized = question.strip().lower()
        if not normalized:
            return {
                "answer": "Ask a question about revenue, margin, orders, forecasts, channels, regions, or anomalies.",
                "supporting_data": [],
            }
        if any(token in normalized for token in ["forecast", "predict", "projection", "next"]):
            return self._answer_forecast(normalized)
        if any(token in normalized for token in ["anomaly", "anomalies", "outlier", "unusual", "spike", "drop"]):
            return self._answer_anomalies(normalized)
        if "top category" in normalized or ("category" in normalized and "best" in normalized):
            return self._answer_top_dimension("category", normalized)
        if "top region" in normalized or ("region" in normalized and "best" in normalized):
            return self._answer_top_dimension("region", normalized)
        if "top channel" in normalized or ("channel" in normalized and "best" in normalized):
            return self._answer_top_dimension("channel", normalized)
        if any(token in normalized for token in ["marketing", "roas", "spend", "cpc"]):
            return self._answer_marketing(normalized)
        if any(token in normalized for token in ["profit", "margin"]):
            return self._answer_profit(normalized)
        if any(token in normalized for token in ["orders", "aov", "average order"]):
            return self._answer_orders(normalized)
        return self._answer_revenue(normalized)

    def _date_bounds(self, normalized: str):
        match = re.search(r"(last|past)\s+(\d+)\s+day", normalized)
        if match:
            days = int(match.group(2))
            return self._clamp_bounds(self.max_date - timedelta(days=days - 1), self.max_date)
        year_match = re.search(r"\b(2024|2025|2026)\b", normalized)
        if year_match:
            year = int(year_match.group(1))
            return self._clamp_bounds(datetime(year, 1, 1).date(), datetime(year, 12, 31).date())
        if "this year" in normalized or "ytd" in normalized:
            return self._clamp_bounds(datetime(self.max_date.year, 1, 1).date(), self.max_date)
        if "last month" in normalized:
            first_this_month = self.max_date.replace(day=1)
            last_previous = first_this_month - timedelta(days=1)
            first_previous = last_previous.replace(day=1)
            return self._clamp_bounds(first_previous, last_previous)
        return None, None

    def _clamp_bounds(self, start, end):
        return max(start, self.min_date), min(end, self.max_date)

    def _dimension_filters(self, normalized: str) -> dict[str, str]:
        filters = {}
        for category in self.categories:
            if category.lower() in normalized:
                filters["category"] = category
        for region in self.regions:
            if region.lower() in normalized:
                filters["region"] = region
        for channel in self.channels:
            if channel.lower() in normalized:
                filters["channel"] = channel
        return filters

    def _filtered_breakdown(self, normalized: str) -> list[dict]:
        start, end = self._date_bounds(normalized)
        filters = self._dimension_filters(normalized)
        rows = []
        for row in self.breakdown:
            row_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
            if start and row_date < start:
                continue
            if end and row_date > end:
                continue
            if any(row[key] != value for key, value in filters.items()):
                continue
            rows.append(row)
        return rows

    def _filtered_daily(self, normalized: str) -> list[dict]:
        start, end = self._date_bounds(normalized)
        rows = []
        for row in self.daily:
            row_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
            if start and row_date < start:
                continue
            if end and row_date > end:
                continue
            rows.append(row)
        return rows

    def _range_label(self, normalized: str) -> str:
        start, end = self._date_bounds(normalized)
        if start and end:
            return f"{start.isoformat()} to {end.isoformat()}"
        return "the full available period"

    def _aggregate(self, rows: list[dict]) -> dict[str, float]:
        orders = sum(as_int(row["orders"]) for row in rows)
        revenue = sum(as_float(row["net_revenue"]) for row in rows)
        profit = sum(as_float(row["gross_profit"]) for row in rows)
        units = sum(as_int(row["units"]) for row in rows)
        return {
            "orders": orders,
            "revenue": revenue,
            "profit": profit,
            "units": units,
            "aov": revenue / orders if orders else 0.0,
            "margin_rate": profit / revenue if revenue else 0.0,
        }

    def _answer_revenue(self, normalized: str) -> dict:
        rows = self._filtered_breakdown(normalized)
        metrics = self._aggregate(rows)
        return {
            "answer": (
                f"Net revenue for {self._range_label(normalized)} is {_money(metrics['revenue'])} "
                f"from {metrics['orders']:,} orders, with AOV of {_money(metrics['aov'])}."
            ),
            "supporting_data": [metrics],
        }

    def _answer_profit(self, normalized: str) -> dict:
        rows = self._filtered_breakdown(normalized)
        metrics = self._aggregate(rows)
        return {
            "answer": (
                f"Gross profit for {self._range_label(normalized)} is {_money(metrics['profit'])}. "
                f"Margin rate is {_pct(metrics['margin_rate'])} on {_money(metrics['revenue'])} revenue."
            ),
            "supporting_data": [metrics],
        }

    def _answer_orders(self, normalized: str) -> dict:
        rows = self._filtered_breakdown(normalized)
        metrics = self._aggregate(rows)
        return {
            "answer": (
                f"{metrics['orders']:,} orders shipped {metrics['units']:,} units for "
                f"{self._range_label(normalized)}. Average order value is {_money(metrics['aov'])}."
            ),
            "supporting_data": [metrics],
        }

    def _answer_top_dimension(self, dimension: str, normalized: str) -> dict:
        rows = self._filtered_breakdown(normalized)
        grouped = defaultdict(lambda: {"net_revenue": 0.0, "orders": 0, "gross_profit": 0.0})
        for row in rows:
            bucket = grouped[row[dimension]]
            bucket["net_revenue"] += as_float(row["net_revenue"])
            bucket["orders"] += as_int(row["orders"])
            bucket["gross_profit"] += as_float(row["gross_profit"])
        ranked = sorted(grouped.items(), key=lambda item: item[1]["net_revenue"], reverse=True)
        if not ranked:
            return {"answer": "No matching rows were found.", "supporting_data": []}
        leader, metrics = ranked[0]
        return {
            "answer": (
                f"Top {dimension} for {self._range_label(normalized)} is {leader}, "
                f"with {_money(metrics['net_revenue'])} revenue across {metrics['orders']:,} orders."
            ),
            "supporting_data": [
                {"name": name, **values} for name, values in ranked[:5]
            ],
        }

    def _answer_marketing(self, normalized: str) -> dict:
        rows = self._filtered_daily(normalized)
        revenue = sum(as_float(row["net_revenue"]) for row in rows)
        spend = sum(as_float(row["marketing_spend"]) for row in rows)
        clicks = sum(as_int(row["clicks"]) for row in rows)
        impressions = sum(as_int(row["impressions"]) for row in rows)
        roas = revenue / spend if spend else 0.0
        cpc = spend / clicks if clicks else 0.0
        ctr = clicks / impressions if impressions else 0.0
        return {
            "answer": (
                f"Marketing spend for {self._range_label(normalized)} is {_money(spend)} with "
                f"{roas:.2f}x ROAS, {_money(cpc)} CPC, and {_pct(ctr)} CTR."
            ),
            "supporting_data": [
                {
                    "revenue": revenue,
                    "spend": spend,
                    "roas": roas,
                    "clicks": clicks,
                    "impressions": impressions,
                    "cpc": cpc,
                    "ctr": ctr,
                }
            ],
        }

    def _answer_forecast(self, normalized: str) -> dict:
        match = re.search(r"(\d+)\s+day", normalized)
        days = min(90, max(1, int(match.group(1)))) if match else 30
        selected = self.forecast[:days]
        total = sum(as_float(row["forecast_revenue"]) for row in selected)
        lower = sum(as_float(row["lower_bound"]) for row in selected)
        upper = sum(as_float(row["upper_bound"]) for row in selected)
        return {
            "answer": (
                f"Forecast revenue for the next {days} days is {_money(total)} "
                f"with an expected range of {_money(lower)} to {_money(upper)}. "
                f"Holdout MAPE is {_pct(float(self.forecast_summary['holdout_mape']))}."
            ),
            "supporting_data": selected[:7],
        }

    def _answer_anomalies(self, normalized: str) -> dict:
        start, end = self._date_bounds(normalized)
        rows = []
        for row in self.anomalies:
            row_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
            if start and row_date < start:
                continue
            if end and row_date > end:
                continue
            rows.append(row)
        rows.sort(key=lambda row: (row["date"], row["severity"]), reverse=True)
        if not rows:
            return {
                "answer": f"No anomalies were flagged for {self._range_label(normalized)}.",
                "supporting_data": [],
            }
        top = rows[0]
        return {
            "answer": (
                f"{len(rows)} anomalies were flagged for {self._range_label(normalized)}. "
                f"Most recent: {top['date']} {top['metric']} at {top['value']} vs expected {top['expected']} "
                f"({top['severity']} severity)."
            ),
            "supporting_data": rows[:5],
        }


def sample_questions() -> list[str]:
    return [
        "What was revenue in the last 30 days?",
        "Which category performed best in 2026?",
        "Show the next 30 day forecast",
        "Were there any anomalies in the last 90 days?",
        "What is our marketing ROAS this year?",
        "How much gross profit did Apparel generate?",
    ]
