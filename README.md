# AI-Powered Business Intelligence Dashboard

End-to-end analytics project for e-commerce sales data. It generates raw operational data, builds analytics marts, forecasts revenue, detects anomalies, exports Tableau-ready CSVs, and serves an interactive Python/HTML dashboard with a local natural-language Q&A assistant.

## What Is Included

- Raw synthetic e-commerce data: orders, customers, products, marketing spend
- Data ingestion and feature engineering pipeline
- Revenue forecasting with dependency-free seasonal regression
- Revenue, margin, and ROAS anomaly detection
- Tableau-ready export pack in `data/tableau`
- Interactive browser dashboard in `dashboard/index.html`
- Optional Streamlit dashboard in `streamlit_app.py`
- Local Q&A assistant in `scripts/ask.py`

## Quick Start

```bash
cd /Users/prabhmehardhalio/Documents/Playground/ai-powered-bi-dashboard
python3 scripts/run_pipeline.py
```

Open the dashboard:

```bash
open dashboard/index.html
```

Ask the local analytics assistant:

```bash
python3 scripts/ask.py "What was revenue in the last 30 days?"
python3 scripts/ask.py "Show the next 30 day forecast"
python3 scripts/ask.py "Were there anomalies in the last 90 days?"
```

## Optional Streamlit App

The core project runs with the Python standard library. For the Streamlit version:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Project Structure

```text
ai-powered-bi-dashboard/
  dashboard/              Interactive static dashboard
  data/raw/               Generated operational source data
  data/processed/         Analytics marts, forecasts, anomaly outputs
  data/tableau/           Tableau-ready CSV export pack
  models/                 Forecast model metadata
  scripts/                Pipeline and Q&A commands
  src/aibids/             Data, ML, anomaly, Q&A, export modules
  tableau/                Tableau build guide and calculated fields
  tests/                  Smoke tests
```

## Tableau Workflow

Use the files in `data/tableau`:

- `tableau_sales_model.csv`: order-level fact table
- `tableau_daily_metrics.csv`: daily KPI mart
- `tableau_daily_breakdown.csv`: date/category/region/channel mart
- `tableau_forecast.csv`: 90-day revenue forecast
- `tableau_anomaly_events.csv`: anomaly event table
- `tableau_customer_segments.csv`: customer-level value bands

See `tableau/dashboard_build_guide.md` and `tableau/calculated_fields.md` for the workbook layout.

## Reproducibility

The pipeline is deterministic. Rerunning `python3 scripts/run_pipeline.py` regenerates the same raw data and downstream outputs from a fixed seed.
