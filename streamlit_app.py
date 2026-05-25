"""Optional Streamlit dashboard for the AI-powered BI project."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aibids.qa import AnalyticsQA  # noqa: E402


DATA_DIR = PROJECT_ROOT / "data" / "processed"


@st.cache_data
def load_data():
    daily = pd.read_csv(DATA_DIR / "daily_totals.csv", parse_dates=["date"])
    breakdown = pd.read_csv(DATA_DIR / "daily_breakdown.csv", parse_dates=["date"])
    forecast = pd.read_csv(DATA_DIR / "forecast_daily.csv", parse_dates=["date"])
    anomalies = pd.read_csv(DATA_DIR / "anomaly_events.csv", parse_dates=["date"])
    return daily, breakdown, forecast, anomalies


st.set_page_config(page_title="AI-Powered BI Dashboard", layout="wide")
st.title("AI-Powered Business Intelligence Dashboard")

daily, breakdown, forecast, anomalies = load_data()

with st.sidebar:
    st.header("Filters")
    start, end = st.date_input(
        "Date range",
        value=(daily["date"].min().date(), daily["date"].max().date()),
        min_value=daily["date"].min().date(),
        max_value=daily["date"].max().date(),
    )
    category = st.selectbox("Category", ["All"] + sorted(breakdown["category"].unique()))
    region = st.selectbox("Region", ["All"] + sorted(breakdown["region"].unique()))
    channel = st.selectbox("Channel", ["All"] + sorted(breakdown["channel"].unique()))

filtered = breakdown[(breakdown["date"].dt.date >= start) & (breakdown["date"].dt.date <= end)]
if category != "All":
    filtered = filtered[filtered["category"] == category]
if region != "All":
    filtered = filtered[filtered["region"] == region]
if channel != "All":
    filtered = filtered[filtered["channel"] == channel]

revenue = filtered["net_revenue"].sum()
profit = filtered["gross_profit"].sum()
orders = int(filtered["orders"].sum())
margin = profit / revenue if revenue else 0
aov = revenue / orders if orders else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Revenue", f"${revenue:,.0f}")
col2.metric("Gross Profit", f"${profit:,.0f}", f"{margin:.1%} margin")
col3.metric("Orders", f"{orders:,.0f}", f"${aov:,.0f} AOV")
col4.metric("30 Day Forecast", f"${forecast.head(30)['forecast_revenue'].sum():,.0f}")

daily_filtered = (
    filtered.groupby("date", as_index=False)
    .agg(net_revenue=("net_revenue", "sum"), gross_profit=("gross_profit", "sum"), orders=("orders", "sum"))
    .sort_values("date")
)

trend = px.line(daily_filtered, x="date", y="net_revenue", title="Daily Net Revenue")
trend.add_scatter(
    x=forecast["date"],
    y=forecast["forecast_revenue"],
    mode="lines",
    name="Forecast",
    line={"dash": "dash", "color": "#b74d3f"},
)
st.plotly_chart(trend, use_container_width=True)

left, right = st.columns(2)
with left:
    category_chart = (
        filtered.groupby("category", as_index=False)["net_revenue"].sum().sort_values("net_revenue", ascending=False)
    )
    st.plotly_chart(
        px.bar(category_chart, x="net_revenue", y="category", orientation="h", title="Category Revenue"),
        use_container_width=True,
    )
with right:
    region_chart = (
        filtered.groupby("region", as_index=False)["net_revenue"].sum().sort_values("net_revenue", ascending=False)
    )
    st.plotly_chart(
        px.bar(region_chart, x="net_revenue", y="region", orientation="h", title="Regional Revenue"),
        use_container_width=True,
    )

st.subheader("Anomaly Events")
st.dataframe(anomalies.sort_values("date", ascending=False).head(20), use_container_width=True)

st.subheader("Analytics Q&A")
question = st.text_input("Question", value="What was revenue in the last 30 days?")
if question:
    st.write(AnalyticsQA().answer(question)["answer"])
