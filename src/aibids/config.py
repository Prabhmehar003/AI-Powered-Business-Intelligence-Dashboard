"""Project paths and shared configuration."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
TABLEAU_DIR = DATA_DIR / "tableau"
MODEL_DIR = PROJECT_ROOT / "models"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
DASHBOARD_ASSETS_DIR = DASHBOARD_DIR / "assets"

DATA_START = "2024-01-01"
DATA_END = "2026-04-30"
FORECAST_HORIZON_DAYS = 90
RANDOM_SEED = 42

CHANNELS = [
    "Organic Search",
    "Paid Search",
    "Email",
    "Social",
    "Marketplace",
    "Direct",
]

REGIONS = ["North", "South", "East", "West", "Central"]
SEGMENTS = ["New", "Returning", "VIP"]


def ensure_directories() -> None:
    """Create all project output directories."""
    for path in [
        RAW_DIR,
        PROCESSED_DIR,
        TABLEAU_DIR,
        MODEL_DIR,
        DASHBOARD_ASSETS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
