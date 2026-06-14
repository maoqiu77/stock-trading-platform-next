from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def resolve_project_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


DATA_HOME = resolve_project_path(os.getenv("STOCK_APP_DATA_HOME", "storage/local"))
TEMPLATE_HOME = resolve_project_path(
    os.getenv("STOCK_APP_TEMPLATE_HOME", "storage/templates")
)
DB_PATH = resolve_project_path(os.getenv("STOCK_APP_DB_PATH", "storage/local/app.db"))
MARKET_PROVIDER = os.getenv("STOCK_APP_MARKET_PROVIDER", "yfinance")
