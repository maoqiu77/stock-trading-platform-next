from __future__ import annotations

import argparse
import csv
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.core.database import init_db  # noqa: E402
from app.modules.ai_advice import save_ai_advice_state  # noqa: E402
from app.modules.ai_settings import save_ai_settings  # noqa: E402
from app.modules.trading_data import (  # noqa: E402
    BALANCED_SETTINGS,
    STRATEGY_ENGINE_KEY_MAP,
    save_trading_state,
)


DEFAULT_LEGACY_ROOT = Path("/Users/yaochengzhi/Documents/股票交易平台")
PROFILE_IDS = ("conservative", "balanced", "aggressive", "custom")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import private legacy Streamlit data into storage/local/app.db."
    )
    parser.add_argument(
        "--legacy-root",
        type=Path,
        default=DEFAULT_LEGACY_ROOT,
        help="Path to the old Streamlit project.",
    )
    args = parser.parse_args()

    legacy_root = args.legacy_root.expanduser().resolve()
    if not legacy_root.exists():
        raise SystemExit(f"Legacy project not found: {legacy_root}")

    init_db()
    config = load_yaml(legacy_root / "config.yaml")
    trading_state = build_trading_state(legacy_root, config)
    saved_state = save_trading_state(trading_state)

    advice_state = build_ai_advice_state(legacy_root / "storage" / "ai_advice")
    saved_advice = save_ai_advice_state(advice_state)

    ai_settings = build_ai_settings(legacy_root / ".env")
    saved_ai_settings = save_ai_settings(ai_settings)

    print("Imported legacy private data into storage/local/app.db")
    print(f"stockPool={','.join(saved_state['stockPool'])}")
    print(f"positions={len(saved_state['positions'])}")
    print(f"trades={len(saved_state['trades'])}")
    print(f"aiAdviceRecords={len(saved_advice['records'])}")
    print(f"aiBaseUrl={saved_ai_settings['baseUrl']}")
    print(f"aiModel={saved_ai_settings['model']}")
    print(f"aiApiKey={mask_key(saved_ai_settings['apiKey'])}")


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload if isinstance(payload, dict) else {}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_trading_state(legacy_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    account_rows = read_csv_rows(legacy_root / "storage" / "account.csv")
    portfolio_rows = read_csv_rows(legacy_root / "storage" / "portfolio.csv")
    trade_rows = read_csv_rows(legacy_root / "storage" / "trade_history.csv")

    account = account_rows[0] if account_rows else config.get("account", {})
    stock_pool = [
        normalize_ticker(item)
        for item in config.get("stock_pool", [])
        if normalize_ticker(item)
    ]
    positions = [legacy_position_to_state(row) for row in portfolio_rows]
    trades = [
        legacy_trade_to_state(index, row)
        for index, row in enumerate(trade_rows, start=1)
    ]

    return {
        "schemaVersion": 1,
        "account": {
            "totalAssets": number(account.get("total_assets"), 0.0),
            "baseCurrency": "USD",
        },
        "stockPool": stock_pool,
        "positions": positions,
        "trades": trades,
        "activeStrategyProfile": str(config.get("active_strategy_profile") or "balanced"),
        "strategyProfiles": build_strategy_profiles(config),
        "privacyMode": "external-ai-ready",
    }


def legacy_position_to_state(row: dict[str, str]) -> dict[str, Any]:
    return {
        "ticker": normalize_ticker(row.get("ticker")),
        "targetWeight": number(row.get("target_weight")),
        "assetType": "ETF" if str(row.get("asset_type", "")).upper() == "ETF" else "STOCK",
        "takeProfitPct": number(row.get("take_profit_pct")),
        "stopLossPct": number(row.get("stop_loss_pct")),
        "purchaseDate": str(row.get("purchase_date") or ""),
    }


def legacy_trade_to_state(index: int, row: dict[str, str]) -> dict[str, Any]:
    unit_price = number(row.get("unit_price"))
    amount = number(row.get("amount"))
    shares = number(row.get("shares"))
    if shares <= 0 and amount > 0 and unit_price > 0:
        shares = amount / unit_price
    return {
        "id": f"legacy-{index:03d}",
        "date": str(row.get("date") or ""),
        "ticker": normalize_ticker(row.get("ticker")),
        "action": "卖出" if str(row.get("action", "")).strip() == "卖出" else "买入",
        "shares": shares,
        "unitPrice": unit_price,
        "amount": amount,
        "note": str(row.get("note") or "").strip(),
    }


def build_strategy_profiles(config: dict[str, Any]) -> list[dict[str, Any]]:
    existing_profiles = config.get("strategy_profiles", {})
    if not isinstance(existing_profiles, dict):
        existing_profiles = {}
    base_strategy = config.get("strategy", {})
    base_risk = config.get("risk", {})
    profiles = []
    for profile_id in PROFILE_IDS:
        source = existing_profiles.get(profile_id, {})
        if not isinstance(source, dict):
            source = {}
        strategy = source.get("strategy") if isinstance(source.get("strategy"), dict) else base_strategy
        risk = source.get("risk") if isinstance(source.get("risk"), dict) else base_risk
        settings = deepcopy(BALANCED_SETTINGS)
        settings.update(snake_settings_to_camel(strategy))
        settings.update(snake_settings_to_camel(risk))
        base_role_settings = snake_settings_to_camel(base_strategy)
        if not settings.get("coreHoldings"):
            settings["coreHoldings"] = base_role_settings.get("coreHoldings", {})
        if not settings.get("satelliteSymbols"):
            settings["satelliteSymbols"] = base_role_settings.get("satelliteSymbols", [])
        profiles.append(
            {
                "id": profile_id,
                "name": str(source.get("name") or default_profile_name(profile_id)),
                "description": str(source.get("description") or default_profile_description(profile_id)),
                "settings": settings,
            }
        )
    return profiles


def snake_settings_to_camel(source: Any) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}
    inverse = {engine_key: source_key for source_key, engine_key in STRATEGY_ENGINE_KEY_MAP.items()}
    output: dict[str, Any] = {}
    for key, value in source.items():
        camel_key = inverse.get(str(key))
        if camel_key:
            output[camel_key] = value
    return output


def build_ai_advice_state(advice_dir: Path) -> dict[str, Any]:
    records: dict[str, Any] = {}
    if advice_dir.exists():
        for path in sorted(advice_dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(record, dict):
                record_date = str(record.get("date") or path.stem)
                record["date"] = record_date
                record.setdefault("source", "legacy-streamlit")
                records[record_date] = record
    return {"schemaVersion": 1, "records": records}


def build_ai_settings(env_path: Path) -> dict[str, Any]:
    env = read_env(env_path)
    return {
        "schemaVersion": 1,
        "baseUrl": env.get("AI_BASE_URL", ""),
        "model": env.get("AI_MODEL", ""),
        "apiKey": env.get("AI_API_KEY", ""),
        "updatedAt": "",
    }


def read_env(path: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    if not path.exists():
        return output
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        output[key.strip()] = value.strip().strip('"').strip("'")
    return output


def normalize_ticker(value: Any) -> str:
    return str(value or "").strip().upper()


def number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def default_profile_name(profile_id: str) -> str:
    return {
        "conservative": "保守型",
        "balanced": "平衡型",
        "aggressive": "进取型",
        "custom": "自定义",
    }.get(profile_id, profile_id)


def default_profile_description(profile_id: str) -> str:
    return {
        "conservative": "更严格的追高限制，更小的单次加仓比例。",
        "balanced": "默认策略参数，适合多数手动加减仓场景。",
        "aggressive": "允许更高 RSI 和更大单次加仓比例。",
        "custom": "从当前策略复制而来，可按自己的交易风格调整。",
    }.get(profile_id, "")


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


if __name__ == "__main__":
    main()
