"""Small CSV/JSON helpers used across the project."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable


def read_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    materialized = list(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(materialized)


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(value: str | int | float | None, default: float = 0.0) -> float:
    if value in {None, ""}:
        return default
    return float(value)


def as_int(value: str | int | float | None, default: int = 0) -> int:
    if value in {None, ""}:
        return default
    return int(float(value))
