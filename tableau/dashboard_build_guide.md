# Tableau Dashboard Build Guide

## Data Connections

Connect to the CSV files in `data/tableau`.

Recommended logical tables:

1. `tableau_sales_model.csv`
2. `tableau_daily_metrics.csv`
3. `tableau_daily_breakdown.csv`
4. `tableau_forecast.csv`
5. `tableau_anomaly_events.csv`
6. `tableau_customer_segments.csv`

Use `date` for daily marts and `order_date` for order-level analysis. Keep the daily forecast table separate or relate it to daily metrics on `date`.

## Dashboard Pages

1. Executive Overview
   - KPI tiles: Revenue, Gross Profit, Margin %, Orders, AOV, ROAS
   - Line chart: Daily Net Revenue
   - Bar charts: Category, Region, Channel

2. Forecasting
   - Actual revenue by date from `tableau_daily_metrics.csv`
   - Forecast revenue, lower bound, upper bound from `tableau_forecast.csv`
   - Forecast summary text box: seasonal ridge regression with holdout MAPE

3. Anomaly Monitor
   - Event table from `tableau_anomaly_events.csv`
   - Filter by severity and metric
   - Timeline of anomaly dates over daily revenue

4. Customer Value
   - Value bands from `tableau_customer_segments.csv`
   - Revenue and order counts by segment
   - Top categories by customer value band

## Filters

Add dashboard filters for:

- Date range
- Category
- Region
- Channel
- Customer segment
- Anomaly severity

## Suggested Layout

Use a 12-column dashboard grid. Put KPI tiles across the top, revenue trend across the left two-thirds, and anomaly/event cards on the right. Place category, region, and channel bars below the trend. Keep Forecasting and Customer Value as separate tabs for clarity.
