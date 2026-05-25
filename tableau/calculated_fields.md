# Tableau Calculated Fields

## Revenue

```text
SUM([net_revenue])
```

## Gross Profit

```text
SUM([gross_profit])
```

## Gross Margin %

```text
SUM([gross_profit]) / SUM([net_revenue])
```

## Average Order Value

```text
SUM([net_revenue]) / COUNTD([order_id])
```

## Units Per Order

```text
SUM([quantity]) / COUNTD([order_id])
```

## Discount Rate

```text
SUM([discount_amount]) / SUM([gross_revenue])
```

## Forecast Variance

```text
SUM([net_revenue]) - SUM([forecast_revenue])
```

## Forecast Variance %

```text
(SUM([net_revenue]) - SUM([forecast_revenue])) / SUM([forecast_revenue])
```

## Anomaly Direction

```text
IF FLOAT([deviation_pct]) > 0 THEN "Spike" ELSE "Drop" END
```

## ROAS

```text
SUM([net_revenue]) / SUM([marketing_spend])
```
