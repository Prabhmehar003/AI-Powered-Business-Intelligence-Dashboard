"""Generate a realistic synthetic e-commerce dataset for the BI demo."""

from __future__ import annotations

import csv
import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from .config import CHANNELS, DATA_END, DATA_START, RANDOM_SEED, RAW_DIR, REGIONS, SEGMENTS


PRODUCTS = [
    ("P-1001", "Noise-canceling Headphones", "Electronics", 149.0, 82.0),
    ("P-1002", "Smart Fitness Watch", "Electronics", 219.0, 126.0),
    ("P-1003", "USB-C Docking Station", "Electronics", 129.0, 73.0),
    ("P-1004", "Portable Projector", "Electronics", 349.0, 218.0),
    ("P-2001", "Organic Face Serum", "Beauty", 42.0, 14.0),
    ("P-2002", "Hydrating Shampoo Set", "Beauty", 28.0, 9.0),
    ("P-2003", "LED Vanity Mirror", "Beauty", 76.0, 34.0),
    ("P-3001", "Ergonomic Office Chair", "Home", 289.0, 156.0),
    ("P-3002", "Weighted Blanket", "Home", 88.0, 39.0),
    ("P-3003", "Air Purifier", "Home", 199.0, 112.0),
    ("P-3004", "Standing Desk Mat", "Home", 49.0, 17.0),
    ("P-4001", "Trail Running Shoes", "Sports", 132.0, 61.0),
    ("P-4002", "Adjustable Dumbbells", "Sports", 399.0, 241.0),
    ("P-4003", "Yoga Starter Kit", "Sports", 54.0, 19.0),
    ("P-5001", "Merino Travel Hoodie", "Apparel", 118.0, 47.0),
    ("P-5002", "All-weather Jacket", "Apparel", 179.0, 83.0),
    ("P-5003", "Compression Socks Pack", "Apparel", 24.0, 6.0),
    ("P-6001", "Data Science Handbook", "Books", 38.0, 12.0),
    ("P-6002", "Leadership Field Guide", "Books", 31.0, 8.0),
    ("P-6003", "Cookbook Collection", "Books", 45.0, 15.0),
]


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _date_range(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _weighted_choice(items: list[str], weights: list[float]) -> str:
    return random.choices(items, weights=weights, k=1)[0]


def _daily_order_count(day: date, start: date) -> int:
    days = (day - start).days
    trend = 48 + days * 0.055
    weekday_factor = [1.02, 1.05, 1.08, 1.0, 1.13, 1.28, 0.76][day.weekday()]
    month_factor = {
        1: 0.9,
        2: 0.94,
        3: 1.0,
        4: 1.02,
        5: 1.08,
        6: 1.12,
        7: 1.06,
        8: 1.04,
        9: 1.09,
        10: 1.18,
        11: 1.52,
        12: 1.44,
    }[day.month]
    seasonal = 1 + 0.13 * math.sin(2 * math.pi * day.timetuple().tm_yday / 365.25)
    promo_factor = 1.0
    if day.month == 11 and day.weekday() == 4 and 22 <= day.day <= 29:
        promo_factor = 2.7
    if day.month == 12 and day.day in {9, 10, 16, 17}:
        promo_factor = 1.7
    if day == date(2025, 7, 14):
        promo_factor = 0.38
    if day == date(2026, 2, 17):
        promo_factor = 2.1
    expected = trend * weekday_factor * month_factor * seasonal * promo_factor
    return max(8, int(random.gauss(expected, max(4.0, expected * 0.08))))


def _product_weights(day: date) -> list[float]:
    weights = []
    for _, _, category, _, _ in PRODUCTS:
        base = {
            "Electronics": 1.22,
            "Beauty": 1.0,
            "Home": 1.05,
            "Sports": 0.9,
            "Apparel": 1.0,
            "Books": 0.74,
        }[category]
        if category == "Sports" and day.month in {1, 5, 6, 7}:
            base *= 1.35
        if category == "Home" and day.month in {9, 10, 11}:
            base *= 1.25
        if category == "Electronics" and day.month in {11, 12}:
            base *= 1.45
        if category == "Beauty" and day.month in {2, 5, 12}:
            base *= 1.22
        weights.append(base)
    return weights


def generate_products() -> list[dict]:
    rows = []
    for product_id, product_name, category, price, cost in PRODUCTS:
        rows.append(
            {
                "product_id": product_id,
                "product_name": product_name,
                "category": category,
                "list_price": f"{price:.2f}",
                "unit_cost": f"{cost:.2f}",
            }
        )
    _write_csv(
        RAW_DIR / "products.csv",
        rows,
        ["product_id", "product_name", "category", "list_price", "unit_cost"],
    )
    return rows


def generate_customers(count: int = 2800) -> list[dict]:
    start = _parse_date(DATA_START) - timedelta(days=420)
    end = _parse_date(DATA_END)
    rows = []
    for index in range(1, count + 1):
        signup_offset = random.randint(0, (end - start).days)
        signup_date = start + timedelta(days=signup_offset)
        segment = _weighted_choice(SEGMENTS, [0.42, 0.46, 0.12])
        region = _weighted_choice(REGIONS, [0.25, 0.18, 0.2, 0.22, 0.15])
        channel = _weighted_choice(CHANNELS, [0.28, 0.18, 0.16, 0.16, 0.13, 0.09])
        rows.append(
            {
                "customer_id": f"C-{index:05d}",
                "signup_date": signup_date.isoformat(),
                "home_region": region,
                "customer_segment": segment,
                "acquisition_channel": channel,
            }
        )
    _write_csv(
        RAW_DIR / "customers.csv",
        rows,
        [
            "customer_id",
            "signup_date",
            "home_region",
            "customer_segment",
            "acquisition_channel",
        ],
    )
    return rows


def generate_marketing_spend() -> list[dict]:
    rows = []
    channel_base = {
        "Organic Search": 320,
        "Paid Search": 1320,
        "Email": 240,
        "Social": 880,
        "Marketplace": 710,
        "Direct": 120,
    }
    start = _parse_date(DATA_START)
    end = _parse_date(DATA_END)
    for day in _date_range(start, end):
        days = (day - start).days
        seasonal = 1 + 0.12 * math.sin(2 * math.pi * day.timetuple().tm_yday / 365.25)
        for channel in CHANNELS:
            promo = 1.0
            if channel in {"Paid Search", "Social"} and day.month in {11, 12}:
                promo = 1.58
            if channel == "Email" and day.weekday() in {1, 3}:
                promo *= 1.22
            if day == date(2026, 2, 17) and channel == "Paid Search":
                promo *= 2.8
            spend = max(35, random.gauss(channel_base[channel] * seasonal * promo, 45))
            ctr = {
                "Organic Search": 0.044,
                "Paid Search": 0.031,
                "Email": 0.071,
                "Social": 0.025,
                "Marketplace": 0.038,
                "Direct": 0.052,
            }[channel]
            impressions = int(spend * random.uniform(38, 72))
            clicks = int(impressions * random.gauss(ctr, ctr * 0.12))
            rows.append(
                {
                    "date": day.isoformat(),
                    "channel": channel,
                    "spend": f"{spend:.2f}",
                    "impressions": max(0, impressions),
                    "clicks": max(0, clicks),
                }
            )
    _write_csv(
        RAW_DIR / "marketing_spend.csv",
        rows,
        ["date", "channel", "spend", "impressions", "clicks"],
    )
    return rows


def generate_orders(customers: list[dict]) -> list[dict]:
    start = _parse_date(DATA_START)
    end = _parse_date(DATA_END)
    product_rows = [
        {
            "product_id": product_id,
            "product_name": product_name,
            "category": category,
            "price": price,
            "cost": cost,
        }
        for product_id, product_name, category, price, cost in PRODUCTS
    ]
    rows = []
    order_number = 1
    customer_ids = [row["customer_id"] for row in customers]
    customer_weights = [1.0 + (0.9 if row["customer_segment"] == "VIP" else 0.0) for row in customers]

    for day in _date_range(start, end):
        count = _daily_order_count(day, start)
        product_weights = _product_weights(day)
        for _ in range(count):
            product = random.choices(product_rows, weights=product_weights, k=1)[0]
            customer_id = random.choices(customer_ids, weights=customer_weights, k=1)[0]
            channel = _weighted_choice(CHANNELS, [0.27, 0.2, 0.17, 0.15, 0.13, 0.08])
            region = _weighted_choice(REGIONS, [0.25, 0.18, 0.2, 0.22, 0.15])
            quantity = random.choices([1, 2, 3, 4], weights=[0.67, 0.22, 0.08, 0.03], k=1)[0]
            unit_price = max(4.0, random.gauss(product["price"], product["price"] * 0.035))
            discount = random.choice([0.0, 0.05, 0.1, 0.15])
            if channel in {"Email", "Social"}:
                discount += random.choice([0.0, 0.05])
            if day.month in {11, 12}:
                discount += random.choice([0.05, 0.1, 0.15])
            if day == date(2026, 3, 8):
                discount += 0.28
            discount = min(discount, 0.45)
            gross_revenue = unit_price * quantity
            discount_amount = gross_revenue * discount
            shipping_cost = random.uniform(3.4, 11.8) + quantity * random.uniform(0.8, 2.2)
            status = random.choices(
                ["Completed", "Returned", "Cancelled"],
                weights=[0.935, 0.045, 0.02],
                k=1,
            )[0]
            if day == date(2026, 3, 8):
                status = random.choices(
                    ["Completed", "Returned", "Cancelled"],
                    weights=[0.82, 0.16, 0.02],
                    k=1,
                )[0]
            rows.append(
                {
                    "order_id": f"O-{order_number:07d}",
                    "order_date": day.isoformat(),
                    "customer_id": customer_id,
                    "product_id": product["product_id"],
                    "region": region,
                    "channel": channel,
                    "quantity": quantity,
                    "unit_price": f"{unit_price:.2f}",
                    "discount_pct": f"{discount:.4f}",
                    "discount_amount": f"{discount_amount:.2f}",
                    "gross_revenue": f"{gross_revenue:.2f}",
                    "shipping_cost": f"{shipping_cost:.2f}",
                    "order_status": status,
                }
            )
            order_number += 1

    _write_csv(
        RAW_DIR / "orders.csv",
        rows,
        [
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
        ],
    )
    return rows


def generate_demo_data() -> dict[str, int]:
    """Generate all raw CSVs and return row counts."""
    random.seed(RANDOM_SEED)
    products = generate_products()
    customers = generate_customers()
    marketing = generate_marketing_spend()
    orders = generate_orders(customers)
    return {
        "products": len(products),
        "customers": len(customers),
        "marketing_spend": len(marketing),
        "orders": len(orders),
    }
