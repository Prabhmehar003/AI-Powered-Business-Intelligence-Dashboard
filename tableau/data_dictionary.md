# Data Dictionary

## `tableau_sales_model.csv`

- `order_id`: Unique order identifier
- `order_date`: Order date
- `customer_id`: Unique customer identifier
- `customer_segment`: New, Returning, or VIP
- `product_id`, `product_name`, `category`: Product attributes
- `region`, `channel`: Sales geography and acquisition channel
- `quantity`, `unit_price`, `unit_cost`: Unit-level economics
- `gross_revenue`, `discount_amount`, `net_revenue`: Revenue fields
- `shipping_cost`, `gross_profit`, `margin_rate`: Profitability fields
- `order_status`: Completed, Returned, or Cancelled

## `tableau_daily_metrics.csv`

Daily KPI mart with revenue, profit, order volume, marketing spend, impressions, clicks, ROAS, CPC, and CTR.

## `tableau_daily_breakdown.csv`

Daily dimensional mart by date, category, region, and channel. Use it for filtered trend charts and dimensional comparisons.

## `tableau_forecast.csv`

90-day forecast with `forecast_revenue`, `lower_bound`, and `upper_bound`.

## `tableau_anomaly_events.csv`

Anomaly event table with severity, expected value, deviation percentage, explanation, and action hint.

## `tableau_customer_segments.csv`

Customer-level RFM-style output with order count, revenue, profit, recency, top category, and value band.
