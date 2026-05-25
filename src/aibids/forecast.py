"""Forecast daily revenue with a small dependency-free regression model."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from .config import FORECAST_HORIZON_DAYS, MODEL_DIR, PROCESSED_DIR
from .io_utils import as_float, read_csv, write_csv, write_json


FORECAST_FIELDS = [
    "date",
    "horizon_day",
    "forecast_revenue",
    "lower_bound",
    "upper_bound",
    "model",
]


def _parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


def _money(value: float) -> str:
    return f"{value:.2f}"


def _features(day, start_day) -> list[float]:
    day_index = (day - start_day).days
    scaled_time = day_index / 365.25
    day_of_year = day.timetuple().tm_yday
    weekday = day.weekday()
    vector = [
        1.0,
        scaled_time,
        math.sin(2 * math.pi * day_of_year / 365.25),
        math.cos(2 * math.pi * day_of_year / 365.25),
    ]
    vector.extend(1.0 if weekday == index else 0.0 for index in range(6))
    return vector


def _solve_linear_system(matrix: list[list[float]], target: list[float]) -> list[float]:
    size = len(target)
    augmented = [row[:] + [target[index]] for index, row in enumerate(matrix)]

    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-9:
            augmented[pivot][col] = 1e-9
        if pivot != col:
            augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        pivot_value = augmented[col][col]
        for j in range(col, size + 1):
            augmented[col][j] /= pivot_value
        for row in range(size):
            if row == col:
                continue
            factor = augmented[row][col]
            if factor == 0:
                continue
            for j in range(col, size + 1):
                augmented[row][j] -= factor * augmented[col][j]

    return [augmented[row][size] for row in range(size)]


def _fit(features: list[list[float]], target: list[float], ridge: float = 0.35) -> list[float]:
    width = len(features[0])
    xtx = [[0.0 for _ in range(width)] for _ in range(width)]
    xty = [0.0 for _ in range(width)]
    for row, value in zip(features, target):
        for i in range(width):
            xty[i] += row[i] * value
            for j in range(width):
                xtx[i][j] += row[i] * row[j]
    for i in range(1, width):
        xtx[i][i] += ridge
    return _solve_linear_system(xtx, xty)


def _predict(coefficients: list[float], features: list[float]) -> float:
    return sum(coefficient * value for coefficient, value in zip(coefficients, features))


def _mape(actual: list[float], predicted: list[float]) -> float:
    errors = []
    for observed, estimate in zip(actual, predicted):
        if observed <= 0:
            continue
        errors.append(abs(observed - estimate) / observed)
    return sum(errors) / len(errors) if errors else 0.0


def forecast_daily_revenue(horizon_days: int = FORECAST_HORIZON_DAYS) -> dict[str, float | int | str]:
    """Train the revenue model, write forecasts, and return model metrics."""
    daily_rows = read_csv(PROCESSED_DIR / "daily_totals.csv")
    history = [(_parse_date(row["date"]), as_float(row["net_revenue"])) for row in daily_rows]
    history.sort(key=lambda item: item[0])
    if len(history) < 120:
        raise ValueError("At least 120 daily observations are required for forecasting")

    start_day = history[0][0]
    holdout_size = min(60, max(21, len(history) // 8))
    train = history[:-holdout_size]
    holdout = history[-holdout_size:]

    train_features = [_features(day, start_day) for day, _ in train]
    train_target = [value for _, value in train]
    backtest_coefficients = _fit(train_features, train_target)
    holdout_predictions = [
        max(0.0, _predict(backtest_coefficients, _features(day, start_day))) for day, _ in holdout
    ]
    holdout_actual = [value for _, value in holdout]
    mape = _mape(holdout_actual, holdout_predictions)

    all_features = [_features(day, start_day) for day, _ in history]
    all_target = [value for _, value in history]
    coefficients = _fit(all_features, all_target)
    fitted = [max(0.0, _predict(coefficients, features)) for features in all_features]
    residuals = [actual - estimate for actual, estimate in zip(all_target, fitted)]
    residual_std = math.sqrt(sum(value * value for value in residuals) / max(1, len(residuals) - 1))

    last_day = history[-1][0]
    forecast_rows = []
    for horizon in range(1, horizon_days + 1):
        forecast_day = last_day + timedelta(days=horizon)
        estimate = max(0.0, _predict(coefficients, _features(forecast_day, start_day)))
        interval = 1.96 * residual_std * math.sqrt(1 + horizon / 365.25)
        forecast_rows.append(
            {
                "date": forecast_day.isoformat(),
                "horizon_day": horizon,
                "forecast_revenue": _money(estimate),
                "lower_bound": _money(max(0.0, estimate - interval)),
                "upper_bound": _money(estimate + interval),
                "model": "ridge_seasonal_regression",
            }
        )

    summary = {
        "model": "ridge_seasonal_regression",
        "training_start": history[0][0].isoformat(),
        "training_end": history[-1][0].isoformat(),
        "observations": len(history),
        "horizon_days": horizon_days,
        "holdout_days": holdout_size,
        "holdout_mape": round(mape, 4),
        "residual_std": round(residual_std, 2),
        "next_30_day_forecast": round(
            sum(as_float(row["forecast_revenue"]) for row in forecast_rows[:30]), 2
        ),
    }
    write_csv(PROCESSED_DIR / "forecast_daily.csv", forecast_rows, FORECAST_FIELDS)
    write_json(PROCESSED_DIR / "forecast_summary.json", summary)
    write_json(
        MODEL_DIR / "forecast_model.json",
        {
            **summary,
            "coefficients": [round(value, 6) for value in coefficients],
            "feature_order": [
                "intercept",
                "scaled_time",
                "sin_day_of_year",
                "cos_day_of_year",
                "weekday_monday",
                "weekday_tuesday",
                "weekday_wednesday",
                "weekday_thursday",
                "weekday_friday",
                "weekday_saturday",
            ],
        },
    )
    return summary
