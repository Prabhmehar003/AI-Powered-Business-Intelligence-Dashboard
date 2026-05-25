"""Ingest raw CSV data and build analytics-ready marts."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from .config import PROCESSED_DIR, RAW_DIR
from .io_utils import as_float, as_int, read_csv, write_csv


ENRICHED_ORDER_FIELDS = [
    "order_id",
    "order_date",
    "customer_id",
    "customer_segment",
    "product_id",
    "product_name",
    "category",
    "region",
    "channel",
    "quantity",
    "unit_price",
    "unit_cost",
    "discount_pct",
    "discount_amount",
    "gross_revenue",
    "net_revenue",
    "shipping_cost",
    "gross_profit",
    "margin_rate",
    "order_status",
]

DAILY_BREAKDOWN_FIELDS = [
    "date",
    "category",
    "region",
    "channel",
    "orders",
    "customers",
    "units",
    "gross_revenue",
    "net_revenue",
    "gross_profit",
    "discount_amount",
    "shipping_cost",
    "avg_order_value",
    "margin_rate",
]

DAILY_TOTAL_FIELDS = [
    "date",
    "orders",
    "customers",
    "units",
    "gross_revenue",
    "net_revenue",
    "gross_profit",
    "discount_amount",
    "shipping_cost",
    "marketing_spend",
    "impressions",
    "clicks",
    "avg_order_value",
    "margin_rate",
    "roas",
    "cost_per_click",
    "click_through_rate",
]


def _required(rows: list[dict], required_columns: set[str], name: str) -> None:
    if not rows:
        raise ValueError(f"{name} is empty")
    missing = required_columns.difference(rows[0].keys())
    if missing:
        joined = ", ".join(sorted(missing))
        raise ValueError(f"{name} is missing required columns: {joined}")


def _money(value: float) -> str:
    return f"{value:.2f}"


def _rate(value: float) -> str:
    return f"{value:.4f}"


def _aggregate_orders(rows: list[dict], keys: list[str]) -> list[dict]:
    grouped: dict[tuple, dict] = {}
    for row in rows:
        key = tuple(row[column] for column in keys)
        bucket = grouped.setdefault(
            key,
            {
                **{column: row[column] for column in keys},
                "orders": 0,
                "customers_set": set(),
                "units": 0,
                "gross_revenue": 0.0,
                "net_revenue": 0.0,
                "gross_profit": 0.0,
                "discount_amount": 0.0,
                "shipping_cost": 0.0,
            },
        )
        bucket["orders"] += 1
        bucket["customers_set"].add(row["customer_id"])
        bucket["units"] += as_int(row["quantity"])
        bucket["gross_revenue"] += as_float(row["gross_revenue"])
        bucket["net_revenue"] += as_float(row["net_revenue"])
        bucket["gross_profit"] += as_float(row["gross_profit"])
        bucket["discount_amount"] += as_float(row["discount_amount"])
        bucket["shipping_cost"] += as_float(row["shipping_cost"])

    output = []
    for bucket in grouped.values():
        orders = bucket["orders"]
        revenue = bucket["net_revenue"]
        profit = bucket["gross_profit"]
        output.append(
            {
                **{column: bucket[column] for column in keys},
                "orders": orders,
                "customers": len(bucket["customers_set"]),
                "units": bucket["units"],
                "gross_revenue": _money(bucket["gross_revenue"]),
                "net_revenue": _money(revenue),
                "gross_profit": _money(profit),
                "discount_amount": _money(bucket["discount_amount"]),
                "shipping_cost": _money(bucket["shipping_cost"]),
                "avg_order_value": _money(revenue / orders if orders else 0),
                "margin_rate": _rate(profit / revenue if revenue else 0),
            }
        )
    return sorted(output, key=lambda row: tuple(row[column] for column in keys))


def _aggregate_marketing(marketing_rows: list[dict]) -> tuple[list[dict], dict[str, dict]]:
    by_channel = {}
    by_date = defaultdict(lambda: {"spend": 0.0, "impressions": 0, "clicks": 0})
    for row in marketing_rows:
        key = (row["date"], row["channel"])
        spend = as_float(row["spend"])
        impressions = as_int(row["impressions"])
        clicks = as_int(row["clicks"])
        by_channel[key] = {
            "date": row["date"],
            "channel": row["channel"],
            "spend": _money(spend),
            "impressions": impressions,
            "clicks": clicks,
        }
        bucket = by_date[row["date"]]
        bucket["spend"] += spend
        bucket["impressions"] += impressions
        bucket["clicks"] += clicks
    marketing_daily = [by_channel[key] for key in sorted(by_channel)]
    return marketing_daily, by_date


def _build_daily_totals(enriched_rows: list[dict], marketing_by_date: dict[str, dict]) -> list[dict]:
    daily = _aggregate_orders(enriched_rows, ["order_date"])
    output = []
    for row in daily:
        date_key = row.pop("order_date")
        spend = marketing_by_date[date_key]["spend"]
        impressions = marketing_by_date[date_key]["impressions"]
        clicks = marketing_by_date[date_key]["clicks"]
        revenue = as_float(row["net_revenue"])
        output.append(
            {
                "date": date_key,
                **row,
                "marketing_spend": _money(spend),
                "impressions": impressions,
                "clicks": clicks,
                "roas": _rate(revenue / spend if spend else 0),
                "cost_per_click": _money(spend / clicks if clicks else 0),
                "click_through_rate": _rate(clicks / impressions if impressions else 0),
            }
        )
    return sorted(output, key=lambda row: row["date"])


def _build_customer_segments(enriched_rows: list[dict]) -> list[dict]:
    latest_date = max(datetime.strptime(row["order_date"], "%Y-%m-%d").date() for row in enriched_rows)
    grouped = {}
    for row in enriched_rows:
        customer_id = row["customer_id"]
        bucket = grouped.setdefault(
            customer_id,
            {
                "customer_id": customer_id,
                "customer_segment": row["customer_segment"],
                "orders": 0,
                "net_revenue": 0.0,
                "gross_profit": 0.0,
                "last_order_date": row["order_date"],
                "categories": defaultdict(int),
            },
        )
        bucket["orders"] += 1
        bucket["net_revenue"] += as_float(row["net_revenue"])
        bucket["gross_profit"] += as_float(row["gross_profit"])
        bucket["last_order_date"] = max(bucket["last_order_date"], row["order_date"])
        bucket["categories"][row["category"]] += 1

    output = []
    for bucket in grouped.values():
        last_date = datetime.strptime(bucket["last_order_date"], "%Y-%m-%d").date()
        recency_days = (latest_date - last_date).days
        revenue = bucket["net_revenue"]
        orders = bucket["orders"]
        top_category = max(bucket["categories"], key=bucket["categories"].get)
        if revenue >= 1800 and orders >= 7:
            value_band = "Strategic"
        elif revenue >= 800:
            value_band = "Growth"
        elif recency_days <= 45:
            value_band = "Active"
        else:
            value_band = "Dormant"
        output.append(
            {
                "customer_id": bucket["customer_id"],
                "customer_segment": bucket["customer_segment"],
                "orders": orders,
                "net_revenue": _money(revenue),
                "gross_profit": _money(bucket["gross_profit"]),
                "avg_order_value": _money(revenue / orders if orders else 0),
                "last_order_date": bucket["last_order_date"],
                "recency_days": recency_days,
                "top_category": top_category,
                "value_band": value_band,
            }
        )
    return sorted(output, key=lambda row: (-as_float(row["net_revenue"]), row["customer_id"]))


def ingest_raw_data() -> dict[str, int]:
    """Read raw CSVs and write processed analytics tables."""
    orders = read_csv(RAW_DIR / "orders.csv")
    products = read_csv(RAW_DIR / "products.csv")
    customers = read_csv(RAW_DIR / "customers.csv")
    marketing = read_csv(RAW_DIR / "marketing_spend.csv")

    _required(
        orders,
        {
            "order_id",
            "order_date",
            "customer_id",
            "product_id",
            "region",
            "channel",
            "quantity",
            "unit_price",
            "discount_pct",
            "discount_amount",
            "gross_revenue",
            "shipping_cost",
            "order_status",
        },
        "orders.csv",
    )
    _required(products, {"product_id", "product_name", "category", "unit_cost"}, "products.csv")
    _required(customers, {"customer_id", "customer_segment"}, "customers.csv")

    products_by_id = {row["product_id"]: row for row in products}
    customers_by_id = {row["customer_id"]: row for row in customers}
    enriched = []
    for row in orders:
        product = products_by_id[row["product_id"]]
        customer = customers_by_id[row["customer_id"]]
        quantity = as_int(row["quantity"])
        unit_cost = as_float(product["unit_cost"])
        gross_revenue = as_float(row["gross_revenue"])
        discount_amount = as_float(row["discount_amount"])
        shipping_cost = as_float(row["shipping_cost"])
        merchandise_revenue = gross_revenue - discount_amount
        status = row["order_status"]
        if status == "Completed":
            net_revenue = merchandise_revenue
            gross_profit = net_revenue - (unit_cost * quantity) - shipping_cost
        elif status == "Returned":
            net_revenue = -0.85 * merchandise_revenue
            gross_profit = net_revenue - shipping_cost - (unit_cost * quantity * 0.15)
        else:
            net_revenue = 0.0
            gross_profit = -0.25 * shipping_cost

        enriched.append(
            {
                "order_id": row["order_id"],
                "order_date": row["order_date"],
                "customer_id": row["customer_id"],
                "customer_segment": customer["customer_segment"],
                "product_id": row["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "region": row["region"],
                "channel": row["channel"],
                "quantity": quantity,
                "unit_price": _money(as_float(row["unit_price"])),
                "unit_cost": _money(unit_cost),
                "discount_pct": _rate(as_float(row["discount_pct"])),
                "discount_amount": _money(discount_amount),
                "gross_revenue": _money(gross_revenue),
                "net_revenue": _money(net_revenue),
                "shipping_cost": _money(shipping_cost),
                "gross_profit": _money(gross_profit),
                "margin_rate": _rate(gross_profit / net_revenue if net_revenue else 0),
                "order_status": status,
            }
        )

    daily_breakdown = _aggregate_orders(enriched, ["order_date", "category", "region", "channel"])
    for row in daily_breakdown:
        row["date"] = row.pop("order_date")

    marketing_daily, marketing_by_date = _aggregate_marketing(marketing)
    daily_totals = _build_daily_totals(enriched, marketing_by_date)
    category_summary = _aggregate_orders(enriched, ["category"])
    region_summary = _aggregate_orders(enriched, ["region"])
    channel_summary = _aggregate_orders(enriched, ["channel"])
    customer_segments = _build_customer_segments(enriched)

    write_csv(PROCESSED_DIR / "enriched_orders.csv", enriched, ENRICHED_ORDER_FIELDS)
    write_csv(PROCESSED_DIR / "daily_breakdown.csv", daily_breakdown, DAILY_BREAKDOWN_FIELDS)
    write_csv(PROCESSED_DIR / "daily_totals.csv", daily_totals, DAILY_TOTAL_FIELDS)
    write_csv(
        PROCESSED_DIR / "marketing_daily.csv",
        marketing_daily,
        ["date", "channel", "spend", "impressions", "clicks"],
    )
    write_csv(
        PROCESSED_DIR / "category_summary.csv",
        category_summary,
        [field for field in DAILY_BREAKDOWN_FIELDS if field not in {"date", "region", "channel"}],
    )
    write_csv(
        PROCESSED_DIR / "region_summary.csv",
        region_summary,
        [field for field in DAILY_BREAKDOWN_FIELDS if field not in {"date", "category", "channel"}],
    )
    write_csv(
        PROCESSED_DIR / "channel_summary.csv",
        channel_summary,
        [field for field in DAILY_BREAKDOWN_FIELDS if field not in {"date", "category", "region"}],
    )
    write_csv(
        PROCESSED_DIR / "customer_segments.csv",
        customer_segments,
        [
            "customer_id",
            "customer_segment",
            "orders",
            "net_revenue",
            "gross_profit",
            "avg_order_value",
            "last_order_date",
            "recency_days",
            "top_category",
            "value_band",
        ],
    )

    return {
        "enriched_orders": len(enriched),
        "daily_breakdown": len(daily_breakdown),
        "daily_totals": len(daily_totals),
        "customer_segments": len(customer_segments),
    }
